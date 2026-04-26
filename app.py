from flask import Flask, request, redirect, jsonify
import psycopg2
import time
import os
import datetime
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# -------------------------
# POSTGRES CONNECTION
# -------------------------
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cursor = conn.cursor()

# -------------------------
# DATABASE
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
id SERIAL PRIMARY KEY,
name TEXT,
email TEXT,
film_id INTEGER,
created_at BIGINT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
id SERIAL PRIMARY KEY,
title TEXT,
youtube_link TEXT,
release_time BIGINT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS viewers (
ticket_id INTEGER PRIMARY KEY,
last_seen BIGINT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logins (
id SERIAL PRIMARY KEY,
name TEXT,
email TEXT,
time BIGINT
)
""")

conn.commit()

# -------------------------
# SETTINGS
# -------------------------
MAX_TICKETS = 700
ADMIN_PASSWORD = "Muha&123"

# -------------------------
# PREMIERE SETUP (7PM)
# -------------------------
release_time = int(datetime.datetime(2026, 5, 1, 19, 0).timestamp())

cursor.execute("SELECT COUNT(*) FROM films")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
    INSERT INTO films (title, youtube_link, release_time)
    VALUES (%s, %s, %s)
    """, (
        "XineRent Premiere Film",
        "https://www.youtube.com/embed/-AUw43bmMWQ",
        release_time
    ))
    conn.commit()

# -------------------------
# HOME (ADDED)
# -------------------------
@app.route("/")
def home():
    return """
    <h1>XineRent Running</h1>
    <a href="/enter">Enter Premiere</a><br>
    <a href="/admin">Admin Panel</a>
    """

# -------------------------
# ENTER (EMAIL LABEL ADDED)
# -------------------------
@app.route("/enter", methods=["GET","POST"])
def enter():

    if request.method=="POST":
        email=request.form["email"]

        cursor.execute("SELECT id FROM tickets WHERE email=%s",(email,))
        t=cursor.fetchone()

        if t:
            return redirect(f"/watch/{t[0]}")

        return "<h2>No ticket</h2>"

    return f"""
    <html><head></head>
    <body>
    <h2>Enter Premiere</h2>

    <form method="POST">
        <p>Enter your email to access the premiere</p>
        <input name="email" placeholder="Email" required>
        <button>Enter</button>
    </form>

    </body></html>
    """

# -------------------------
# API: TICKET COUNT
# -------------------------
@app.route("/ticket-count/<int:film_id>")
def ticket_count(film_id):
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    return jsonify({"count": cursor.fetchone()[0]})

# -------------------------
# ADMIN LIVE API
# -------------------------
@app.route("/admin-data")
def admin_data():
    cursor.execute("""
    SELECT tickets.name,tickets.email
    FROM viewers
    JOIN tickets ON tickets.id=viewers.ticket_id
    WHERE last_seen > %s
    """, (int(time.time()) - 60,))

    live = cursor.fetchall()

    return jsonify({
        "live": [{"name": x[0], "email": x[1]} for x in live],
        "server_time": int(time.time())
    })

# -------------------------
# STYLE + JS
# -------------------------
BASE_STYLE = """
<script>
function startCountdown(endTime){
    function update(){
        const now = Math.floor(Date.now()/1000);
        const diff = endTime - now;

        const timer = document.getElementById("timer");

        if(diff <= 0){
            if(timer) timer.innerHTML = "🎬 LIVE NOW";
            return;
        }

        const d = Math.floor(diff/86400);
        const h = Math.floor((diff%86400)/3600);
        const m = Math.floor((diff%3600)/60);
        const s = diff%60;

        if(timer){
            timer.innerHTML = d+"d "+h+"h "+m+"m "+s+"s";
        }
    }
    update();
    setInterval(update,1000);
}
</script>
"""

# -------------------------
# WATCH (LOCK + TIMER FIXED)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
    t = cursor.fetchone()

    if not t:
        return "<h2>Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
    film = cursor.fetchone()

    if not film:
        return "<h2>Film not found</h2>"

    now = int(time.time())
    release = int(film[3])

    # LOCKED
    if now < release:
        return f"""
        <html>
        <head>{BASE_STYLE}</head>
        <body onload="startCountdown({release})">

        <h2>🔒 PREMIERE LOCKED</h2>
        <p>Welcome {t[1]}</p>

        <div id="timer" style="font-size:40px;"></div>

        </body>
        </html>
        """

    # AFTER RELEASE
    video = film[2]

    cursor.execute("""
    INSERT INTO viewers(ticket_id,last_seen)
    VALUES(%s,%s)
    ON CONFLICT(ticket_id)
    DO UPDATE SET last_seen=EXCLUDED.last_seen
    """, (ticket_id, now))

    conn.commit()

    return f"""
    <html>
    <body>

    <h2>🎬 PREMIERE ROOM</h2>

    <iframe width="100%" height="500" src="{video}?autoplay=1"></iframe>

    </body>
    </html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET","POST"])
def admin():

    p = request.form.get("pass") or request.args.get("pass")

    if p != ADMIN_PASSWORD:
        return """
        <h2>Admin Login</h2>
        <form method="POST">
            <input name="pass" type="password">
            <button>Unlock</button>
        </form>
        """

    cursor.execute("SELECT * FROM logins ORDER BY id DESC")
    logs = cursor.fetchall()

    html = "<h1>ADMIN PANEL</h1>"

    html += "<h2>LIVE VIEWERS</h2><div id='live-box'>Loading...</div>"

    for x in logs:
        html += f"<p>{x[1]} | {x[2]}</p>"

    return f"""
    <html>
    <body onload="loadLive()">
    {html}

    <script>
    function loadLive(){{
        fetch("/admin-data")
        .then(r => r.json())
        .then(data => {{
            let html = "";
            data.live.forEach(v => {{
                html += `<p>${{v.name}} | ${{v.email}}</p>`;
            }});
            document.getElementById("live-box").innerHTML = html;
        }});
    }}
    setInterval(loadLive,3000);
    </script>

    </body>
    </html>
    """

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
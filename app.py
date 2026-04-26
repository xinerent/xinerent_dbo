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
# PREMIERE SETUP (UTC FIXED)
# 7PM WAT = 18:00 UTC
# -------------------------
release_time = int(datetime.datetime(2026, 5, 1, 18, 0).timestamp())

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
# TIME FORMAT
# -------------------------
def format_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d %b %Y %I:%M %p")

# -------------------------
# COUNTER API
# -------------------------
@app.route("/ticket-count/<int:film_id>")
def ticket_count(film_id):
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    count = cursor.fetchone()[0]
    return jsonify({"count": count})

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
    """,(int(time.time())-60,))

    live = cursor.fetchall()

    return jsonify({
        "live":[{"name":x[0],"email":x[1]} for x in live]
    })

# -------------------------
# STYLE
# -------------------------
BASE_STYLE = """
<style>
body {
    margin:0;
    font-family: Arial;
    background: radial-gradient(circle at top,#050505,#000);
    color:white;
    text-align:center;
}

.container { padding: 80px 20px; }

.card {
    background:#0f0f0f;
    border-radius:25px;
    padding:60px;
    margin:30px auto;
    max-width:95%;
    border:1px solid rgba(212,175,55,0.25);
}

h1 { font-size:110px; }
h2 { font-size:75px; }
p  { font-size:40px; }

.glow {
    color:#d4af37;
    text-shadow:0 0 25px #d4af37;
}

iframe {
    width:100%;
    height:600px;
    border-radius:20px;
}

a,button{
    display:block;
    margin-top:25px;
    padding:40px;
    font-size:40px;
    background:linear-gradient(135deg,#d4af37,#f5e6c8);
    color:black;
    border-radius:20px;
    font-weight:bold;
    border:none !important;
}

input{
    width:95%;
    padding:35px;
    font-size:38px;
    border-radius:15px;
    background:#111;
    color:white;
}

.live {
    color:#00ff88;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0% {opacity:1;}
    50% {opacity:0.4;}
    100% {opacity:1;}
}

.admin-box {
    background:black;
    color:white;
    padding:30px;
    border-radius:20px;
    text-align:left;
}

.timer {
    font-size:50px;
    margin-top:20px;
    color:#d4af37;
    text-shadow:0 0 20px #d4af37;
}

.fs-btn{
    margin-top:20px;
    padding:20px;
    font-size:30px;
    background:black;
    color:#d4af37;
    border-radius:15px;
}
</style>

<script>
function startCountdown(endTime){
    function update(){
        let now = Math.floor(Date.now()/1000);
        let diff = endTime - now;

        if(diff <= 0){
            clearInterval(countdownInterval);
            document.getElementById("timer").innerHTML = "🎬 LIVE NOW";
            document.getElementById("player").style.display = "block";
            document.getElementById("lock").style.display = "none";
            autoCinema();
            return;
        }

        let d = Math.floor(diff / 86400);
        let h = Math.floor((diff % 86400) / 3600);
        let m = Math.floor((diff % 3600) / 60);
        let s = diff % 60;

        document.getElementById("timer").innerHTML =
            d+"d "+h+"h "+m+"m "+s+"s";
    }

    update();
    countdownInterval = setInterval(update,1000);
}
</script>
"""

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h1 class="glow">🎬 XineRent</h1>
        <div class="card">
            <a href="/films">🎟 Get Ticket</a>
            <a href="/enter">🎬 Enter Premiere</a>
            <a href="/admin">🔐 Admin Panel</a>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# FILMS
# -------------------------
@app.route("/films")
def films():
    cursor.execute("SELECT * FROM films")
    films = cursor.fetchall()

    html = f"<html><head>{BASE_STYLE}</head><body><div class='container'>"

    film_ids = []

    for f in films:
        film_ids.append(f[0])

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (f[0],))
        count = cursor.fetchone()[0]

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p>
                <span id="count-{f[0]}">{count}</span> / {MAX_TICKETS}
            </p>
            <script>
                window.FILM_IDS = {film_ids};
            </script>
        """

        if count >= MAX_TICKETS:
            html += "<p>❌ SOLD OUT</p>"
        else:
            html += f"<a href='/claim/{f[0]}'>🎟 Claim Ticket</a>"

        html += "</div>"

    return html + "</div></body></html>"

# -------------------------
# CLAIM
# -------------------------
@app.route("/claim/<int:film_id>")
def claim(film_id):
    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h2 class="glow">🎟 Claim Ticket</h2>
        <div class="card">
            <form action="/submit/{film_id}" method="POST">
                <input name="name" placeholder="Name" required>
                <input name="email" placeholder="Email" required>
                <button>Get Ticket</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# SUBMIT
# -------------------------
@app.route("/submit/<int:film_id>", methods=["POST"])
def submit(film_id):
    name = request.form["name"]
    email = request.form["email"]

    cursor.execute("INSERT INTO logins(name,email,time) VALUES(%s,%s,%s)",
                   (name,email,int(time.time())))
    conn.commit()

    cursor.execute("SELECT id FROM tickets WHERE email=%s AND film_id=%s", (email,film_id))
    ex = cursor.fetchone()

    if ex:
        return redirect(f"/watch/{ex[0]}")

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    if cursor.fetchone()[0] >= MAX_TICKETS:
        return "<h2>Sold Out</h2>"

    cursor.execute("""
        INSERT INTO tickets(name,email,film_id,created_at)
        VALUES(%s,%s,%s,%s)
        RETURNING id
    """, (name,email,film_id,int(time.time())))

    ticket_id = cursor.fetchone()[0]
    conn.commit()

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# ENTER
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
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h2 class="glow">Enter Premiere</h2>
        <div class="card">
            <form method="POST">
                <p>Enter your email to access the premiere</p>
                <input name="email" placeholder="Enter your email" required>
                <button>Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
    t=cursor.fetchone()

    if not t:
        return "<h2>Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
    film=cursor.fetchone()

    video = film[2] if film and film[2] else ""
    now=int(time.time())

    cursor.execute("""
    INSERT INTO viewers(ticket_id,last_seen)
    VALUES(%s,%s)
    ON CONFLICT(ticket_id)
    DO UPDATE SET last_seen=EXCLUDED.last_seen
    """,(ticket_id,now))

    conn.commit()

    return f"""
    <html><head>{BASE_STYLE}</head>
    <body onload="startCountdown({int(film[3])})">
    <div class="container">
        <h2 class="glow">🎬 PREMIERE ROOM</h2>

        <div class="card" id="lock">
            <p>Welcome {t[1]}</p>
            <p>Premiere countdown:</p>
            <div id="timer" class="timer"></div>
        </div>

        <div id="player" style="display:none;">
            <iframe id="videoFrame"
                src="{video}?autoplay=1&controls=1"
                allow="autoplay; fullscreen">
            </iframe>

            <button class="fs-btn" onclick="goCinema()">⛶ Enter Full Cinema Mode</button>
        </div>

    </div>
    </body></html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET","POST"])
def admin():

    p=request.form.get("pass") or request.args.get("pass")

    if p!=ADMIN_PASSWORD:
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body>
        <div class="container">
            <h2 class="glow">ADMIN LOGIN</h2>
            <div class="card">
                <form method="POST">
                    <input name="pass" type="password">
                    <button>Unlock</button>
                </form>
            </div>
        </div>
        </body></html>
        """

    cursor.execute("SELECT * FROM logins ORDER BY id DESC")
    logs=cursor.fetchall()

    html="<h1 class='glow'>ADMIN PANEL</h1>"
    html+="<div class='admin-box'><h2>LIVE VIEWERS</h2><div id='live-box'></div>"

    html+="<h2>USERS</h2>"
    for x in logs:
        html+=f"<p>{x[1]} | {x[2]}</p>"

    html+="</div>"

    return f"<html><head>{BASE_STYLE}</head><body><div class='container'>{html}</div></body></html>"

# -------------------------
# RUN
# -------------------------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
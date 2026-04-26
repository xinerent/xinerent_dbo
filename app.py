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
# PREMIERE SETUP
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
# STYLE + CINEMA ENGINE JS
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

.timer {
    font-size:50px;
    margin-top:20px;
    color:#d4af37;
    text-shadow:0 0 20px #d4af37;
}
</style>

<script>
function startCountdown(endTime){

    function update(){
        const now = Math.floor(Date.now() / 1000);
        const diff = endTime - now;

        const timerEl = document.getElementById("timer");

        if(diff <= 0){
            if(timerEl) timerEl.innerHTML = "🎬 LIVE NOW";

            const lock = document.getElementById("lock");
            const player = document.getElementById("player");

            if(lock) lock.style.display = "none";
            if(player) player.style.display = "block";
            return;
        }

        let d = Math.floor(diff / 86400);
        let h = Math.floor((diff % 86400) / 3600);
        let m = Math.floor((diff % 3600) / 60);
        let s = diff % 60;

        if(timerEl){
            timerEl.innerHTML = `${d}d ${h}h ${m}m ${s}s`;
        }
    }

    update();
    setInterval(update, 1000);
}

/* ---------------- CINEMA MODE ---------------- */

function goCinema(){
    const overlay = document.getElementById("cinemaOverlay");
    if(overlay) overlay.style.display = "flex";

    const el = document.documentElement;

    if (el.requestFullscreen) el.requestFullscreen();
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    else if (el.msRequestFullscreen) el.msRequestFullscreen();
}

function exitCinema(){
    const overlay = document.getElementById("cinemaOverlay");
    if(overlay) overlay.style.display = "none";

    if (document.exitFullscreen) document.exitFullscreen();
    else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
}

function togglePlay(){
    const video = document.getElementById("cinemaVideo");
    if(!video) return;

    if(video.paused) video.play();
    else video.pause();
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

    for f in films:
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (f[0],))
        count = cursor.fetchone()[0]

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p>{count} / {MAX_TICKETS}</p>
        """

        if count >= MAX_TICKETS:
            html += "<p>❌ SOLD OUT</p>"
        else:
            html += f"<a href='/claim/{f[0]}'>🎟 Claim Ticket</a>"

        html += "</div>"

    return html + "</div></body></html>"

# -------------------------
# CLAIM / SUBMIT / ENTER
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

    cursor.execute("""
        INSERT INTO tickets(name,email,film_id,created_at)
        VALUES(%s,%s,%s,%s)
        RETURNING id
    """, (name,email,film_id,int(time.time())))

    ticket_id = cursor.fetchone()[0]
    conn.commit()

    return redirect(f"/watch/{ticket_id}")

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
                <input name="email">
                <button>Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH (CINEMA MODE ENABLED)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
    t=cursor.fetchone()

    if not t:
        return "<h2>Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
    film=cursor.fetchone()

    if not film:
        return "<h2>Film not found</h2>"

    now = int(time.time())
    release = int(film[3])

    if now < release:
        return f"""
        <html>
        <head>{BASE_STYLE}</head>
        <body onload="startCountdown({release})">

        <div class="container">
            <h2 class="glow">🔒 PREMIERE LOCKED</h2>

            <div class="card" id="lock">
                <p>Welcome {t[1]}</p>
                <div id="timer" class="timer"></div>
            </div>
        </div>

        </body>
        </html>
        """

    video = film[2]

    cursor.execute("""
    INSERT INTO viewers(ticket_id,last_seen)
    VALUES(%s,%s)
    ON CONFLICT(ticket_id)
    DO UPDATE SET last_seen=EXCLUDED.last_seen
    """,(ticket_id,now))

    conn.commit()

    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body>

    <div class="container">
        <h2 class="glow">🎬 PREMIERE ROOM</h2>

        <div class="card">
            <button onclick="goCinema()">⛶ Enter Cinema Mode</button>
        </div>
    </div>

    <!-- CINEMA MODE -->
    <div id="cinemaOverlay"
         style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:black;z-index:9999;flex-direction:column;justify-content:center;align-items:center;">

        <video id="cinemaVideo" width="100%" height="100%" autoplay controls>
            <source src="{video}" type="video/mp4">
        </video>

        <div style="position:absolute;bottom:40px;display:flex;gap:30px;">
            <button onclick="togglePlay()">⏯ Play/Pause</button>
            <button onclick="exitCinema()">❌ Exit</button>
        </div>

    </div>

    </body>
    </html>
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
    for x in logs:
        html+=f"<p>{x[1]} | {x[2]}</p>"

    return f"<html><head>{BASE_STYLE}</head><body><div class='container'>{html}</div></body></html>"

# -------------------------
# RUN
# -------------------------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
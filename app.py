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
# API: TICKET COUNT
# -------------------------
@app.route("/ticket-count/<int:film_id>")
def ticket_count(film_id):
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    return jsonify({"count": cursor.fetchone()[0]})

# -------------------------
# LIVE VIEWERS API (ADMIN)
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
# STYLE + CINEMA ENGINE
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

iframe, video {
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
    border:none;
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
    font-size:60px;
    margin-top:20px;
    color:#d4af37;
    text-shadow:0 0 20px #d4af37;
}

/* CINEMA OVERLAY */
#cinemaOverlay{
    display:none;
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:black;
    z-index:9999;
    justify-content:center;
    align-items:center;
    flex-direction:column;
}
</style>

<script>

/* ---------------- SAFE COUNTDOWN ENGINE ---------------- */
function startCountdown(endTime){

    function update(){
        const now = Math.floor(Date.now() / 1000);
        const diff = endTime - now;

        const timer = document.getElementById("timer");

        if(diff <= 0){
            if(timer) timer.innerHTML = "🎬 LIVE NOW";

            const lock = document.getElementById("lock");
            const player = document.getElementById("player");

            if(lock) lock.style.display = "none";
            if(player) player.style.display = "block";
            return;
        }

        const d = Math.floor(diff / 86400);
        const h = Math.floor((diff % 86400) / 3600);
        const m = Math.floor((diff % 3600) / 60);
        const s = diff % 60;

        if(timer){
            timer.innerHTML = `${d}d ${h}h ${m}m ${s}s`;
        }
    }

    update();
    setInterval(update, 1000);
}

/* ---------------- CINEMA MODE v2 ---------------- */
function goCinema(){
    const overlay = document.getElementById("cinemaOverlay");
    const video = document.getElementById("cinemaVideo");

    if(overlay) overlay.style.display = "flex";

    if(video){
        video.play().catch(()=>{});
    }

    const el = document.documentElement;

    if(el.requestFullscreen) el.requestFullscreen();
}

/* EXIT */
function exitCinema(){
    const overlay = document.getElementById("cinemaOverlay");
    if(overlay) overlay.style.display = "none";

    if(document.exitFullscreen) document.exitFullscreen();
}

/* PLAY/PAUSE */
function togglePlay(){
    const video = document.getElementById("cinemaVideo");
    if(!video) return;

    if(video.paused) video.play();
    else video.pause();
}

/* ---------------- ADMIN LIVE AUTO REFRESH ---------------- */
function loadLive(){
    fetch("/admin-data")
    .then(r => r.json())
    .then(data => {
        let html = "";
        data.live.forEach(v => {
            html += `<p>${v.name} | ${v.email}</p>`;
        });

        const box = document.getElementById("live-box");
        if(box) box.innerHTML = html;
    });
}
setInterval(loadLive, 3000);

</script>
"""

# -------------------------
# WATCH PAGE (FIXED GATE + CINEMA READY)
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

    # 🔒 LOCK STATE
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
    """, (ticket_id, now))

    conn.commit()

    # 🎬 CINEMA READY
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

    <div id="cinemaOverlay">
        <video id="cinemaVideo" controls autoplay>
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
# ADMIN (LIVE ENABLED)
# -------------------------
@app.route("/admin", methods=["GET","POST"])
def admin():

    p = request.form.get("pass") or request.args.get("pass")

    if p != ADMIN_PASSWORD:
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
    logs = cursor.fetchall()

    html = "<h1 class='glow'>ADMIN PANEL</h1>"

    html += """
    <div class="card">
        <h2 class="glow">LIVE VIEWERS</h2>
        <div id="live-box">Loading...</div>
    </div>
    """

    for x in logs:
        html += f"<p>{x[1]} | {x[2]}</p>"

    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body onload="loadLive()">
    <div class="container">{html}</div>
    </body>
    </html>
    """

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
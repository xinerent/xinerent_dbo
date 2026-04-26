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
# PREMIERE SETUP — May 1st 2026 at 19:00
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
    SELECT tickets.name, tickets.email
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

/* ---- COUNTDOWN TIMER ---- */
.timer-wrap {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin-top: 40px;
    flex-wrap: wrap;
}
.timer-block {
    display: flex;
    flex-direction: column;
    align-items: center;
}
.timer-number {
    font-size: 90px;
    font-weight: bold;
    color: #d4af37;
    text-shadow: 0 0 30px #d4af37, 0 0 60px rgba(212,175,55,0.4);
    min-width: 140px;
    line-height: 1;
}
.timer-label {
    font-size: 30px;
    color: rgba(255,255,255,0.6);
    margin-top: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
}
.timer-sep {
    font-size: 90px;
    color: #d4af37;
    opacity: 0.5;
    line-height: 1;
    padding-top: 0px;
}
.live-badge {
    font-size: 60px;
    color: #d4af37;
    text-shadow: 0 0 20px #d4af37;
    animation: pulse 1s infinite;
    margin-top: 30px;
}
@keyframes pulse {
    0%,100% { opacity:1; }
    50%      { opacity:0.4; }
}

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
// ---- COUNTDOWN — no page refresh, pure JS ----
function startCountdown(endTime) {
    function pad(n) { return String(n).padStart(2, '0'); }

    function update() {
        var now  = Math.floor(Date.now() / 1000);
        var diff = endTime - now;

        if (diff <= 0) {
            // Hide lock, show player — no reload
            var lock   = document.getElementById("lock");
            var player = document.getElementById("player");
            var badge  = document.getElementById("live-badge");

            if (lock)   lock.style.display   = "none";
            if (player) player.style.display  = "block";
            if (badge)  badge.style.display   = "block";
            return; // stop updating
        }

        var days    = Math.floor(diff / 86400);
        var hours   = Math.floor((diff % 86400) / 3600);
        var minutes = Math.floor((diff % 3600) / 60);
        var seconds = diff % 60;

        var el;
        el = document.getElementById("t-days");    if(el) el.textContent = pad(days);
        el = document.getElementById("t-hours");   if(el) el.textContent = pad(hours);
        el = document.getElementById("t-minutes"); if(el) el.textContent = pad(minutes);
        el = document.getElementById("t-seconds"); if(el) el.textContent = pad(seconds);

        setTimeout(update, 1000);
    }

    update(); // run immediately, then every second via setTimeout
}

function goCinema(){
    var overlay = document.getElementById("cinemaOverlay");
    var video   = document.getElementById("cinemaVideo");
    if(overlay) overlay.style.display = "flex";
    if(video)   video.play().catch(function(){});
    var el = document.documentElement;
    if(el.requestFullscreen) el.requestFullscreen();
}

function exitCinema(){
    var overlay = document.getElementById("cinemaOverlay");
    if(overlay) overlay.style.display = "none";
    if(document.exitFullscreen) document.exitFullscreen();
}

function togglePlay(){
    var video = document.getElementById("cinemaVideo");
    if(!video) return;
    if(video.paused) video.play();
    else video.pause();
}

function loadLive(){
    fetch("/admin-data")
    .then(function(r){ return r.json(); })
    .then(function(data){
        var html = "";
        data.live.forEach(function(v){
            html += "<p>" + v.name + " | " + v.email + "</p>";
        });
        var box = document.getElementById("live-box");
        if(box) box.innerHTML = html;
    });
}
setInterval(loadLive, 3000);
</script>
"""

# -------------------------
# WATCH PAGE
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s", (ticket_id,))
    t = cursor.fetchone()

    if not t:
        return "<h2>Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s", (t[3],))
    film = cursor.fetchone()

    if not film:
        return "<h2>Film not found</h2>"

    now     = int(time.time())
    release = int(film[3])

    if now < release:
        # Premiere not started — show live countdown (no reload)
        return f"""
        <html>
        <head>{BASE_STYLE}</head>
        <body onload="startCountdown({release})">
        <div class="container">
            <h2 class="glow">🔒 PREMIERE LOCKED</h2>
            <div class="card" id="lock">
                <p>Welcome, <span class="glow">{t[1]}</span></p>
                <p style="font-size:32px;color:rgba(255,255,255,0.5);">
                    Premieres Friday, May 1st at 7:00 PM
                </p>

                <!-- countdown blocks -->
                <div class="timer-wrap">
                    <div class="timer-block">
                        <span class="timer-number" id="t-days">--</span>
                        <span class="timer-label">Days</span>
                    </div>
                    <div class="timer-sep">:</div>
                    <div class="timer-block">
                        <span class="timer-number" id="t-hours">--</span>
                        <span class="timer-label">Hours</span>
                    </div>
                    <div class="timer-sep">:</div>
                    <div class="timer-block">
                        <span class="timer-number" id="t-minutes">--</span>
                        <span class="timer-label">Minutes</span>
                    </div>
                    <div class="timer-sep">:</div>
                    <div class="timer-block">
                        <span class="timer-number" id="t-seconds">--</span>
                        <span class="timer-label">Seconds</span>
                    </div>
                </div>
            </div>

            <!-- hidden until premiere starts -->
            <div id="player" style="display:none;" class="card">
                <button onclick="goCinema()">⛶ Enter Cinema Mode</button>
            </div>
            <div id="live-badge" class="live-badge" style="display:none;">🎬 LIVE NOW</div>
        </div>
        </body>
        </html>
        """

    # Premiere already live
    video = film[2]

    cursor.execute("""
    INSERT INTO viewers(ticket_id, last_seen)
    VALUES(%s, %s)
    ON CONFLICT(ticket_id)
    DO UPDATE SET last_seen=EXCLUDED.last_seen
    """, (ticket_id, now))

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
# ADMIN
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

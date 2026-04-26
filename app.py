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
# PREMIERE SETUP — Friday May 1st 2026 at 19:00 (7 PM)
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
    SELECT tickets.name, tickets.email
    FROM viewers
    JOIN tickets ON tickets.id = viewers.ticket_id
    WHERE last_seen > %s
    """, (int(time.time()) - 60,))
    live = cursor.fetchall()
    return jsonify({
        "live": [{"name": x[0], "email": x[1]} for x in live]
    })

# -------------------------
# BASE STYLE + JS
# -------------------------
BASE_STYLE = """
<style>
body {
    margin: 0;
    font-family: Arial;
    background: radial-gradient(circle at top, #050505, #000);
    color: white;
    text-align: center;
}
.container { padding: 80px 20px; }
.card {
    background: #0f0f0f;
    border-radius: 25px;
    padding: 60px;
    margin: 30px auto;
    max-width: 95%;
    border: 1px solid rgba(212,175,55,0.25);
}
h1 { font-size: 110px; }
h2 { font-size: 75px; }
p  { font-size: 40px; }
.glow {
    color: #d4af37;
    text-shadow: 0 0 25px #d4af37;
}
a, button {
    display: block;
    margin-top: 25px;
    padding: 40px;
    font-size: 40px;
    background: linear-gradient(135deg, #d4af37, #f5e6c8);
    color: black;
    border-radius: 20px;
    font-weight: bold;
    border: none !important;
    cursor: pointer;
    text-decoration: none;
}
input {
    width: 95%;
    padding: 35px;
    font-size: 38px;
    border-radius: 15px;
    background: #111;
    color: white;
    border: 1px solid rgba(212,175,55,0.3);
    margin-bottom: 20px;
    box-sizing: border-box;
}

/* ---- TIMER ---- */
.timer-wrap {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 30px;
    margin-top: 40px;
    flex-wrap: wrap;
}
.timer-block {
    display: flex;
    flex-direction: column;
    align-items: center;
}
.timer-number {
    font-size: 100px;
    font-weight: bold;
    color: #d4af37;
    text-shadow: 0 0 30px #d4af37, 0 0 60px rgba(212,175,55,0.4);
    min-width: 160px;
    line-height: 1;
}
.timer-label {
    font-size: 28px;
    color: rgba(255,255,255,0.55);
    margin-top: 10px;
    letter-spacing: 4px;
    text-transform: uppercase;
}
.timer-sep {
    font-size: 100px;
    color: #d4af37;
    opacity: 0.4;
    line-height: 1;
}
.live-badge {
    font-size: 60px;
    color: #d4af37;
    text-shadow: 0 0 20px #d4af37;
    animation: pulse 1s infinite;
    margin-top: 30px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.35; }
}

/* ---- CINEMA PLAYER ---- */
.player-wrap {
    position: relative;
    width: 100%;
    border-radius: 20px;
    overflow: hidden;
    background: #000;
    /* 16:9 ratio */
    aspect-ratio: 16 / 9;
}
.player-wrap iframe {
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 0;
}
/* Cinema toggle button — sits in the corner of the player */
.cinema-btn {
    position: absolute;
    bottom: 14px;
    right: 14px;
    z-index: 10;
    display: flex !important;
    align-items: center;
    gap: 12px;
    padding: 18px 28px !important;
    font-size: 28px !important;
    background: rgba(0,0,0,0.75) !important;
    color: #d4af37 !important;
    border: 2px solid rgba(212,175,55,0.5) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(6px);
    margin-top: 0 !important;
    width: auto !important;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.2s;
}
.cinema-btn:hover {
    background: rgba(212,175,55,0.2) !important;
}
/* Fullscreen: fill the whole screen */
.player-wrap:-webkit-full-screen { width:100vw; height:100vh; aspect-ratio:unset; border-radius:0; }
.player-wrap:-moz-full-screen    { width:100vw; height:100vh; aspect-ratio:unset; border-radius:0; }
.player-wrap:fullscreen          { width:100vw; height:100vh; aspect-ratio:unset; border-radius:0; }
.player-wrap:fullscreen iframe,
.player-wrap:-webkit-full-screen iframe,
.player-wrap:-moz-full-screen iframe {
    position:absolute; top:0; left:0; width:100%; height:100%;
}
</style>

<script>
/* ---- COUNTDOWN ---- */
function startCountdown(endTime) {
    function pad(n) { return String(n).padStart(2, '0'); }
    function update() {
        var now  = Math.floor(Date.now() / 1000);
        var diff = endTime - now;
        if (diff <= 0) {
            var lock   = document.getElementById("lock");
            var player = document.getElementById("player");
            var badge  = document.getElementById("live-badge");
            if (lock)   lock.style.display  = "none";
            if (player) player.style.display = "block";
            if (badge)  badge.style.display  = "block";
            return;
        }
        var days    = Math.floor(diff / 86400);
        var hours   = Math.floor((diff % 86400) / 3600);
        var minutes = Math.floor((diff % 3600) / 60);
        var seconds = diff % 60;
        var el;
        el = document.getElementById("t-days");    if (el) el.textContent = pad(days);
        el = document.getElementById("t-hours");   if (el) el.textContent = pad(hours);
        el = document.getElementById("t-minutes"); if (el) el.textContent = pad(minutes);
        el = document.getElementById("t-seconds"); if (el) el.textContent = pad(seconds);
        setTimeout(update, 1000);
    }
    update();
}

/* ---- CINEMATIC MODE ---- */
function toggleCinema() {
    var wrap = document.getElementById("player-wrap");
    var btn  = document.getElementById("cinema-btn");
    if (!wrap) return;

    var isFs = document.fullscreenElement
            || document.webkitFullscreenElement
            || document.mozFullScreenElement;

    if (!isFs) {
        /* Enter fullscreen on the wrapper div — iframe fills it */
        if (wrap.requestFullscreen)       wrap.requestFullscreen();
        else if (wrap.webkitRequestFullscreen) wrap.webkitRequestFullscreen();
        else if (wrap.mozRequestFullScreen)    wrap.mozRequestFullScreen();
        if (btn) btn.innerHTML = "⊠ Exit Cinema";
    } else {
        if (document.exitFullscreen)            document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
        else if (document.mozCancelFullScreen)  document.mozCancelFullScreen();
        if (btn) btn.innerHTML = "⛶ Cinema Mode";
    }
}

/* sync button label when user presses Escape */
document.addEventListener("fullscreenchange",       syncBtn);
document.addEventListener("webkitfullscreenchange", syncBtn);
document.addEventListener("mozfullscreenchange",    syncBtn);
function syncBtn() {
    var btn = document.getElementById("cinema-btn");
    if (!btn) return;
    var isFs = document.fullscreenElement
            || document.webkitFullscreenElement
            || document.mozFullScreenElement;
    btn.innerHTML = isFs ? "⊠ Exit Cinema" : "⛶ Cinema Mode";
}

/* ---- ADMIN LIVE ---- */
function loadLive() {
    fetch("/admin-data")
    .then(function(r) { return r.json(); })
    .then(function(data) {
        var html = "";
        data.live.forEach(function(v) {
            html += "<p>" + v.name + " | " + v.email + "</p>";
        });
        var box = document.getElementById("live-box");
        if (box) box.innerHTML = html || "<p style='opacity:0.4'>No viewers right now</p>";
    });
}
</script>
"""

# ---- reusable player HTML ----
def player_html(video_url):
    return f"""
<div class="player-wrap" id="player-wrap">
    <iframe
        src="{video_url}?autoplay=1&controls=1"
        allow="autoplay; fullscreen; accelerometer; gyroscope; picture-in-picture"
        allowfullscreen>
    </iframe>
    <button class="cinema-btn" id="cinema-btn" onclick="toggleCinema()">
        ⛶ Cinema Mode
    </button>
</div>
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
    all_films = cursor.fetchall()

    html = f"<html><head>{BASE_STYLE}</head><body><div class='container'>"
    html += "<h2 class='glow'>🎬 Now Showing</h2>"

    for f in all_films:
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (f[0],))
        count = cursor.fetchone()[0]
        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p><span>{count}</span> / {MAX_TICKETS} tickets claimed</p>
        """
        if count >= MAX_TICKETS:
            html += "<p>❌ SOLD OUT</p>"
        else:
            html += f"<a href='/claim/{f[0]}'>🎟 Claim Ticket</a>"
        html += "</div>"

    html += "</div></body></html>"
    return html

# -------------------------
# CLAIM
# -------------------------
@app.route("/claim/<int:film_id>")
def claim(film_id):
    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h2 class="glow">🎟 Claim Your Ticket</h2>
        <div class="card">
            <form action="/submit/{film_id}" method="POST">
                <input name="name" placeholder="Your Name" required>
                <input name="email" placeholder="Your Email" required>
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
    name  = request.form["name"]
    email = request.form["email"]

    cursor.execute("INSERT INTO logins(name,email,time) VALUES(%s,%s,%s)",
                   (name, email, int(time.time())))
    conn.commit()

    cursor.execute("SELECT id FROM tickets WHERE email=%s AND film_id=%s", (email, film_id))
    ex = cursor.fetchone()
    if ex:
        return redirect(f"/watch/{ex[0]}")

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    if cursor.fetchone()[0] >= MAX_TICKETS:
        return f"<html><head>{BASE_STYLE}</head><body><div class='container'><h2>❌ Sold Out</h2></div></body></html>"

    cursor.execute("""
        INSERT INTO tickets(name, email, film_id, created_at)
        VALUES(%s, %s, %s, %s)
        RETURNING id
    """, (name, email, film_id, int(time.time())))

    ticket_id = cursor.fetchone()[0]
    conn.commit()
    return redirect(f"/watch/{ticket_id}")

# -------------------------
# ENTER
# -------------------------
@app.route("/enter", methods=["GET", "POST"])
def enter():
    if request.method == "POST":
        email = request.form["email"]
        cursor.execute("SELECT id FROM tickets WHERE email=%s", (email,))
        t = cursor.fetchone()
        if t:
            return redirect(f"/watch/{t[0]}")
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body><div class="container">
            <div class="card">
                <h2>❌ No ticket found</h2>
                <p>That email does not have a ticket yet.</p>
                <a href="/films">🎟 Get a Ticket</a>
                <a href="/enter">Try Again</a>
            </div>
        </div></body></html>
        """

    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h2 class="glow">🎬 Enter Premiere</h2>
        <div class="card">
            <form method="POST">
                <p>Enter your email to access the premiere</p>
                <input name="email" placeholder="Your email" required>
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
    cursor.execute("SELECT * FROM tickets WHERE id=%s", (ticket_id,))
    t = cursor.fetchone()
    if not t:
        return f"<html><head>{BASE_STYLE}</head><body><div class='container'><h2>❌ Invalid Ticket</h2></div></body></html>"

    cursor.execute("SELECT * FROM films WHERE id=%s", (t[3],))
    film = cursor.fetchone()
    if not film:
        return f"<html><head>{BASE_STYLE}</head><body><div class='container'><h2>❌ Film not found</h2></div></body></html>"

    now     = int(time.time())
    release = int(film[3])
    video   = film[2]

    cursor.execute("""
    INSERT INTO viewers(ticket_id, last_seen)
    VALUES(%s, %s)
    ON CONFLICT(ticket_id)
    DO UPDATE SET last_seen = EXCLUDED.last_seen
    """, (ticket_id, now))
    conn.commit()

    # ---- COUNTDOWN PAGE (premiere not started yet) ----
    if now < release:
        return f"""
        <html>
        <head>{BASE_STYLE}</head>
        <body onload="startCountdown({release})">
        <div class="container">
            <h2 class="glow">🔒 PREMIERE LOCKED</h2>
            <div class="card" id="lock">
                <p>Welcome, <span class="glow">{t[1]}</span></p>
                <p style="font-size:32px; color:rgba(255,255,255,0.5); margin-top:0;">
                    Premieres Friday, May 1st at 7:00 PM
                </p>
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

            <!-- Hidden until countdown hits zero — no reload needed -->
            <div id="player" style="display:none;" class="card">
                {player_html(video)}
            </div>
            <div id="live-badge" class="live-badge" style="display:none;">🎬 LIVE NOW</div>
        </div>
        </body>
        </html>
        """

    # ---- LIVE PAGE (premiere already started) ----
    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h2 class="glow">🎬 PREMIERE ROOM</h2>
        <div class="live-badge">🎬 LIVE NOW</div>
        <div class="card">
            <p>Welcome, <span class="glow">{t[1]}</span></p>
            {player_html(video)}
        </div>
    </div>
    </body>
    </html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    p = request.form.get("pass") or request.args.get("pass")

    if p != ADMIN_PASSWORD:
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body>
        <div class="container">
            <h2 class="glow">🔐 ADMIN LOGIN</h2>
            <div class="card">
                <form method="POST">
                    <input name="pass" type="password" placeholder="Password">
                    <button>Unlock</button>
                </form>
            </div>
        </div>
        </body></html>
        """

    cursor.execute("SELECT * FROM logins ORDER BY id DESC")
    logs = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]

    html  = "<h1 class='glow'>ADMIN PANEL</h1>"
    html += f"<p>Total tickets: <span class='glow'>{total_tickets} / {MAX_TICKETS}</span></p>"
    html += """
    <div class="card">
        <h2 class="glow">🟢 LIVE VIEWERS</h2>
        <div id="live-box"><p style="opacity:0.4">Loading...</p></div>
    </div>
    <div class="card">
        <h2 class="glow">📋 ALL REGISTRATIONS</h2>
    """
    for x in logs:
        html += f"<p>{x[1]} | {x[2]}</p>"
    html += "</div>"

    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body onload="loadLive(); setInterval(loadLive, 3000)">
    <div class="container">{html}</div>
    </body>
    </html>
    """

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

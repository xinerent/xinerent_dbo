from flask import Flask, request, redirect
import sqlite3
import time
import os
import datetime
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# -------------------------
# DATABASE
# -------------------------
conn = sqlite3.connect("dbo.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    film_id INTEGER,
    created_at INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    youtube_link TEXT,
    release_time INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS viewers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    last_seen INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS email_log (
    ticket_id INTEGER PRIMARY KEY,
    sent INTEGER
)
""")

conn.commit()

# -------------------------
# PREMIERE TIME
# -------------------------
release_time = int(datetime.datetime(2026, 4, 24, 19, 0).timestamp())

cursor.execute("SELECT COUNT(*) FROM films")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
    INSERT INTO films (title, youtube_link, release_time)
    VALUES (?, ?, ?)
    """, (
        "XineRent Premiere Film",
        "https://www.youtube.com/embed/-AUw43bmMWQ",
        release_time
    ))
    conn.commit()

# -------------------------
# SETTINGS
# -------------------------
MAX_TICKETS = 700
ADMIN_PASSWORD = "Muha&123"

# -------------------------
# EMAIL SYSTEM
# -------------------------
def send_email(to_email, subject, message):
    sender_email = "YOUR_EMAIL@gmail.com"
    app_password = "YOUR_APP_PASSWORD"

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email error:", e)

# -------------------------
# UI (BIGGER + WHITE + GOLD)
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: Arial;
    background: radial-gradient(circle at top, #050505, #000);
    color: #ffffff;
    text-align: center;
    font-size: 34px;
}

.container { padding: 70px 20px; }

.card {
    background: #0f0f0f;
    border-radius: 28px;
    padding: 50px;
    margin: 35px auto;
    max-width: 98%;
    border: 1px solid rgba(212,175,55,0.3);
}

h1 { font-size: 90px; }
h2 { font-size: 65px; }
p  { font-size: 34px; }

.glow {
    color: #d4af37;
    text-shadow: 0 0 25px #d4af37;
}

/* BIG TIMER FIX */
.timer {
    font-size: 110px;
    color: white;
    font-weight: bold;
    text-shadow: 0 0 25px #fff;
}

/* BUTTONS */
a, button {
    display: block;
    margin-top: 30px;
    padding: 35px;
    background: linear-gradient(135deg, #d4af37, #f5e6c8);
    color: black;
    border-radius: 22px;
    font-size: 38px;
    font-weight: bold;
    text-decoration: none;
}

/* INPUT */
input {
    width: 95%;
    padding: 30px;
    font-size: 34px;
    background: #111;
    color: white;
    border: 1px solid #333;
    border-radius: 15px;
}

/* VIDEO */
.video-box iframe {
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 20px;
}

/* LIVE DOT */
.live {
    color: #00ff88;
    font-weight: bold;
}
</style>
"""

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return f"""
    <html><head>{BASE_STYLE}</head><body>
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
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=?", (f[0],))
        count = cursor.fetchone()[0]

        button = "<p>❌ SOLD OUT</p>" if count >= MAX_TICKETS else f"<a href='/claim/{f[0]}'>🎟 Claim Ticket</a>"

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p class="glow">Official Selection – Cinebration International Film Festival 2026</p>
            <p>{count}/{MAX_TICKETS} tickets</p>
            {button}
        </div>
        """

    return html + "</div></body></html>"

# -------------------------
# CLAIM
# -------------------------
@app.route("/claim/<int:film_id>")
def claim(film_id):
    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎟 Claim Ticket</h2>
        <div class="card">
            <form action="/submit/{film_id}" method="POST">
                <input name="name" placeholder="Your Name" required>
                <input name="email" placeholder="Email" required>
                <button type="submit">Get Ticket</button>
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
    name = request.form.get("name")
    email = request.form.get("email")

    cursor.execute("SELECT id FROM tickets WHERE email=? AND film_id=?", (email, film_id))
    existing = cursor.fetchone()

    if existing:
        return redirect(f"/watch/{existing[0]}")

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=?", (film_id,))
    count = cursor.fetchone()[0]

    if count >= MAX_TICKETS:
        return "<h2>❌ SOLD OUT</h2>"

    cursor.execute("""
    INSERT INTO tickets (name, email, film_id, created_at)
    VALUES (?, ?, ?, ?)
    """, (name, email, film_id, int(time.time())))
    conn.commit()

    ticket_id = cursor.lastrowid

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# ENTER
# -------------------------
@app.route("/enter", methods=["GET", "POST"])
def enter():
    if request.method == "POST":
        email = request.form.get("email")

        cursor.execute("SELECT id FROM tickets WHERE email=?", (email,))
        ticket = cursor.fetchone()

        if ticket:
            return redirect(f"/watch/{ticket[0]}")
        return "<h2>❌ No ticket found</h2>"

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎬 Enter Premiere</h2>
        <div class="card">
            <form method="POST">
                <input name="email" placeholder="Enter email" required>
                <button type="submit">Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH (FIXED TIMER + LIVE VIEWERS + EMAIL SAFE)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    ticket = cursor.fetchone()
    if not ticket:
        return "<h2>❌ Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=?", (ticket[3],))
    film = cursor.fetchone()

    now = int(time.time())

    # LIVE VIEWERS UPDATE
    cursor.execute("""
    INSERT OR REPLACE INTO viewers (ticket_id, last_seen)
    VALUES (?, ?)
    """, (ticket_id, now))
    conn.commit()

    # PRE PREMIERE
    if now < film[3]:
        remaining = film[3] - now
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <h2 class="glow">⏳ PREMIERE LOCKED</h2>
            <div class="card">
                <p>Welcome {ticket[1]}</p>
                <div class="timer">{remaining//3600}h {(remaining%3600)//60}m</div>
            </div>
        </div>
        </body></html>
        """

    # EMAIL ONLY ONCE
    cursor.execute("SELECT sent FROM email_log WHERE ticket_id=?", (ticket_id,))
    sent = cursor.fetchone()

    if not sent:
        send_email(
            ticket[2],
            "🎬 PREMIERE IS LIVE",
            f"Hi {ticket[1]}, the premiere has started. Join now!"
        )
        cursor.execute("INSERT INTO email_log VALUES (?,1)", (ticket_id,))
        conn.commit()

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎬 LIVE PREMIERE</h2>
        <div class="card video-box">
            <iframe src="{film[2]}" allowfullscreen></iframe>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# ADMIN (FIXED LOGIN UI + LIVE VIEWERS)
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    pass_input = request.args.get("pass") or request.form.get("pass")

    if pass_input != ADMIN_PASSWORD:
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <h2 class="glow">🔐 ADMIN LOGIN</h2>
            <div class="card">
                <form method="GET">
                    <input name="pass" type="password" placeholder="Enter Password">
                    <button type="submit">Unlock</button>
                </form>
            </div>
        </div>
        </body></html>
        """

    now = int(time.time())
    cutoff = now - 60

    cursor.execute("""
    SELECT tickets.name, tickets.email
    FROM viewers
    JOIN tickets ON tickets.id = viewers.ticket_id
    WHERE viewers.last_seen > ?
    """, (cutoff,))
    live = cursor.fetchall()

    cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
    users = cursor.fetchall()

    html = "<h1 class='glow'>🎟 ADMIN PANEL</h1>"

    html += f"<h2>🟢 LIVE VIEWERS ({len(live)})</h2>"

    for v in live:
        html += f"<div class='card'><p class='live'>{v[0]} ({v[1]})</p></div>"

    html += "<h2>🎟 ALL TICKETS</h2>"

    for u in users:
        html += f"""
        <div class="card">
            <p>ID: {u[0]}</p>
            <p>{u[1]}</p>
            <p>{u[2]}</p>
        </div>
        """

    return f"<html><head>{BASE_STYLE}</head><body><div class='container'>{html}</div></body></html>"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
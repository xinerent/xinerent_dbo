from flask import Flask, request, redirect
import time
import os
import datetime
import smtplib
from email.mime.text import MIMEText
import psycopg2

app = Flask(__name__)

# -------------------------
# DATABASE (POSTGRES - RENDER)
# -------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS email_log (
    ticket_id INTEGER PRIMARY KEY,
    sent INTEGER
)
""")

# -------------------------
# TIME FORMAT FUNCTION
# -------------------------
def format_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d %b %Y %I:%M %p")

# -------------------------
# PREMIERE TIME
# -------------------------
release_time = int(datetime.datetime(2026, 4, 24, 19, 0).timestamp())

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
# CINEMATIC UI UPGRADE (EDGE / GLOW / FILM FEEL)
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: radial-gradient(circle at top, #0a0a0a, #000000 60%);
    color: #ffffff;
    text-align: center;
    font-size: 34px;
}

/* cinematic grain overlay */
body::before {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: url('https://www.transparenttextures.com/patterns/noise.png');
    opacity: 0.08;
    pointer-events: none;
}

.container {
    padding: 70px 20px;
}

.card {
    background: linear-gradient(145deg, #0f0f0f, #070707);
    border-radius: 28px;
    padding: 50px;
    margin: 35px auto;
    max-width: 98%;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 0 40px rgba(0,0,0,0.7), inset 0 0 15px rgba(255,255,255,0.03);
    color: #ffffff !important;
}

/* cinematic glow edge */
.card:hover {
    box-shadow: 0 0 60px rgba(255,255,255,0.08), 0 0 120px rgba(0,0,0,0.9);
    transform: scale(1.01);
    transition: 0.3s ease;
}

.card p,
.card b,
.card span,
.card div,
.card h1,
.card h2,
.card h3 {
    color: #ffffff !important;
}

h1 { font-size: 90px; letter-spacing: 2px; }
h2 { font-size: 65px; letter-spacing: 1px; }
p  { font-size: 34px; opacity: 0.9; }

.glow {
    color: #ffffff;
    text-shadow: 0 0 10px rgba(255,255,255,0.3),
                 0 0 30px rgba(255,255,255,0.1);
}

a, button {
    display: block;
    margin-top: 30px;
    padding: 35px;
    background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
    color: white;
    border-radius: 22px;
    font-size: 38px;
    font-weight: bold;
    text-decoration: none;
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 0 25px rgba(0,0,0,0.6);
}

a:hover, button:hover {
    box-shadow: 0 0 40px rgba(255,255,255,0.15);
    transform: scale(1.02);
}

input {
    width: 95%;
    padding: 30px;
    font-size: 34px;
    background: #111;
    color: white;
    border: 1px solid #333;
    border-radius: 15px;
}

.video-box iframe {
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 18px;
    box-shadow: 0 0 60px rgba(0,0,0,0.9);
}

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
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (f[0],))
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

    cursor.execute("INSERT INTO logins (name,email,time) VALUES (%s,%s,%s)",
                   (name, email, int(time.time())))

    cursor.execute("SELECT id FROM tickets WHERE email=%s AND film_id=%s", (email, film_id))
    existing = cursor.fetchone()

    if existing:
        return redirect(f"/watch/{existing[0]}")

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    count = cursor.fetchone()[0]

    if count >= MAX_TICKETS:
        return "<h2>❌ SOLD OUT</h2>"

    cursor.execute("""
    INSERT INTO tickets (name,email,film_id,created_at)
    VALUES (%s,%s,%s,%s)
    """, (name, email, film_id, int(time.time())))

    cursor.execute("SELECT id FROM tickets WHERE email=%s AND film_id=%s ORDER BY id DESC LIMIT 1",
                   (email, film_id))
    ticket_id = cursor.fetchone()[0]

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# ENTER
# -------------------------
@app.route("/enter", methods=["GET", "POST"])
def enter():
    if request.method == "POST":
        email = request.form.get("email")

        cursor.execute("SELECT id FROM tickets WHERE email=%s", (email,))
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
# WATCH (NO TIMER - CINEMATIC ONLY)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s", (ticket_id,))
    ticket = cursor.fetchone()

    if not ticket:
        return "<h2>❌ Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s", (ticket[3],))
    film = cursor.fetchone()

    now = int(time.time())

    cursor.execute("""
    INSERT INTO viewers (ticket_id,last_seen)
    VALUES (%s,%s)
    ON CONFLICT (ticket_id)
    DO UPDATE SET last_seen=%s
    """, (ticket_id, now, now))

    if now < film[3]:
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <h2 class="glow">🎬 CINEMA EXPERIENCE</h2>
            <div class="card">
                <p>Welcome {ticket[1]}</p>
                <p class="glow">Your premiere will begin soon...</p>
                <p>Feel the cinematic world building up 🎥</p>
            </div>
        </div>
        </body></html>
        """

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
# ADMIN
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

    cutoff = int(time.time()) - 60

    cursor.execute("""
    SELECT tickets.name, tickets.email
    FROM viewers
    JOIN tickets ON tickets.id = viewers.ticket_id
    WHERE viewers.last_seen > %s
    """, (cutoff,))
    live_users = cursor.fetchall()

    cursor.execute("SELECT * FROM logins ORDER BY id DESC")
    logins = cursor.fetchall()

    html = "<h1 class='glow'>🎟 ADMIN PANEL</h1>"
    html += f"<h2>🟢 LIVE VIEWERS ({len(live_users)})</h2>"

    for v in live_users:
        html += f"<div class='card'><p class='live'>{v[0]} ({v[1]})</p></div>"

    html += "<h2>👤 USERS (JOIN HISTORY)</h2>"

    for l in logins:
        html += f"""
        <div class="card">
            <p><b>Name:</b> {l[1]}</p>
            <p><b>Email:</b> {l[2]}</p>
            <p><b>Joined:</b> {format_time(l[3])}</p>
        </div>
        """

    return f"<html><head>{BASE_STYLE}</head><body><div class='container'>{html}</div></body></html>"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
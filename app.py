from flask import Flask, request, redirect
import time
import os
import datetime
import smtplib
from email.mime.text import MIMEText
import psycopg2

app = Flask(__name__)

# -------------------------
# DATABASE (POSTGRES - SAFE CONNECTION)
# -------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set")

def get_cursor():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn.cursor()

# -------------------------
# INIT DATABASE
# -------------------------
def init_db():
    cursor = get_cursor()

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

init_db()

# -------------------------
# TIME FORMAT FUNCTION
# -------------------------
def format_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d %b %Y %I:%M %p")

# -------------------------
# PREMIERE TIME
# -------------------------
release_time = int(datetime.datetime(2026, 4, 24, 19, 0).timestamp())

cursor = get_cursor()
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
# CINEMATIC + ANTI PIRACY UI
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: radial-gradient(circle at top, #050505, #000);
    color: #fff;
    text-align: center;
    font-size: 34px;
    overflow-x: hidden;
}

body::before {
    content: "";
    position: fixed;
    width: 100%;
    height: 100%;
    background: url('https://www.transparenttextures.com/patterns/noise.png');
    opacity: 0.07;
    pointer-events: none;
}

body::after {
    content: "XineRent • Protected Screening";
    position: fixed;
    bottom: 20px;
    right: 20px;
    font-size: 18px;
    color: rgba(255,255,255,0.15);
    pointer-events: none;
}

.container { padding: 70px 20px; }

.card {
    background: linear-gradient(145deg, #0f0f0f, #070707);
    border-radius: 28px;
    padding: 50px;
    margin: 35px auto;
    max-width: 98%;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 0 60px rgba(0,0,0,0.8);
}

h1 { font-size: 90px; }
h2 { font-size: 65px; }

a, button {
    display: block;
    margin-top: 30px;
    padding: 35px;
    background: #1a1a1a;
    color: white;
    border-radius: 22px;
    font-size: 38px;
    font-weight: bold;
    text-decoration: none;
    border: 1px solid rgba(255,255,255,0.1);
}

.video-box {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 18px;
    overflow: hidden;
}

.video-box iframe {
    width: 100%;
    height: 100%;
    border: none;
}

.fs-btn {
    margin-top: 20px;
    padding: 20px;
    font-size: 28px;
    background: black;
    border: 1px solid white;
    color: white;
}
</style>

<script>
document.addEventListener("contextmenu", event => event.preventDefault());

function goFull() {
    let frame = document.getElementById("cineFrame");
    if (frame.requestFullscreen) {
        frame.requestFullscreen();
    } else if (frame.webkitRequestFullscreen) {
        frame.webkitRequestFullscreen();
    }
}
</script>
"""

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h1>🎬 XineRent</h1>
        <div class="card">
            <a href="/films">🎟 Get Ticket</a>
            <a href="/enter">🎬 Enter Premiere</a>
            <a href="/admin">🔐 Admin</a>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# FILMS
# -------------------------
@app.route("/films")
def films():
    cursor = get_cursor()
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
    cursor = get_cursor()
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
        cursor = get_cursor()
        email = request.form.get("email")

        cursor.execute("SELECT id FROM tickets WHERE email=%s", (email,))
        ticket = cursor.fetchone()

        if ticket:
            return redirect(f"/watch/{ticket[0]}")
        return "<h2>❌ No ticket found</h2>"

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
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
# WATCH
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):
    cursor = get_cursor()

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

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <div class="card">
            <p>Welcome {ticket[1]}</p>

            <div class="video-box">
                <iframe id="cineFrame" src="{film[2]}" allowfullscreen></iframe>
            </div>

            <button class="fs-btn" onclick="goFull()">⛶ Fullscreen</button>
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
        return "<h2>Login Required</h2>"

    cursor = get_cursor()

    cursor.execute("""
    SELECT tickets.name, tickets.email
    FROM viewers
    JOIN tickets ON tickets.id = viewers.ticket_id
    """)
    live_users = cursor.fetchall()

    html = "<h1>ADMIN PANEL</h1>"

    for v in live_users:
        html += f"<p>{v[0]} ({v[1]})</p>"

    return html

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
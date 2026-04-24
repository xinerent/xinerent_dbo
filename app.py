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
        "https://www.youtube.com/embed/-AUw43bmMWQ?autoplay=1&mute=0",
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
# GOLD CINEMATIC UI
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: 'Georgia', serif;
    background: radial-gradient(circle at top, #1a1200, #000000 70%);
    color: #f5e6c8;
    text-align: center;
    font-size: 34px;
}

/* film grain */
body::before {
    content: "";
    position: fixed;
    width: 100%;
    height: 100%;
    background: url('https://www.transparenttextures.com/patterns/noise.png');
    opacity: 0.08;
    pointer-events: none;
}

/* gold watermark */
body::after {
    content: "XineRent Private Screening";
    position: fixed;
    bottom: 20px;
    right: 20px;
    font-size: 16px;
    color: rgba(212,175,55,0.25);
    pointer-events: none;
}

.container {
    padding: 70px 20px;
}

.card {
    background: linear-gradient(145deg, #0f0c02, #1a1405);
    border-radius: 30px;
    padding: 50px;
    margin: 35px auto;
    max-width: 98%;
    border: 1px solid rgba(212,175,55,0.3);
    box-shadow: 0 0 50px rgba(212,175,55,0.15), inset 0 0 20px rgba(212,175,55,0.05);
}

/* glow edge */
.card:hover {
    box-shadow: 0 0 80px rgba(212,175,55,0.3);
    transform: scale(1.01);
    transition: 0.3s ease;
}

h1 {
    font-size: 90px;
    color: #d4af37;
    text-shadow: 0 0 30px rgba(212,175,55,0.6);
}

h2 {
    font-size: 65px;
    color: #f5e6c8;
}

p {
    font-size: 34px;
    opacity: 0.95;
}

.glow {
    color: #d4af37;
    text-shadow: 0 0 15px rgba(212,175,55,0.6);
}

a, button {
    display: block;
    margin-top: 30px;
    padding: 35px;
    background: linear-gradient(135deg, #d4af37, #f5e6c8);
    color: black;
    border-radius: 22px;
    font-size: 34px;
    font-weight: bold;
    text-decoration: none;
    border: none;
}

a:hover, button:hover {
    transform: scale(1.03);
    box-shadow: 0 0 30px rgba(212,175,55,0.5);
}

input {
    width: 95%;
    padding: 30px;
    font-size: 34px;
    background: #111;
    color: #f5e6c8;
    border: 1px solid rgba(212,175,55,0.3);
    border-radius: 15px;
}

/* cinematic player */
.video-box {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 0 120px rgba(212,175,55,0.3);
}

.video-box iframe {
    width: 100%;
    height: 100%;
    border: none;
}

/* fullscreen button */
.fs-btn {
    margin-top: 25px;
    padding: 20px;
    font-size: 26px;
    background: black;
    border: 1px solid #d4af37;
    color: #d4af37;
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
        <h1>XineRent</h1>
        <div class="card">
            <a href="/films">Access Premiere</a>
            <a href="/enter">Enter Screening</a>
            <a href="/admin">Admin Panel</a>
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

        button = "<p>Sold Out</p>" if count >= MAX_TICKETS else f"<a href='/claim/{f[0]}'>Reserve Access</a>"

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p class="glow">Digital Premiere Experience</p>
            <p>{count}/{MAX_TICKETS}</p>
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
                <button type="submit">Secure Access</button>
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

    cursor.execute("INSERT INTO tickets (name,email,film_id,created_at) VALUES (%s,%s,%s,%s)",
                   (name, email, film_id, int(time.time())))

    cursor.execute("SELECT id FROM tickets WHERE email=%s AND film_id=%s ORDER BY id DESC LIMIT 1",
                   (email, film_id))
    ticket_id = cursor.fetchone()[0]

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# WATCH (INSTANT PLAY)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s", (ticket_id,))
    ticket = cursor.fetchone()

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
            <div class="video-box">
                <iframe id="cineFrame" src="{film[2]}" allow="autoplay; fullscreen"></iframe>
            </div>
            <button class="fs-btn" onclick="goFull()">Enter Full Cinema</button>
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

    cursor.execute("SELECT name,email FROM tickets")
    users = cursor.fetchall()

    html = "<h1>Admin Panel</h1>"

    for u in users:
        html += f"<p>{u[0]} - {u[1]}</p>"

    return html

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
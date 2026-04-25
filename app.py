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

cursor.execute("""
CREATE TABLE IF NOT EXISTS email_log (
    ticket_id INTEGER PRIMARY KEY,
    sent INTEGER
)
""")

conn.commit()

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
row = cursor.fetchone()

if not row or row[0] == 0:
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
# REAL-TIME COUNTER API
# -------------------------
@app.route("/ticket-count/<int:film_id>")
def ticket_count(film_id):
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    result = cursor.fetchone()
    count = result[0] if result else 0
    return jsonify({"count": count})

# -------------------------
# UI
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
    color: #ffffff !important;
    box-shadow: 0 0 40px rgba(0,0,0,0.8);
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

h1 { font-size: 90px; }
h2 { font-size: 65px; }
p  { font-size: 34px; }

.glow {
    color: #d4af37;
    text-shadow: 0 0 25px #d4af37;
}

.cinema-frame {
    background: radial-gradient(circle, rgba(212,175,55,0.15), transparent);
    padding: 25px;
    border-radius: 30px;
    box-shadow: 0 0 60px rgba(0,0,0,0.9), 0 0 25px rgba(212,175,55,0.2);
}

.video-box iframe {
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 18px;
    border: 2px solid rgba(212,175,55,0.25);
}

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

input {
    width: 95%;
    padding: 30px;
    font-size: 34px;
    background: #111;
    color: white;
    border: 1px solid #333;
    border-radius: 15px;
}

.live {
    color: #00ff88;
    font-weight: bold;
}
</style>

<script>
function animateCounter(id, newValue) {
    const el = document.getElementById(id);
    if (!el) return;

    let current = parseInt(el.innerText) || 0;
    let target = newValue;

    let step = (target - current) / 20;
    let i = 0;

    let interval = setInterval(() => {
        i++;
        current += step;
        el.innerText = Math.floor(current);

        if (i >= 20) {
            el.innerText = target;
            clearInterval(interval);
        }
    }, 50);
}

function refreshTicketCount(filmId) {
    fetch("/ticket-count/" + filmId)
        .then(res => res.json())
        .then(data => {
            const el = document.getElementById("ticket-count");
            if (!el) return;

            const current = parseInt(el.innerText);
            if (current !== data.count) {
                animateCounter("ticket-count", data.count);
            }
        });
}

setInterval(() => {
    if (window.FILM_ID) {
        refreshTicketCount(window.FILM_ID);
    }
}, 3000);
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

            <p>
                <span id="ticket-count">{count}</span>/{MAX_TICKETS} tickets
            </p>

            <script>
                window.FILM_ID = {f[0]};
            </script>

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
                <input name="name" required>
                <input name="email" required>
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
    conn.commit()

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
                <input name="email" required>
                <button type="submit">Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH (FIXED HERE ONLY)
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
    INSERT INTO viewers (ticket_id, last_seen)
    VALUES (%s, %s)
    ON CONFLICT (ticket_id)
    DO UPDATE SET last_seen = %s
    """, (ticket_id, now, now))

    conn.commit()

    cursor.execute("DELETE FROM viewers WHERE last_seen < %s", (now - 60,))
    conn.commit()

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎬 LIVE PREMIERE</h2>

        <div class="cinema-frame">
            <div class="card video-box">
                <iframe src="{film[2]}" allowfullscreen></iframe>
            </div>
        </div>

    </div>
    </body></html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    pass_input = request.form.get("pass") or request.args.get("pass")

    if pass_input != ADMIN_PASSWORD:
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <h2 class="glow">🔐 ADMIN LOGIN</h2>
            <div class="card">
                <form method="POST">
                    <input name="pass" type="password">
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

    html = "<h1>ADMIN PANEL</h1>"

    for v in live_users:
        html += f"<div class='card'>{v[0]} {v[1]}</div>"

    return f"<html><head>{BASE_STYLE}</head><body>{html}</body></html>"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
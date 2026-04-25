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
# TIME FORMAT
# -------------------------
def format_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d %b %Y %I:%M %p")

# -------------------------
# PREMIERE
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
# REAL TIME COUNT
# -------------------------
@app.route("/ticket-count/<int:film_id>")
def ticket_count(film_id):
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    count = cursor.fetchone()[0]
    return jsonify({"count": count})

# -------------------------
# UI UPGRADE (FULL PLATFORM DESIGN)
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: Arial;
    background: #000;
    color: #fff;
    text-align: center;
}

/* GLOBAL LAYOUT */
.container {
    padding: 60px 20px;
}

/* CARDS */
.card {
    background: #0b0b0b;
    border-radius: 24px;
    padding: 40px;
    margin: 25px auto;
    max-width: 900px;
    border: 1px solid rgba(212,175,55,0.25);
    box-shadow: 0 0 25px rgba(0,0,0,0.8);
    color: #fff;
    overflow-wrap: break-word;
    word-break: break-word;
}

/* TEXT */
h1 { font-size: 70px; }
h2 { font-size: 45px; }
p  { font-size: 22px; }

.glow {
    color: #d4af37;
    text-shadow: 0 0 20px #d4af37;
}

/* BUTTONS */
a, button {
    display: block;
    margin-top: 20px;
    padding: 25px;
    background: linear-gradient(135deg, #d4af37, #f5e6c8);
    color: black;
    border-radius: 16px;
    font-size: 24px;
    font-weight: bold;
    text-decoration: none;
    border: none;
}

/* INPUT */
input {
    width: 100%;
    padding: 20px;
    font-size: 20px;
    margin-top: 10px;
    background: #111;
    color: white;
    border-radius: 12px;
    border: 1px solid #333;
}

/* CINEMA */
.cinema-frame {
    background: rgba(212,175,55,0.08);
    padding: 20px;
    border-radius: 20px;
}

.video-box iframe {
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 16px;
}

/* ADMIN DARK MODE FIX */
.admin-card {
    background: #000 !important;
    color: #fff !important;
    border: 1px solid #222;
}

.admin-card p,
.admin-card h1,
.admin-card h2,
.admin-card span {
    color: #fff !important;
}

.live {
    color: #00ff88;
    font-weight: bold;
}
</style>

<script>
function animateCounter(id, value) {
    const el = document.getElementById(id);
    if (!el) return;

    let current = parseInt(el.innerText) || 0;
    let step = (value - current) / 15;

    let i = 0;
    let interval = setInterval(() => {
        i++;
        current += step;
        el.innerText = Math.floor(current);

        if (i >= 15) {
            el.innerText = value;
            clearInterval(interval);
        }
    }, 40);
}

function refresh(filmId) {
    fetch("/ticket-count/" + filmId)
        .then(r => r.json())
        .then(d => {
            const el = document.getElementById("ticket-count");
            if (!el) return;

            const current = parseInt(el.innerText);
            if (current !== d.count) {
                animateCounter("ticket-count", d.count);
            }
        });
}

setInterval(() => {
    if (window.FILM_ID) refresh(window.FILM_ID);
}, 2500);
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

        btn = "<p>❌ SOLD OUT</p>" if count >= MAX_TICKETS else f"<a href='/claim/{f[0]}'>🎟 Claim Ticket</a>"

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p><span id="ticket-count">{count}</span> / {MAX_TICKETS}</p>
            <script>window.FILM_ID={f[0]}</script>
            {btn}
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
            <h2 class="glow">🎟 Claim Ticket</h2>
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

    cursor.execute("INSERT INTO logins (name,email,time) VALUES (%s,%s,%s)",
                   (name, email, int(time.time())))
    conn.commit()

    cursor.execute("SELECT id FROM tickets WHERE email=%s AND film_id=%s", (email, film_id))
    existing = cursor.fetchone()

    if existing:
        return redirect(f"/watch/{existing[0]}")

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    if cursor.fetchone()[0] >= MAX_TICKETS:
        return "<h2>Sold Out</h2>"

    cursor.execute("""
    INSERT INTO tickets (name,email,film_id,created_at)
    VALUES (%s,%s,%s,%s)
    RETURNING id
    """, (name, email, film_id, int(time.time())))

    ticket_id = cursor.fetchone()[0]
    conn.commit()

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# WATCH (CINEMA EXPERIENCE)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s", (ticket_id,))
    ticket = cursor.fetchone()

    if not ticket:
        return "<h2>Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s", (ticket[3],))
    film = cursor.fetchone()

    now = int(time.time())

    cursor.execute("""
    INSERT INTO viewers (ticket_id,last_seen)
    VALUES (%s,%s)
    ON CONFLICT (ticket_id)
    DO UPDATE SET last_seen=%s
    """, (ticket_id, now, now))

    conn.commit()

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎬 LIVE CINEMA</h2>

        <div class="card cinema-frame">
            <div class="video-box">
                <iframe src="{film[2]}" allowfullscreen></iframe>
            </div>
        </div>

    </div>
    </body></html>
    """

# -------------------------
# ADMIN (FULL DARK DASHBOARD FIXED)
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    pass_input = request.form.get("pass") or request.args.get("pass")

    if pass_input != ADMIN_PASSWORD:
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <div class="card">
                <h2 class="glow">Admin Login</h2>
                <form method="POST">
                    <input name="pass" type="password">
                    <button>Enter</button>
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
    live = cursor.fetchall()

    cursor.execute("SELECT * FROM logins ORDER BY id DESC")
    logs = cursor.fetchall()

    html = "<h1 class='glow'>ADMIN DASHBOARD</h1>"

    html += f"<h2>LIVE ({len(live)})</h2>"

    for v in live:
        html += f"<div class='card admin-card'><p>{v[0]}</p><p>{v[1]}</p></div>"

    html += "<h2>USERS</h2>"

    for l in logs:
        html += f"""
        <div class="card admin-card">
            <p>Name: {l[1]}</p>
            <p>Email: {l[2]}</p>
            <p>{format_time(l[3])}</p>
        </div>
        """

    return f"<html><head>{BASE_STYLE}</head><body><div class='container'>{html}</div></body></html>"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
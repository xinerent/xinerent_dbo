from flask import Flask, request, redirect
import sqlite3
import time
import os
import datetime

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

conn.commit()

# -------------------------
# PREMIERE TIME (APRIL 24, 7PM)
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
# 🎬 CINEMATIC GOLD UI
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: 'Segoe UI', Arial;
    background: radial-gradient(circle at top, #050505, #000);
    color: #f5e6c8;
    text-align: center;
    font-size: 30px;
}

.container {
    padding: 50px 20px;
}

/* GOLD CARD */
.card {
    background: linear-gradient(145deg, #0a0a0a, #111);
    border-radius: 28px;
    padding: 40px;
    margin: 30px auto;
    max-width: 95%;
    box-shadow:
        0 0 60px rgba(0,0,0,1),
        0 0 20px rgba(212,175,55,0.2);
    border: 1px solid rgba(212,175,55,0.25);
}

/* BIG HEADINGS */
h1 { font-size: 64px; }
h2 { font-size: 46px; }
p  { font-size: 28px; }

/* GOLD GLOW TEXT */
.glow {
    color: #d4af37;
    text-shadow: 0 0 10px #d4af37, 0 0 30px rgba(212,175,55,0.6);
}

/* BUTTONS */
a, button {
    display: block;
    margin-top: 24px;
    padding: 26px;
    background: linear-gradient(135deg, #d4af37, #f5e6c8);
    color: black;
    border-radius: 18px;
    font-weight: bold;
    font-size: 28px;
    text-decoration: none;
    border: none;
    box-shadow: 0 10px 30px rgba(212,175,55,0.5);
}

/* INPUT */
input {
    width: 96%;
    padding: 24px;
    margin: 16px 0;
    border-radius: 16px;
    border: none;
    font-size: 26px;
    background: #111;
    color: #f5e6c8;
}

/* VIDEO */
.video-box iframe {
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 20px;
}

/* BADGE */
.badge {
    font-size: 24px;
    color: #d4af37;
}

/* MOBILE BOOST */
@media (max-width: 480px) {
    body { font-size: 32px; }
    h1 { font-size: 70px; }
    h2 { font-size: 50px; }
    a, button { font-size: 30px; padding: 28px; }
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

    </div></body></html>
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

        if count >= MAX_TICKETS:
            button = "<p>❌ SOLD OUT</p>"
        else:
            button = f"<a href='/claim/{f[0]}'>🎟 Claim Ticket</a>"

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p class="badge">Official Selection – Cinebration International Film Festival 2026</p>
            <p>{count}/{MAX_TICKETS} tickets sold</p>
            {button}
        </div>
        """

    html += "</div></body></html>"
    return html

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

    </div></body></html>
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

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">

    <div class="card">
        <h2>🎟 Ticket Created</h2>
        <p>Please wait...</p>
    </div>

    </div>

    <script>
    setTimeout(function() {{
        window.location.href = "/watch/{ticket_id}";
    }}, 2000);
    </script>

    </body></html>
    """

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
        else:
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

    </div></body></html>
    """

# -------------------------
# WATCH
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

    if now < film[3]:
        remaining = film[3] - now
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">

        <h2 class="glow">⏳ Premiere Starts Soon</h2>

        <div class="card">
            <p>Welcome {ticket[1]}</p>
            <h1>{hours}h {minutes}m</h1>
        </div>

        </div></body></html>
        """

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">

    <h2 class="glow">🎬 LIVE PREMIERE</h2>

    <div class="card video-box">
        <iframe src="{film[2]}" allowfullscreen></iframe>
    </div>

    </div></body></html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    pass_input = request.args.get("pass") or request.form.get("pass")

    if pass_input != ADMIN_PASSWORD:
        return "<h2>🔐 Admin Locked</h2>"

    cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
    users = cursor.fetchall()

    html = "<h2>🎟 Admin Panel</h2><hr>"

    for u in users:
        html += f"""
        <div class="card">
            <p><b>ID:</b> {u[0]}</p>
            <p><b>Name:</b> {u[1]}</p>
            <p><b>Email:</b> {u[2]}</p>
            <p><b>Film:</b> {u[3]}</p>
        </div>
        """

    return html

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
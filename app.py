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

# -------------------------
# CINEMATIC BIG UI
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

body {
    margin: 0;
    font-family: Arial;
    background: radial-gradient(circle at top, #111, #000);
    color: white;
    text-align: center;
    font-size: 22px;
}

.container {
    padding: 30px 16px;
}

.card {
    background: rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 28px;
    margin: 22px auto;
    max-width: 95%;
    box-shadow: 0 0 25px rgba(0,0,0,0.8);
}

h1 { font-size: 40px; }
h2 { font-size: 32px; }
h3 { font-size: 26px; }
p  { font-size: 20px; }

a, button {
    display: block;
    margin-top: 18px;
    padding: 20px;
    background: #1db954;
    color: black;
    border-radius: 14px;
    font-weight: bold;
    font-size: 22px;
    text-decoration: none;
}

input {
    width: 95%;
    padding: 18px;
    margin: 14px 0;
    border-radius: 12px;
    border: none;
    font-size: 20px;
}

.video-box iframe {
    width: 100%;
    aspect-ratio: 16/9;
    border-radius: 16px;
}

.glow {
    text-shadow: 0 0 12px #1db954;
}

html {
    -webkit-text-size-adjust: 100%;
}

@media (max-width: 480px) {
    body { font-size: 24px; }
    h1 { font-size: 44px; }
    h2 { font-size: 36px; }
    a, button { font-size: 24px; padding: 22px; }
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
    <p>Digital Box Office System</p>

    <div class="card">
        <a href="/films">🎟 Get Ticket</a>
        <a href="/enter">🎬 Enter Premiere</a>
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

    <h2 class="glow">🎟 ACCESS GRANTED</h2>

    <div class="card">
        <p>Ticket ID: #{ticket_id}</p>
        <a href="/watch/{ticket_id}">▶ Enter Premiere</a>
    </div>

    </div></body></html>
    """

# -------------------------
# ENTER (LOGIN)
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
# WATCH (REAL TIMER)
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

        <h2 class="glow">⏳ PREMIERE LOCKED</h2>

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
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
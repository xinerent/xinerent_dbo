from flask import Flask, request
import sqlite3
import time
import os

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
# DEFAULT FILM
# -------------------------
cursor.execute("SELECT COUNT(*) FROM films")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
    INSERT INTO films (title, youtube_link, release_time)
    VALUES (?, ?, ?)
    """, (
        "XineRent Premiere Film",
        "https://www.youtube.com/embed/-AUw43bmMWQ",
        int(time.time()) + 60
    ))
    conn.commit()

# -------------------------
# CINEMATIC UI + MOBILE FIX + VIDEO FIX
# -------------------------
BASE_STYLE = """
<style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: radial-gradient(circle at top, #1a1a1a, #000);
    color: white;
    text-align: center;
    font-size: 18px;
}

.container {
    padding: 25px 15px;
}

.card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px;
    padding: 22px;
    margin: 18px auto;
    max-width: 95%;
    width: 100%;
    box-shadow: 0 0 30px rgba(0,0,0,0.7);
    backdrop-filter: blur(12px);
}

h1 { font-size: 30px; }
h2 { font-size: 26px; }
h3 { font-size: 22px; }

a {
    display: inline-block;
    margin-top: 12px;
    padding: 14px 18px;
    background: #1db954;
    color: black;
    text-decoration: none;
    border-radius: 12px;
    font-weight: bold;
    font-size: 18px;
}

button {
    width: 100%;
    padding: 16px;
    background: #1db954;
    border: none;
    border-radius: 12px;
    font-weight: bold;
    font-size: 18px;
}

input {
    width: 95%;
    padding: 14px;
    margin: 10px 0;
    border-radius: 10px;
    border: none;
    font-size: 16px;
}

.glow {
    text-shadow: 0 0 12px #1db954;
}

/* 🎬 FIXED VIDEO CONTAINER */
.video-box {
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
}

iframe {
    width: 100%;
    aspect-ratio: 16 / 9;
    border-radius: 16px;
    box-shadow: 0 0 25px rgba(0,0,0,0.8);
}

/* MOBILE FIX */
html, body {
    -webkit-text-size-adjust: 100%;
    touch-action: manipulation;
}
</style>

<!-- APP MODE -->
<link rel="manifest" href="/manifest.json">
"""

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body>

    <div class="container">

        <h1 class="glow">🎬 XineRent DBO</h1>
        <p>Digital Box Office System</p>

        <div class="card">
            <a href="/films">🎥 Enter Cinema</a>
        </div>

    </div>

    </body>
    </html>
    """

# -------------------------
# FILMS
# -------------------------
@app.route("/films")
def films():
    cursor.execute("SELECT * FROM films")
    data = cursor.fetchall()

    html = f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body>

    <div class="container">
        <h2 class="glow">🎥 Now Showing</h2>
    """

    for f in data:
        html += f"""
        <div class="card">
            <h3>{f[1]}</h3>
            <a href="/claim/{f[0]}">🎟 Claim Ticket</a>
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
    <html>
    <head>{BASE_STYLE}</head>
    <body>

    <div class="container">

        <h2 class="glow">🎟 Claim Premiere Ticket</h2>

        <div class="card">
            <form action="/submit/{film_id}" method="POST">
                <input name="name" placeholder="Your Name" required>
                <input name="email" placeholder="Email" required>
                <button type="submit">Get Access</button>
            </form>
        </div>

    </div>

    </body>
    </html>
    """

# -------------------------
# SUBMIT
# -------------------------
@app.route("/submit/<int:film_id>", methods=["POST"])
def submit(film_id):
    name = request.form.get("name")
    email = request.form.get("email")

    cursor.execute("""
    INSERT INTO tickets (name, email, film_id, created_at)
    VALUES (?, ?, ?, ?)
    """, (name, email, film_id, int(time.time())))
    conn.commit()

    ticket_id = cursor.lastrowid
    watch_url = f"/watch/{ticket_id}"

    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body>

    <div class="container">

        <h2 class="glow">🎟 ACCESS GRANTED</h2>

        <div class="card">
            <p><b>Ticket ID:</b> #{ticket_id}</p>
            <p>Your cinema entry is ready</p>
            <a href="{watch_url}">▶ Enter Premiere Room</a>
        </div>

    </div>

    </body>
    </html>
    """

# -------------------------
# WATCH (FIXED CINEMA PLAYER + COUNTDOWN)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    ticket = cursor.fetchone()

    if not ticket:
        return "<h2>❌ Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=?", (ticket[3],))
    film = cursor.fetchone()

    if not film:
        return "<h2>❌ Film not found</h2>"

    release_time = film[3]
    now = int(time.time())

    # ⏳ COUNTDOWN
    if now < release_time:
        remaining = release_time - now

        return f"""
        <html>
        <head>{BASE_STYLE}</head>
        <body>

        <div class="container">

            <h2 class="glow">⏳ PREMIERE LOCKED</h2>

            <div class="card">
                <p>Welcome {ticket[1]}</p>
                <p>Starts in: <b>{remaining} seconds</b></p>
            </div>

        </div>

        </body>
        </html>
        """

    # 🎬 LIVE PLAYER (FIXED)
    return f"""
    <html>
    <head>{BASE_STYLE}</head>
    <body>

    <div class="container">

        <h2 class="glow">🎬 LIVE PREMIERE</h2>

        <div class="card video-box">
            <iframe src="{film[2]}" frameborder="0" allowfullscreen></iframe>
        </div>

    </div>

    </body>
    </html>
    """

# -------------------------
# APP MODE
# -------------------------
@app.route("/manifest.json")
def manifest():
    return {
        "name": "XineRent Cinema",
        "short_name": "XineRent",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#000000",
        "theme_color": "#1db954"
    }

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
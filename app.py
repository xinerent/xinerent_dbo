from flask import Flask, request, redirect, jsonify
import psycopg2
import time
import os
import datetime

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
# PREMIERE TIME (IST FIXED)
# 7PM IST = 13:30 UTC
# -------------------------
release_time = int(datetime.datetime(2026, 5, 1, 13, 30).timestamp())

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
# STYLE + SCRIPT
# -------------------------
BASE_STYLE = """
<style>
body {
    margin:0;
    font-family: Arial;
    background: radial-gradient(circle at top,#050505,#000);
    color:white;
    text-align:center;
}

.container { padding: 80px 20px; }

.card {
    background:#0f0f0f;
    border-radius:25px;
    padding:60px;
    margin:30px auto;
    max-width:95%;
    border:1px solid rgba(212,175,55,0.25);
}

h1 { font-size:110px; }
h2 { font-size:75px; }
p  { font-size:40px; }

.glow {
    color:#d4af37;
    text-shadow:0 0 25px #d4af37;
}

iframe {
    width:100%;
    height:600px;
    border-radius:20px;
}

a,button{
    display:block;
    margin-top:25px;
    padding:40px;
    font-size:40px;
    background:linear-gradient(135deg,#d4af37,#f5e6c8);
    color:black;
    border-radius:20px;
    font-weight:bold;
    border:none;
}

.timer {
    font-size:50px;
    color:#d4af37;
}

.fs-btn{
    margin-top:20px;
    padding:20px;
    font-size:30px;
    background:black;
    color:#d4af37;
}
</style>

<script>
function startCountdown(endTime){
    function update(){
        let now = Math.floor(Date.now()/1000);
        let diff = endTime - now;

        let d = Math.floor(diff / 86400);
        let h = Math.floor((diff % 86400) / 3600);
        let m = Math.floor((diff % 3600) / 60);
        let s = diff % 60;

        if(diff <= 0){
            document.getElementById("timer").innerHTML = "🎬 LIVE NOW";
            location.reload();
        } else {
            document.getElementById("timer").innerHTML =
                d+"d "+h+"h "+m+"m "+s+"s";
        }
    }
    update();
    setInterval(update,1000);
}

function goFull(){
    let el=document.documentElement;
    if(el.requestFullscreen){
        el.requestFullscreen();
    }
}

function autoCinema(){
    let el = document.documentElement;

    if(el.requestFullscreen){
        el.requestFullscreen().catch(()=>{});
    }

    document.body.style.overflow = "hidden";

    if ('wakeLock' in navigator) {
        navigator.wakeLock.request('screen').catch(()=>{});
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
    films = cursor.fetchall()

    html = f"<html><head>{BASE_STYLE}</head><body><div class='container'>"

    for f in films:
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (f[0],))
        count = cursor.fetchone()[0]

        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <p>{count} / {MAX_TICKETS}</p>
            <a href='/claim/{f[0]}'>🎟 Claim Ticket</a>
        </div>
        """

    return html + "</div></body></html>"

# -------------------------
# CLAIM
# -------------------------
@app.route("/claim/<int:film_id>")
def claim(film_id):
    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <div class="card">
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

    cursor.execute("""
    INSERT INTO tickets(name,email,film_id,created_at)
    VALUES(%s,%s,%s,%s) RETURNING id
    """, (name,email,film_id,int(time.time())))

    ticket_id = cursor.fetchone()[0]
    conn.commit()

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# ENTER
# -------------------------
@app.route("/enter", methods=["GET","POST"])
def enter():
    if request.method=="POST":
        email=request.form["email"]

        cursor.execute("SELECT id FROM tickets WHERE email=%s",(email,))
        t=cursor.fetchone()

        if t:
            return redirect(f"/watch/{t[0]}")

        return "<h2>No ticket</h2>"

    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">
        <h2 class="glow">Enter Premiere</h2>
        <div class="card">
            <form method="POST">
                <input name="email" placeholder="Enter your email" required>
                <button>Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH (FINAL)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
    t=cursor.fetchone()

    cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
    film=cursor.fetchone()

    now = int(time.time())

    if now < film[3]:
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body onload="startCountdown({film[3]})">
        <div class="container">
            <div class="card">
                <p>Welcome {t[1]}</p>
                <p>Premiere starts in:</p>
                <div id="timer" class="timer"></div>
            </div>
        </div>
        </body></html>
        """

    return f"""
    <html><head>{BASE_STYLE}</head>
    <body onload="autoCinema()">
    <div class="container">
        <div class="card">

            <iframe src="{film[2]}?autoplay=1" allow="autoplay; fullscreen"></iframe>

            <button class="fs-btn" onclick="goFull()">⛶ Cinema Mode</button>

        </div>
    </div>
    </body></html>
    """

# -------------------------
# RUN
# -------------------------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
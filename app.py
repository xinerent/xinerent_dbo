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

conn.commit()

# -------------------------
# SETTINGS
# -------------------------
MAX_TICKETS = 700
ADMIN_PASSWORD = "Muha&123"

# -------------------------
# PREMIERE SETUP
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
    conn.commit()

# -------------------------
# TIME FORMAT
# -------------------------
def format_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d %b %Y %I:%M %p")

# -------------------------
# COUNTER API
# -------------------------
@app.route("/ticket-count/<int:film_id>")
def ticket_count(film_id):
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (film_id,))
    count = cursor.fetchone()[0]
    return jsonify({"count": count})

# -------------------------
# LIVE VIEWERS API
# -------------------------
@app.route("/live-viewers/<int:film_id>")
def live_viewers(film_id):
    cursor.execute("""
    SELECT COUNT(*) FROM viewers v
    JOIN tickets t ON t.id = v.ticket_id
    WHERE t.film_id = %s AND v.last_seen > %s
    """, (film_id, int(time.time()) - 60))
    count = cursor.fetchone()[0]
    return jsonify({"count": count})

# -------------------------
# STYLE
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
    text-decoration:none !important;
    border:none;
}

input{
    width:95%;
    padding:35px;
    font-size:38px;
    border-radius:15px;
    background:#111;
    color:white;
}

.live {
    color:#00ff88;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0% {opacity:1;}
    50% {opacity:0.4;}
    100% {opacity:1;}
}

.admin-box {
    background:black;
    color:white;
    padding:30px;
    border-radius:20px;
    text-align:left;
}
</style>

<script>
function animateCounter(id, value){
    let el=document.getElementById(id);
    if(!el)return;

    let current=parseInt(el.innerText)||0;
    let step=(value-current)/20;

    let i=0;
    let interval=setInterval(()=>{
        i++;
        current+=step;
        el.innerText=Math.floor(current);
        if(i>=20){
            el.innerText=value;
            clearInterval(interval);
        }
    },40);
}

function refresh(filmId){
    fetch("/ticket-count/"+filmId)
    .then(r=>r.json())
    .then(d=>{
        let el=document.getElementById("count-"+filmId);
        if(el && parseInt(el.innerText)!==d.count){
            animateCounter("count-"+filmId,d.count);
        }
    });
}

function refreshLive(filmId){
    fetch("/live-viewers/"+filmId)
    .then(r=>r.json())
    .then(d=>{
        let el=document.getElementById("live-count");
        if(el && parseInt(el.innerText)!==d.count){
            animateCounter("live-count",d.count);
        }
    });
}

setInterval(()=>{
    if(window.FILM_IDS){
        window.FILM_IDS.forEach(id=>refresh(id));
    }
    if(window.FILM_ID){
        refreshLive(window.FILM_ID);
    }
},3000);
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
# ENTER (FIXED INPUT)
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
# WATCH (FULL UPGRADE)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
    t=cursor.fetchone()

    if not t:
        return "<h2>Invalid Ticket</h2>"

    cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
    film=cursor.fetchone()

    video = film[2] if film and film[2] else ""

    now=int(time.time())
    premiere_time = int(datetime.datetime(2026, 5, 1, 19, 0).timestamp())

    cursor.execute("""
    INSERT INTO viewers(ticket_id,last_seen)
    VALUES(%s,%s)
    ON CONFLICT(ticket_id)
    DO UPDATE SET last_seen=EXCLUDED.last_seen
    """,(ticket_id,now))
    conn.commit()

    # BEFORE PREMIERE
    if now < premiere_time:
        return f"""
        <html><head>{BASE_STYLE}</head>
        <body>
        <div class="container">
            <h2 class="glow">🎬 PREMIERE STARTS IN</h2>
            <div class="card">
                <h1 id="countdown"></h1>
            </div>
        </div>

        <script>
        function updateCountdown() {{
            let target={premiere_time};
            let now=Math.floor(Date.now()/1000);
            let diff=target-now;

            let d=Math.floor(diff/86400);
            let h=Math.floor((diff%86400)/3600);
            let m=Math.floor((diff%3600)/60);
            let s=diff%60;

            document.getElementById("countdown").innerText =
            d+"d "+h+"h "+m+"m "+s+"s";
        }}

        setInterval(updateCountdown,1000);
        updateCountdown();
        </script>
        </body></html>
        """

    # AFTER PREMIERE
    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
    <div class="container">

        <h2 class="glow">🎬 LIVE PREMIERE</h2>

        <div class="live">🔴 LIVE VIEWERS: <span id="live-count">0</span></div>

        <div class="card">
            <iframe id="videoFrame" src="{video}" allowfullscreen></iframe>
        </div>

    </div>

    <script>
    window.FILM_ID = {t[3]};

    function goFullScreen(){{
        let iframe = document.getElementById("videoFrame");
        if(iframe.requestFullscreen){{
            iframe.requestFullscreen();
        }}
    }}

    setTimeout(goFullScreen,2000);
    </script>

    </body></html>
    """
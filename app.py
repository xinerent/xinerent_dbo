from flask import Flask, request, redirect, jsonify
import psycopg2
import time
import os
import datetime

app = Flask(__name__)

# -------------------------
# DB CONNECTION
# -------------------------
def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# -------------------------
# INIT DB
# -------------------------
def init_db():
    with get_conn() as conn:
        with conn.cursor() as cursor:

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

init_db()

# -------------------------
# SETTINGS
# -------------------------
MAX_TICKETS = 700
ADMIN_PASSWORD = "Muha&123"
PREMIERE_TIME = int(datetime.datetime(2026, 5, 1, 19, 0).timestamp())

# -------------------------
# INSERT FILM ONCE
# -------------------------
with get_conn() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM films")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO films (title, youtube_link, release_time)
            VALUES (%s,%s,%s)
            """, (
                "XineRent Premiere Film",
                "https://www.youtube.com/embed/-AUw43bmMWQ",
                PREMIERE_TIME
            ))

# -------------------------
# STYLE (CINEMATIC BIG UI)
# -------------------------
BASE_STYLE = """
<style>
body{
    margin:0;
    background:#000;
    color:white;
    font-family:Arial;
    text-align:center;
}

/* VERY BIG TEXT */
h1{font-size:140px;}
h2{font-size:95px;}
p{font-size:50px;}

.container{padding:90px 20px;}

.card{
    background:#0f0f0f;
    padding:80px;
    border-radius:30px;
    margin:30px auto;
    max-width:95%;
    border:1px solid rgba(212,175,55,0.3);
}

/* GOLD FESTIVAL TITLE */
.glow{
    color:#d4af37;
    text-shadow:0 0 30px #d4af37;
}

/* BUTTONS */
a,button{
    padding:50px;
    font-size:45px;
    background:#d4af37;
    color:black;
    border-radius:20px;
    display:block;
    margin-top:30px;
    text-decoration:none;
    font-weight:bold;
}

/* INPUT */
input{
    width:95%;
    padding:45px;
    font-size:40px;
    background:#111;
    color:white;
    border-radius:15px;
}

/* LIVE VIEWERS */
.live{
    color:#00ff88;
    font-weight:bold;
}

/* VIDEO */
iframe{
    width:100%;
    height:700px;
    border-radius:25px;
}

/* CINEMATIC FULLSCREEN FALLBACK */
.cinema-overlay{
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:black;
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:9999;
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
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM films")
            films = cursor.fetchall()

    html = f"<html><head>{BASE_STYLE}</head><body><div class='container'>"

    for f in films:

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM tickets WHERE film_id=%s", (f[0],))
                count = cursor.fetchone()[0]

        remaining = MAX_TICKETS - count

        # FIX: show 0 when empty (no negative or weird values)
        if count < 0:
            count = 0
        if remaining < 0:
            remaining = 0

        html += f"""
        <div class="card">

            <p class="glow">
            🏆 Official Selection at Cinebration International Film Festival 2026
            </p>

            <h2>{f[1]}</h2>

            <p>{count}/{MAX_TICKETS}</p>
            <p class="live">Remaining: {remaining}</p>

            <a href="/claim/{f[0]}">🎟 Get Ticket</a>
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
    name = request.form.get("name")
    email = request.form.get("email")

    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            INSERT INTO tickets(name,email,film_id,created_at)
            VALUES(%s,%s,%s,%s)
            RETURNING id
            """,(name,email,film_id,int(time.time())))
            ticket_id = cursor.fetchone()[0]

    return redirect(f"/watch/{ticket_id}")

# -------------------------
# ENTER
# -------------------------
@app.route("/enter", methods=["GET","POST"])
def enter():
    if request.method=="POST":
        email=request.form.get("email")

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM tickets WHERE email=%s",(email,))
                t=cursor.fetchone()

        if t:
            return redirect(f"/watch/{t[0]}")
        return "<h2>No ticket found</h2>"

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">Enter Premiere</h2>
        <div class="card">
            <form method="POST">
                <input name="email" placeholder="Enter email to enter premiere" required>
                <button>Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH (SAFE + CINEMATIC + FULLSCREEN)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    with get_conn() as conn:
        with conn.cursor() as cursor:

            cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
            t=cursor.fetchone()
            if not t:
                return "<h2>Invalid Ticket</h2>"

            cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
            film=cursor.fetchone()
            video = film[2] if film else ""

    now=int(time.time())

    if now < PREMIERE_TIME:
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <h2 class="glow">🎬 PREMIERE STARTS IN</h2>
            <h1 id="cd"></h1>
        </div>

        <script>
        setInterval(()=>{
            let t={PREMIERE_TIME};
            let n=Math.floor(Date.now()/1000);
            let d=t-n;

            let dd=Math.floor(d/86400);
            let h=Math.floor((d%86400)/3600);
            let m=Math.floor((d%3600)/60);
            let s=d%60;

            document.getElementById("cd").innerText=
            dd+"d "+h+"h "+m+"m "+s+"s";

            if(d<=0) location.reload();
        },1000);
        </script>
        </body></html>
        """

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎬 LIVE PREMIERE</h2>

        <div class="card">
            <iframe id="vid" src="{video}" allowfullscreen></iframe>
        </div>

        <p class="live">🔴 LIVE STREAM ACTIVE</p>
    </div>

    <script>
    window.onload=function(){{
        let v=document.getElementById("vid");

        setTimeout(()=>{
            if(v.requestFullscreen) v.requestFullscreen();
        },1500);
    }}
    </script>
    </body></html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET","POST"])
def admin():

    if request.method=="POST":
        if request.form.get("pass")==ADMIN_PASSWORD:

            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name,email FROM tickets")
                    users=cursor.fetchall()

            html="<h1 class='glow'>ADMIN PANEL</h1><div class='card'>"
            for u in users:
                html+=f"<p>{u[0]} | {u[1]}</p>"
            html+="</div>"

            return f"<html><head>{BASE_STYLE}</head><body>{html}</body></html>"

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">ADMIN LOGIN</h2>
        <div class="card">
            <form method="POST">
                <input name="pass" type="password">
                <button>Login</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# RUN
# -------------------------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
from flask import Flask, request, redirect, jsonify
import psycopg2
import time
import os
import datetime

app = Flask(__name__)

# -------------------------
# DB CONNECTION SAFE
# -------------------------
def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# -------------------------
# INIT DATABASE
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
# STYLE
# -------------------------
BASE_STYLE = """
<style>
body{margin:0;background:#000;color:white;text-align:center;font-family:Arial;}
.container{padding:70px 20px;}
.card{background:#0f0f0f;padding:50px;border-radius:25px;margin:25px auto;max-width:95%;}
h1{font-size:90px;} h2{font-size:65px;} p{font-size:32px;}
.glow{color:#d4af37;text-shadow:0 0 20px #d4af37;}
iframe{width:100%;height:600px;border-radius:18px;}
a,button{
    padding:30px;
    font-size:32px;
    background:#d4af37;
    color:black;
    border-radius:18px;
    text-decoration:none;
    border:none;
    display:block;
    margin-top:20px;
}
input{
    padding:30px;
    font-size:30px;
    width:95%;
    background:#111;
    color:white;
    border-radius:15px;
}
.live{color:#00ff88;}
.admin-box{background:black;padding:25px;border-radius:15px;text-align:left;}
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
        html += f"""
        <div class="card">
            <h2>{f[1]}</h2>
            <a href="/claim/{f[0]}">🎟 Claim Ticket</a>
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

    if not name or not email:
        return "Missing data"

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
    if request.method == "POST":
        email = request.form.get("email")

        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM tickets WHERE email=%s",(email,))
                t = cursor.fetchone()

        if t:
            return redirect(f"/watch/{t[0]}")
        return "<h2>No ticket found</h2>"

    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">Enter Premiere</h2>
        <div class="card">
            <form method="POST">
                <input name="email" placeholder="Enter email to access premiere" required>
                <button>Enter</button>
            </form>
        </div>
    </div>
    </body></html>
    """

# -------------------------
# WATCH (FIXED + SAFE)
# -------------------------
@app.route("/watch/<int:ticket_id>")
def watch(ticket_id):

    with get_conn() as conn:
        with conn.cursor() as cursor:

            cursor.execute("SELECT * FROM tickets WHERE id=%s",(ticket_id,))
            t = cursor.fetchone()
            if not t:
                return "Invalid Ticket"

            cursor.execute("SELECT * FROM films WHERE id=%s",(t[3],))
            film = cursor.fetchone()

            video = film[2] if film else ""

            now = int(time.time())

            cursor.execute("""
            INSERT INTO viewers(ticket_id,last_seen)
            VALUES(%s,%s)
            ON CONFLICT(ticket_id)
            DO UPDATE SET last_seen=%s
            """,(ticket_id,now,now))

            cursor.execute("""
            SELECT COUNT(*) FROM viewers WHERE last_seen > %s
            """,(now-60,))
            live = cursor.fetchone()[0]

    # BEFORE PREMIERE
    if now < PREMIERE_TIME:
        return f"""
        <html><head>{BASE_STYLE}</head><body>
        <div class="container">
            <h2 class="glow">🎬 STARTS IN</h2>
            <h1 id="countdown"></h1>
        </div>

        <script>
        function tick(){{
            let t={PREMIERE_TIME};
            let now=Math.floor(Date.now()/1000);
            let d=t-now;

            if(d<=0){{
                location.reload();
                return;
            }}

            let dd=Math.floor(d/86400);
            let h=Math.floor((d%86400)/3600);
            let m=Math.floor((d%3600)/60);
            let s=d%60;

            document.getElementById("countdown").innerText=
            dd+"d "+h+"h "+m+"m "+s+"s";
        }}
        setInterval(tick,1000);
        tick();
        </script>
        </body></html>
        """

    # AFTER PREMIERE
    return f"""
    <html><head>{BASE_STYLE}</head><body>
    <div class="container">
        <h2 class="glow">🎬 LIVE PREMIERE</h2>
        <p class="live">🔴 LIVE VIEWERS: {live}</p>

        <div class="card">
            <iframe id="vid" src="{video}" allowfullscreen></iframe>
        </div>
    </div>

    <script>
    window.onload=function(){{
        let v=document.getElementById("vid");
        if(v.requestFullscreen) v.requestFullscreen();
    }}
    </script>

    </body></html>
    """

# -------------------------
# ADMIN
# -------------------------
@app.route("/admin", methods=["GET","POST"])
def admin():

    if request.method == "POST":
        if request.form.get("pass") == ADMIN_PASSWORD:

            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name,email FROM tickets")
                    users = cursor.fetchall()

            html = "<h1 class='glow'>ADMIN</h1><div class='admin-box'>"
            for u in users:
                html += f"<p>{u[0]} - {u[1]}</p>"
            html += "</div>"

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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
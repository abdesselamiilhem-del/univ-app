import os, time
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
from flask import Flask, request, redirect, url_for, Response, render_template
from jinja2 import DictLoader

app = Flask(__name__)
DB_URL = os.environ["DATABASE_URL"]
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

BASE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>University of Atlas</title>
<style>
body{font-family:system-ui,sans-serif;max-width:800px;margin:auto;padding:1rem;line-height:1.6;background:#f4f6fb;color:#1b2a41}
h1{background:#1f3a68;color:#fff;padding:1rem;border-radius:10px;margin-bottom:.5rem}
nav{background:#fff;padding:.7rem;border-radius:10px}
nav a{margin-right:1rem;color:#1f3a68;font-weight:600;text-decoration:none}
.card{background:#fff;border-radius:10px;padding:1rem;margin:.8rem 0;box-shadow:0 1px 4px #0002}
input,textarea{width:100%;padding:.6rem;margin:.3rem 0 .8rem;border:1px solid #ccd;border-radius:6px;box-sizing:border-box}
button{padding:.5rem 1rem;background:#1f3a68;color:#fff;border:0;border-radius:6px}
small{color:#667}
</style></head><body>
<h1>University of Atlas</h1>
<nav><a href="/">Home</a><a href="/departments">Departments</a><a href="/news">News</a><a href="/admin">Admin</a></nav>
{% block c %}{% endblock %}</body></html>"""

HOME = """{% extends 'base' %}{% block c %}
<div class="card"><p>Welcome to the (fictional) University of Atlas, founded in 1965.</p></div>
<h2>Recent announcements</h2>
{% for a in items %}<div class="card"><b>{{a.title}}</b><br><small>{{a.created_at.strftime('%Y-%m-%d')}}</small><p>{{a.content}}</p></div>
{% else %}<p>No announcements yet.</p>{% endfor %}{% endblock %}"""

DEPTS = """{% extends 'base' %}{% block c %}<h2>Departments</h2>
{% for d in items %}<div class="card"><b>{{d.name}}</b><p>{{d.description}}</p></div>{% endfor %}{% endblock %}"""

NEWS = """{% extends 'base' %}{% block c %}<h2>News and announcements</h2>
{% for a in items %}<div class="card"><b>{{a.title}}</b><br><small>{{a.created_at.strftime('%Y-%m-%d %H:%M')}}</small><p>{{a.content}}</p></div>{% endfor %}{% endblock %}"""

ADMIN = """{% extends 'base' %}{% block c %}<h2>Administration</h2>
<p><a href="/admin/new">+ Add announcement</a></p>
{% for a in items %}<div class="card"><b>{{a.title}}</b><p>{{a.content}}</p>
<a href="/admin/{{a.id}}/edit">Edit</a>
<form method="post" action="/admin/{{a.id}}/delete" style="display:inline" onsubmit="return confirm('Delete?')"><button>Delete</button></form></div>{% endfor %}{% endblock %}"""

FORM = """{% extends 'base' %}{% block c %}<h2>{{'Edit' if a else 'New'}} announcement</h2>
<form method="post"><label>Title</label><input name="title" required value="{{a.title if a else ''}}">
<label>Content</label><textarea name="content" rows="6" required>{{a.content if a else ''}}</textarea>
<button>Save</button></form>{% endblock %}"""

app.jinja_loader = DictLoader({"base": BASE, "home": HOME, "depts": DEPTS,
                               "news": NEWS, "admin": ADMIN, "form": FORM})

def run(sql, args=(), fetch=False):
    conn = psycopg2.connect(DB_URL, options="-c search_path=univapp,public")
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, args)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()

def init_db():
    for _ in range(30):
        try:
            run("CREATE SCHEMA IF NOT EXISTS univapp")
            run("""CREATE TABLE IF NOT EXISTS departments(
                     id SERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
                   CREATE TABLE IF NOT EXISTS announcements(
                     id SERIAL PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT now());""")
            if not run("SELECT 1 FROM departments LIMIT 1", fetch=True):
                run("""INSERT INTO departments(name,description) VALUES
                  ('Computer Science','Algorithms, software engineering, AI and networks.'),
                  ('Physics','Classical and modern physics, lab research.'),
                  ('Literature','Languages, writing and cultural studies.');
                  INSERT INTO announcements(title,content) VALUES
                  ('Welcome back','The new academic year starts on Monday.'),
                  ('Library hours','The library is open until 10 PM during exams.');""")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("Database not reachable")

def auth(f):
    @wraps(f)
    def w(*a, **k):
        c = request.authorization
        if not c or c.username != ADMIN_USER or c.password != ADMIN_PASSWORD:
            return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="Admin"'})
        return f(*a, **k)
    return w

@app.route("/")
def home():
    return render_template("home", items=run("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 3", fetch=True))

@app.route("/departments")
def departments():
    return render_template("depts", items=run("SELECT * FROM departments ORDER BY name", fetch=True))

@app.route("/news")
def news():
    return render_template("news", items=run("SELECT * FROM announcements ORDER BY created_at DESC", fetch=True))

@app.route("/admin")
@auth
def admin():
    return render_template("admin", items=run("SELECT * FROM announcements ORDER BY created_at DESC", fetch=True))

@app.route("/admin/new", methods=["GET", "POST"])
@auth
def new():
    if request.method == "POST":
        run("INSERT INTO announcements(title,content) VALUES(%s,%s)", (request.form["title"], request.form["content"]))
        return redirect(url_for("admin"))
    return render_template("form", a=None)

@app.route("/admin/<int:i>/edit", methods=["GET", "POST"])
@auth
def edit(i):
    if request.method == "POST":
        run("UPDATE announcements SET title=%s, content=%s WHERE id=%s", (request.form["title"], request.form["content"], i))
        return redirect(url_for("admin"))
    rows = run("SELECT * FROM announcements WHERE id=%s", (i,), fetch=True)
    return render_template("form", a=rows[0] if rows else None)

@app.route("/admin/<int:i>/delete", methods=["POST"])
@auth
def delete(i):
    run("DELETE FROM announcements WHERE id=%s", (i,))
    return redirect(url_for("admin"))

init_db()



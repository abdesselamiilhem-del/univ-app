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
SCHEMA = "umbb"

BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>University of Boumerdès</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:820px;margin:0 auto;padding:0 1rem 2rem;line-height:1.6;background:#f5f7fa;color:#1c2b39}
header{background:#14365d;color:#fff;padding:1.2rem 1rem;margin:0 -1rem 1rem}
header h1{margin:0;font-size:1.5rem}
header p{margin:.2rem 0 0;opacity:.8;font-size:.9rem}
nav{margin:0 -1rem 1rem;padding:.7rem 1rem;background:#fff;border-bottom:1px solid #dde3ea}
nav a{margin-right:1.2rem;color:#14365d;font-weight:600;text-decoration:none}
h2{color:#14365d;margin-top:1.5rem}
.card{background:#fff;border:1px solid #dde3ea;border-radius:8px;padding:1rem;margin:.8rem 0}
.card b{color:#14365d}
input,textarea{width:100%;padding:.6rem;margin:.3rem 0 .9rem;border:1px solid #c5ced8;border-radius:6px;box-sizing:border-box;font:inherit}
button{padding:.5rem 1.1rem;background:#14365d;color:#fff;border:0;border-radius:6px;font:inherit}
small{color:#6b7a89}
footer{margin-top:2rem;padding-top:1rem;border-top:1px solid #dde3ea;font-size:.8rem;color:#6b7a89}
</style></head><body>
<header><h1>University of Boumerdès</h1><p>Information and announcements portal</p></header>
<nav><a href="/">Home</a><a href="/departments">Departments</a><a href="/news">News</a><a href="/admin">Administration</a></nav>
{% block c %}{% endblock %}
<footer>Academic project, Cloud Computing. All data shown on this site is sample data.</footer>
</body></html>"""

HOME = """{% extends 'base' %}{% block c %}
<div class="card"><p>Welcome to the information portal of the University of Boumerdès (Université M'Hamed Bougara de Boumerdès). Students, teachers and visitors can browse the departments and follow the latest announcements.</p></div>
<h2>Recent announcements</h2>
{% for a in items %}<div class="card"><b>{{a.title}}</b><br><small>{{a.created_at.strftime('%d/%m/%Y')}}</small><p>{{a.content}}</p></div>
{% else %}<p>No announcements yet.</p>{% endfor %}{% endblock %}"""

DEPTS = """{% extends 'base' %}{% block c %}<h2>Departments</h2>
{% for d in items %}<div class="card"><b>{{d.name}}</b><p>{{d.description}}</p></div>{% endfor %}{% endblock %}"""

NEWS = """{% extends 'base' %}{% block c %}<h2>News and announcements</h2>
{% for a in items %}<div class="card"><b>{{a.title}}</b><br><small>{{a.created_at.strftime('%d/%m/%Y %H:%M')}}</small><p>{{a.content}}</p></div>
{% else %}<p>No announcements yet.</p>{% endfor %}{% endblock %}"""

ADMIN = """{% extends 'base' %}{% block c %}<h2>Administration</h2>
<p><a href="/admin/new">+ Add announcement</a></p>
{% for a in items %}<div class="card"><b>{{a.title}}</b><p>{{a.content}}</p>
<a href="/admin/{{a.id}}/edit">Edit</a>
<form method="post" action="/admin/{{a.id}}/delete" style="display:inline" onsubmit="return confirm('Delete this announcement?')"><button>Delete</button></form></div>{% endfor %}{% endblock %}"""

FORM = """{% extends 'base' %}{% block c %}<h2>{{'Edit' if a else 'New'}} announcement</h2>
<form method="post"><label>Title</label><input name="title" required value="{{a.title if a else ''}}">
<label>Content</label><textarea name="content" rows="6" required>{{a.content if a else ''}}</textarea>
<button>Save</button></form>{% endblock %}"""

app.jinja_loader = DictLoader({"base": BASE, "home": HOME, "depts": DEPTS,
                               "news": NEWS, "admin": ADMIN, "form": FORM})

def run(sql, args=(), fetch=False):
    conn = psycopg2.connect(DB_URL, options="-c search_path=%s,public" % SCHEMA)
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, args)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()

def init_db():
    for _ in range(30):
        try:
            run("CREATE SCHEMA IF NOT EXISTS %s" % SCHEMA)
            run("""CREATE TABLE IF NOT EXISTS departments(
                     id SERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
                   CREATE TABLE IF NOT EXISTS announcements(
                     id SERIAL PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT now());""")
            if not run("SELECT 1 FROM departments LIMIT 1", fetch=True):
                run("""INSERT INTO departments(name,description) VALUES
                  ('Computer Science','Software engineering, networks, databases and artificial intelligence.'),
                  ('Mathematics','Algebra, analysis, probability and applied mathematics.'),
                  ('Physics','Fundamental and applied physics, materials and energy.'),
                  ('Electrical Engineering','Electronics, automation, power systems and telecommunications.'),
                  ('Mechanical Engineering','Design, thermodynamics, manufacturing and industrial maintenance.'),
                  ('Hydrocarbons and Chemistry','Process engineering, petroleum technologies and chemical analysis.'),
                  ('Economics and Management','Finance, accounting, marketing and business administration.'),
                  ('Languages and Literature','Arabic, French and English language and literature studies.');
                  INSERT INTO announcements(title,content) VALUES
                  ('Registration for the new academic year','Online registration is open for continuing students. Please check the schedule published by your department.'),
                  ('Library opening hours during exams','The central library extends its opening hours throughout the examination period.'),
                  ('Cloud Computing project presentations','Student groups will present their projects during the last practical session.');""")
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




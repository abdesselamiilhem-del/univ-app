import os, time, hmac, hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, session, send_file, redirect, abort

app = Flask(__name__)
DB_URL = os.environ["DATABASE_URL"]
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
app.secret_key = os.environ.get("SECRET_KEY") or hashlib.sha256(
    ("portal|" + ADMIN_PASSWORD + DB_URL).encode()).hexdigest()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

SCHEMA = "portal"
CATEGORIES = ["Registrations", "Event", "Examinations", "Conference", "Information"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_FILES = {"index.html", "departments.html", "announce.html", "login.html",
              "admin.html", "style.css", "app.js"}
IMAGES = ["campus.jpg", "Image PNG.png"]


def run(sql, args=(), fetch=False):
    conn = psycopg2.connect(DB_URL, options="-c search_path=%s,public" % SCHEMA)
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, args or None)
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
                     id SERIAL PRIMARY KEY, title TEXT NOT NULL,
                     category TEXT NOT NULL DEFAULT 'Information', content TEXT NOT NULL,
                     created_at TIMESTAMP NOT NULL DEFAULT now());""")
            if not run("SELECT 1 FROM departments LIMIT 1", fetch=True):
                run("""INSERT INTO departments(name,description) VALUES
                  ('Computer Science','Computer systems, Software Engineering, Artificial Intelligence.'),
                  ('Mathematics','Applied mathematics, statistics and mathematical modeling.'),
                  ('Physics','Mechanics, optics, energy, and applied physics.'),
                  ('Chemistry','The study of matter, its properties, and the changes it undergoes.'),
                  ('Medicine','The science and practice of diagnosing, treating, and preventing disease.'),
                  ('Biology','The study of living organisms and their interactions with the environment.'),
                  ('Agronomy','Techniques and methods to improve agricultural production, protect plants and soil, and develop sustainable agriculture.');
                  INSERT INTO announcements(title,category,content,created_at) VALUES
                  ('Registration for the 2026-2027 Academic Year Is Now Open','Registrations','Applications are open until January 15.', now() - interval '25 days'),
                  ('Campus Open Day','Event','Guided tours and meetings with faculty members.', now() - interval '20 days'),
                  ('Semester 1 Examination Schedule','Examinations','The schedule is available for all academic programs.', now() - interval '15 days'),
                  ('Artificial Intelligence Conference','Conference','Amphitheater 100, open to students and visitors.', now() - interval '10 days'),
                  ('Library Closure for Inventory','Information','Reopening scheduled for January 4.', now() - interval '5 days');""")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("Database not reachable")


def ann(r):
    return {"id": r["id"], "title": r["title"], "category": r["category"],
            "content": r["content"],
            "created_at": r["created_at"].strftime("%Y-%m-%dT%H:%M:%S")}


def same(a, b):
    return hmac.compare_digest(str(a).encode(), str(b).encode())


def guard():
    if not session.get("admin"):
        return jsonify(error="Authentication required."), 401


def read_form():
    d = request.get_json(silent=True) or {}
    title = str(d.get("title", "")).strip()
    content = str(d.get("content", "")).strip()
    category = d.get("category")
    if not title or len(title) > 150:
        return None, "The title is required (150 characters maximum)."
    if not content:
        return None, "The content is required."
    if category not in CATEGORIES:
        return None, "Invalid category."
    return (title, category, content), None


@app.post("/api/login")
def api_login():
    d = request.get_json(silent=True) or {}
    if same(d.get("username", ""), ADMIN_USER) and same(d.get("password", ""), ADMIN_PASSWORD):
        session["admin"] = True
        return jsonify(ok=True)
    return jsonify(error="Invalid username or password."), 401


@app.post("/api/logout")
def api_logout():
    session.clear()
    return "", 204


@app.get("/api/departments")
def api_departments():
    return jsonify(run("SELECT * FROM departments ORDER BY id", fetch=True))


@app.get("/api/announcements")
def api_announcements():
    rows = run("SELECT * FROM announcements ORDER BY created_at DESC, id DESC", fetch=True)
    return jsonify([ann(r) for r in rows])


@app.post("/api/announcements")
def api_add():
    denied = guard()
    if denied:
        return denied
    data, error = read_form()
    if error:
        return jsonify(error=error), 400
    row = run("INSERT INTO announcements(title,category,content) VALUES(%s,%s,%s) RETURNING *",
              data, fetch=True)[0]
    return jsonify(ann(row)), 201


@app.put("/api/announcements/<int:i>")
def api_edit(i):
    denied = guard()
    if denied:
        return denied
    data, error = read_form()
    if error:
        return jsonify(error=error), 400
    rows = run("UPDATE announcements SET title=%s, category=%s, content=%s WHERE id=%s RETURNING *",
               data + (i,), fetch=True)
    if not rows:
        return jsonify(error="Announcement not found."), 400
    return jsonify(ann(rows[0]))


@app.delete("/api/announcements/<int:i>")
def api_delete(i):
    denied = guard()
    if denied:
        return denied
    run("DELETE FROM announcements WHERE id=%s", (i,))
    return "", 204


def find_file(name):
    for f in os.listdir(BASE_DIR):
        if f.lower() == name.lower():
            return os.path.join(BASE_DIR, f)


@app.route("/")
def home():
    return site("index.html")


@app.route("/<name>")
def site(name):
    low = name.lower()
    if low == "campus.jpg":
        for f in IMAGES:
            if find_file(f):
                return send_file(find_file(f), max_age=0)
        abort(404)
    if low not in SITE_FILES:
        abort(404)
    if low == "admin.html" and not session.get("admin"):
        return redirect("/Login.html")
    path = find_file(low)
    if not path:
        abort(404)
    return send_file(path, max_age=0)


init_db()


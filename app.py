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
<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:1rem;line-height:1.5}
nav a{margin-right:1rem}.card{border:1px solid #ccc;border-radius:8px;padding:.8rem;margin:.8rem 0}
input,textarea{width:100%;padding:.5rem;margin:.3rem 0 .8rem}button{padding:.5rem 1rem}
small{color:#666}</style></head><body>
<h1>University of Atlas</h1>
<nav><a href="/">Home</a><a href="/departments">Departments</a><a href="/news">News</a><a href="/admin">Admin</a></nav><hr>
{% block c %}{% endblock %}</body>

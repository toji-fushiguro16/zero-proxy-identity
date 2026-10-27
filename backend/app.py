import os
import re
import sqlite3

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from auth import (authenticated, create_token, db_execute, db_query,
                  init_db, record)
from proxy import proxy_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
# Only needed if you still open the page through Live Server (port 5500)
CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})
app.register_blueprint(proxy_bp)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
VALID_ROLES = {"user", "manager", "admin"}


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------- Auth ----------
@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not USERNAME_RE.match(username):
        return jsonify(error="Username must be 3-30 letters, numbers or underscores"), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400

    try:
        # Everyone who registers starts as a normal user; only an admin can promote.
        db_execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')",
            (username, generate_password_hash(password)),
        )
    except sqlite3.IntegrityError:
        return jsonify(error="Username already taken"), 409

    return jsonify(token=create_token(username, "user"),
                   user={"username": username, "role": "user"}), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    user = db_query("SELECT * FROM users WHERE username = ?", (username,), one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Invalid username or password"), 401

    return jsonify(token=create_token(user["username"], user["role"]),
                   user={"username": user["username"], "role": user["role"]})


@app.get("/api/me")
@authenticated
def me():
    return jsonify(user=g.user)


# ---------- Dashboard data ----------
@app.get("/api/stats")
@authenticated
def stats():
    def count(decision):
        row = db_query("SELECT COUNT(*) AS n FROM audit_logs WHERE decision = ?", (decision,), one=True)
        return row["n"]
    return jsonify(allowed=count("ALLOWED"), denied=count("DENIED"))


@app.get("/api/logs")
@authenticated
def logs():
    if g.user["role"] != "admin":
        record(g.user["username"], "audit-logs", "DENIED",
               f"Role '{g.user['role']}' lacks 'admin'")
        return jsonify(error="Forbidden: admin role required"), 403
    rows = db_query("SELECT identity, service, decision, reason, time "
                    "FROM audit_logs ORDER BY id DESC LIMIT 100")
    return jsonify(logs=[dict(r) for r in rows])


# ---------- Role management (admin only) ----------
@app.get("/api/users")
@authenticated
def list_users():
    if g.user["role"] != "admin":
        return jsonify(error="Forbidden: admin role required"), 403
    rows = db_query("SELECT username, role FROM users ORDER BY username")
    return jsonify(users=[dict(r) for r in rows])


@app.patch("/api/users/<username>/role")
@authenticated
def set_role(username):
    if g.user["role"] != "admin":
        record(g.user["username"], "user-management", "DENIED", "Admin role required")
        return jsonify(error="Forbidden: admin role required"), 403

    role = str((request.get_json(silent=True) or {}).get("role", "")).lower()
    if role not in VALID_ROLES:
        return jsonify(error=f"Role must be one of {sorted(VALID_ROLES)}"), 400
    if not db_query("SELECT 1 FROM users WHERE username = ?", (username,), one=True):
        return jsonify(error="User not found"), 404

    db_execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
    record(g.user["username"], "user-management", "ALLOWED", f"Set {username} to {role}")
    return jsonify(username=username, role=role)


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
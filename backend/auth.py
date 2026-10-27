import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import g, jsonify, request
from werkzeug.security import generate_password_hash

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
TOKEN_HOURS = 1


# ---------- Database helpers ----------
def db_query(sql, args=(), one=False):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, args).fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def db_execute(sql, args=()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(sql, args)
        conn.commit()


def init_db():
    db_execute(
        """CREATE TABLE IF NOT EXISTS users (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT UNIQUE NOT NULL COLLATE NOCASE,
               password_hash TEXT NOT NULL,
               role TEXT NOT NULL DEFAULT 'user'
           )"""
    )
    db_execute(
        """CREATE TABLE IF NOT EXISTS audit_logs (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               identity TEXT NOT NULL,
               service TEXT NOT NULL,
               decision TEXT NOT NULL,
               reason TEXT NOT NULL,
               time TEXT NOT NULL
           )"""
    )
    if not db_query("SELECT 1 FROM users WHERE username = 'admin'", one=True):
        if not ADMIN_PASSWORD:
            raise RuntimeError("Set ADMIN_PASSWORD in backend/.env before first run")
        db_execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            ("admin", generate_password_hash(ADMIN_PASSWORD)),
        )


def record(identity, service, decision, reason):
    db_execute(
        "INSERT INTO audit_logs (identity, service, decision, reason, time) VALUES (?, ?, ?, ?, ?)",
        (identity, service, decision, reason, datetime.now(timezone.utc).isoformat()),
    )


# ---------- Tokens ----------
def create_token(username, role):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def read_token():
    """Returns (payload, error_message)."""
    parts = request.headers.get("Authorization", "").split(" ")
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
        return None, "Missing token"
    try:
        return jwt.decode(parts[1], JWT_SECRET, algorithms=["HS256"]), None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


# ---------- Decorators ----------
def authenticated(fn):
    """Verifies the token only (no audit entry). Used for /me, /stats, /logs, /users."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload, error = read_token()
        if error:
            return jsonify(error=error), 401
        g.user = {"username": payload["sub"], "role": payload["role"]}
        return fn(*args, **kwargs)
    return wrapper


def gateway(service, allowed_roles=None):
    """Verifies the token, checks the role against allowed_roles, and audits the decision.
    allowed_roles=None means any authenticated user may access the service."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            payload, error = read_token()
            if error:
                record("anonymous", service, "DENIED", error)
                return jsonify(error=error), 401

            g.user = {"username": payload["sub"], "role": payload["role"]}
            if allowed_roles and g.user["role"] not in allowed_roles:
                record(
                    g.user["username"], service, "DENIED",
                    f"Role '{g.user['role']}' not in {allowed_roles}",
                )
                return jsonify(error=f"Forbidden: requires one of {allowed_roles}"), 403

            record(
                g.user["username"], service, "ALLOWED",
                "Role verified" if allowed_roles else "Token verified",
            )
            return fn(*args, **kwargs)
        return wrapper
    return decorator
"""
db.py — SQLite database layer for Wikipedia Paraphraser AI
Tables: users, searches
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, date, timedelta

# /tmp/ persists between reruns on Streamlit Cloud within the same container session
DB_PATH = os.getenv("DB_PATH", "/tmp/paraphraser.db")


# ── connection ─────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safer for concurrent access
    return conn


# ── init ───────────────────────────────────────────────────────────────────────
def init_db():
    """Create tables if they don't exist. Safe to call on every app startup."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS searches (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            topic      TEXT    NOT NULL,
            lang       TEXT    NOT NULL,
            model      TEXT    NOT NULL,
            tone       TEXT    NOT NULL,
            length     TEXT    NOT NULL,
            original   TEXT    NOT NULL,
            paraphrase TEXT    NOT NULL,
            words_orig INTEGER NOT NULL DEFAULT 0,
            words_para INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ── password helpers ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}:{dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split(":", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# ── auth ───────────────────────────────────────────────────────────────────────
def register_user(username: str, email: str, password: str) -> tuple:
    """Returns (True, "") on success or (False, error_message) on failure."""
    username = username.strip()
    email    = email.strip().lower()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if "@" not in email or "." not in email:
        return False, "Please enter a valid email address."
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
            (username, email, hash_password(password), datetime.utcnow().isoformat()),
        )
        conn.commit()
        return True, ""
    except sqlite3.IntegrityError as e:
        if "username" in str(e).lower():
            return False, "Username already taken."
        if "email" in str(e).lower():
            return False, "Email already registered."
        return False, "Registration failed — please try again."
    finally:
        conn.close()


def login_user(username: str, password: str) -> tuple:
    """Returns (user_dict, "") on success or (None, error_message) on failure."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        if not row:
            return None, "Username not found."
        if not verify_password(password, row["password_hash"]):
            return None, "Incorrect password."
        return {"id": row["id"], "username": row["username"], "email": row["email"]}, ""
    finally:
        conn.close()


# ── searches ───────────────────────────────────────────────────────────────────
def save_search(user_id: int, topic: str, lang: str, model: str, tone: str, length: str,
                original: str, paraphrase: str, words_orig: int, words_para: int):
    """Save a completed search to the database. Silently fails if DB is unavailable."""
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO searches
               (user_id, topic, lang, model, tone, length, original, paraphrase,
                words_orig, words_para, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, topic, lang, model, tone, length, original, paraphrase,
             words_orig, words_para, datetime.utcnow().isoformat()),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def get_user_searches(user_id: int, limit: int = 100) -> list:
    """Return all searches for a user, newest first."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT id, topic, lang, model, tone, length, original, paraphrase,
                      words_orig, words_para, created_at
               FROM searches WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def delete_search(search_id: int, user_id: int):
    """Delete a search — only if it belongs to the requesting user."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM searches WHERE id = ? AND user_id = ?",
                     (search_id, user_id))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def get_user_stats(user_id: int) -> dict:
    """Return total searches and unique topics for a user."""
    conn = get_conn()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as total, COUNT(DISTINCT topic) as unique_topics
               FROM searches WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        return dict(row) if row else {"total": 0, "unique_topics": 0}
    except Exception:
        return {"total": 0, "unique_topics": 0}
    finally:
        conn.close()


# ── history grouping helper ───────────────────────────────────────────────────
def group_by_date(searches: list) -> dict:
    """Group a list of search dicts into Today / Yesterday / Last 7 Days / Older."""
    today     = date.today()
    yesterday = today - timedelta(days=1)
    week_ago  = today - timedelta(days=7)
    groups = {"Today": [], "Yesterday": [], "Last 7 Days": [], "Older": []}
    for s in searches:
        try:
            d = date.fromisoformat(s["created_at"][:10])
        except Exception:
            d = today
        if   d == today:     groups["Today"].append(s)
        elif d == yesterday: groups["Yesterday"].append(s)
        elif d >= week_ago:  groups["Last 7 Days"].append(s)
        else:                groups["Older"].append(s)
    return {k: v for k, v in groups.items() if v}

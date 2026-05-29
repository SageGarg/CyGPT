from __future__ import annotations
import hashlib
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "users.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username     TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt         TEXT NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    return con


def _hash(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def validate_password(password: str) -> str | None:
    """Returns an error string, or None if the password is valid."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"\d", password):
        return "Password must contain at least one number."
    return None


def validate_username(username: str) -> str | None:
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Username can only contain letters, numbers, and underscores."
    return None


def register(username: str, display_name: str, password: str) -> str | None:
    """Register a new user. Returns error string or None on success."""
    username = username.strip()
    display_name = display_name.strip() or username

    err = validate_username(username)
    if err:
        return err
    err = validate_password(password)
    if err:
        return err

    salt = os.urandom(16).hex()
    con = _conn()
    try:
        con.execute(
            "INSERT INTO users (username, display_name, password_hash, salt) VALUES (?, ?, ?, ?)",
            (username.lower(), display_name, _hash(password, salt), salt),
        )
        con.commit()
        return None
    except sqlite3.IntegrityError:
        return "Username already taken — please choose another."
    finally:
        con.close()


def login(username: str, password: str) -> tuple[str, str] | None:
    """Returns (username, display_name) on success, or None on failure."""
    con = _conn()
    try:
        row = con.execute(
            "SELECT display_name, password_hash, salt FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
        if row and _hash(password, row[2]) == row[1]:
            return username.strip().lower(), row[0]
        return None
    finally:
        con.close()

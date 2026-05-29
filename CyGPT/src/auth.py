from __future__ import annotations
import hashlib
import os
import re

from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL

# Supabase table that holds user accounts. Mirrors the original SQLite schema:
#   username (pk) · display_name · password_hash · salt · created_at
USERS_TABLE = "users"

_client: Client | None = None


def _supabase() -> Client:
    """Lazily build (and cache) the Supabase client."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
                "in your .env file."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


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
    try:
        _supabase().table(USERS_TABLE).insert(
            {
                "username": username.lower(),
                "display_name": display_name,
                "password_hash": _hash(password, salt),
                "salt": salt,
            }
        ).execute()
        return None
    except Exception as exc:  # noqa: BLE001 — surface a friendly message
        msg = str(exc).lower()
        # Postgres unique-violation (code 23505) → username already exists.
        if "duplicate" in msg or "23505" in msg or "already exists" in msg:
            return "Username already taken — please choose another."
        return f"Could not create account: {exc}"


def login(username: str, password: str) -> tuple[str, str, int] | None:
    """Returns (username, display_name, user_id) on success, or None on failure."""
    uname = username.strip().lower()
    resp = (
        _supabase()
        .table(USERS_TABLE)
        .select("id, display_name, password_hash, salt")
        .eq("username", uname)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return None

    row = rows[0]
    if _hash(password, row["salt"]) == row["password_hash"]:
        return uname, row["display_name"], row["id"]
    return None

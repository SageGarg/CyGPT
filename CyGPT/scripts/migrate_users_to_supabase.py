"""
One-off: copy existing users from the local SQLite DB (data/users.db) into the
Supabase `users` table. Safe to re-run — existing usernames are skipped.

Usage:
    python scripts/migrate_users_to_supabase.py

Requires SUPABASE_URL and SUPABASE_KEY in your .env (see .env.example), and the
Supabase table created via db/schema.sql.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth import USERS_TABLE, _supabase  # noqa: E402

SQLITE_PATH = Path(__file__).parent.parent / "data" / "users.db"


def main() -> None:
    if not SQLITE_PATH.exists():
        print(f"No local DB at {SQLITE_PATH} — nothing to migrate.")
        return

    con = sqlite3.connect(str(SQLITE_PATH))
    rows = con.execute(
        "SELECT username, display_name, password_hash, salt FROM users"
    ).fetchall()
    con.close()

    if not rows:
        print("Local DB has no users — nothing to migrate.")
        return

    client = _supabase()
    migrated, skipped = 0, 0
    for username, display_name, password_hash, salt in rows:
        existing = (
            client.table(USERS_TABLE)
            .select("username")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        if existing.data:
            skipped += 1
            continue
        client.table(USERS_TABLE).insert(
            {
                "username": username,
                "display_name": display_name,
                "password_hash": password_hash,
                "salt": salt,
            }
        ).execute()
        migrated += 1
        print(f"  migrated: {username}")

    print(f"\nDone. Migrated {migrated}, skipped {skipped} (already present).")


if __name__ == "__main__":
    main()

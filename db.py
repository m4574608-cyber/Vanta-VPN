import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = "vanta.db"


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TEXT NOT NULL,
                subscription_until TEXT
            )
            """
        )


def add_user(user_id, username, full_name):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users "
            "(user_id, username, full_name, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, now),
        )
        conn.execute(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (username, full_name, user_id),
        )


def get_user(user_id):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

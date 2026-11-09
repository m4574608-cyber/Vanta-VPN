import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

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


def _now():
    return datetime.now(timezone.utc)


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
    now = _now().isoformat(timespec="seconds")
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


def count_users():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def count_active():
    now = _now().isoformat(timespec="seconds")
    with db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE subscription_until > ?",
            (now,),
        ).fetchone()[0]


def add_days(user_id, days):
    user = get_user(user_id)
    if user is None:
        return None
    start = _now()
    if user["subscription_until"]:
        current = datetime.fromisoformat(user["subscription_until"])
        if current > start:
            start = current
    until = (start + timedelta(days=days)).isoformat(timespec="seconds")
    with db() as conn:
        conn.execute(
            "UPDATE users SET subscription_until = ? WHERE user_id = ?",
            (until, user_id),
        )
    return until

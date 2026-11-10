import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DB_PATH = "vanta.db"

NEW_COLUMNS = {
    "referrer_id": "INTEGER",
    "referral_counted": "INTEGER NOT NULL DEFAULT 0",
    "friends_used": "INTEGER NOT NULL DEFAULT 0",
    "last_reward_at": "TEXT",
}


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
                subscription_until TEXT,
                referrer_id INTEGER,
                referral_counted INTEGER NOT NULL DEFAULT 0,
                friends_used INTEGER NOT NULL DEFAULT 0,
                last_reward_at TEXT
            )
            """
        )
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
        for name, definition in NEW_COLUMNS.items():
            if name not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")


def add_user(user_id, username, full_name, referrer_id=None):
    """Добавить пользователя. Вернёт True, если он новый."""
    now = _now().isoformat(timespec="seconds")
    with db() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO users "
            "(user_id, username, full_name, created_at, referrer_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, now, referrer_id),
        )
        is_new = cur.rowcount == 1
        conn.execute(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (username, full_name, user_id),
        )
    return is_new


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


def count_referrals(user_id):
    """Сколько друзей засчитано этому пользователю."""
    with db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE referrer_id = ? AND referral_counted = 1",
            (user_id,),
        ).fetchone()[0]


def confirm_referral(user_id):
    """Засчитать приглашённого. Вернёт ID пригласившего или None."""
    with db() as conn:
        cur = conn.execute(
            "UPDATE users SET referral_counted = 1 "
            "WHERE user_id = ? AND referrer_id IS NOT NULL "
            "AND referral_counted = 0",
            (user_id,),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT referrer_id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["referrer_id"]


def referral_status(user_id, per, cooldown_days):
    """Состояние рефералки: сколько друзей, чего не хватает, можно ли забрать."""
    user = get_user(user_id)
    counted = count_referrals(user_id)
    free = counted - user["friends_used"]

    wait_days = 0
    if user["last_reward_at"]:
        ready_at = datetime.fromisoformat(user["last_reward_at"]) + timedelta(
            days=cooldown_days
        )
        now = _now()
        if now < ready_at:
            wait_days = math.ceil((ready_at - now).total_seconds() / 86400)

    return {
        "counted": counted,
        "need": max(0, per - free),
        "wait_days": wait_days,
        "can_claim": free >= per and wait_days == 0,
    }


def claim_referral_reward(user_id, per, days, cooldown_days):
    """Выдать награду, если хватает друзей и прошёл месяц.

    Вернёт дату окончания подписки или None, если награда недоступна.
    """
    now = _now()
    with db() as conn:
        row = conn.execute(
            "SELECT friends_used, last_reward_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None

        counted = conn.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE referrer_id = ? AND referral_counted = 1",
            (user_id,),
        ).fetchone()[0]
        if counted - row["friends_used"] < per:
            return None

        if row["last_reward_at"]:
            last = datetime.fromisoformat(row["last_reward_at"])
            if now < last + timedelta(days=cooldown_days):
                return None

        cur = conn.execute(
            "UPDATE users SET friends_used = friends_used + ?, "
            "last_reward_at = ? WHERE user_id = ? AND friends_used = ?",
            (per, now.isoformat(timespec="seconds"), user_id, row["friends_used"]),
        )
        if cur.rowcount == 0:
            return None
    return add_days(user_id, days)

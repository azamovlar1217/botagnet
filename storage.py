"""Doimiy xotira (SQLite): suhbat tarixi, oila a'zolari, eslatmalar, xotira, bozor budjeti.

Bot qayta ishga tushsa ham hech narsa yo'qolmaydi.
"""

import json
import os
import sqlite3
import time

from google.genai import types

_DIR = "/data" if os.path.isdir("/data") else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(_DIR, "agent.db"))

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS family (user_id INTEGER PRIMARY KEY, role TEXT, name TEXT, added REAL);
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, due REAL, text TEXT, done INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, added REAL);
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ts REAL, amount INTEGER, note TEXT);
    """
)
db.commit()


# ---------------------------------------------------------------- kalit-qiymat
def get(key: str, default=None):
    row = db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
    return json.loads(row["v"]) if row else default


def put(key: str, value):
    db.execute("INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)", (key, json.dumps(value, ensure_ascii=False)))
    db.commit()


# ---------------------------------------------------------------- suhbat tarixi
def load_history(key: str) -> list:
    raw = get(f"hist:{key}", [])
    out = []
    for item in raw:
        try:
            out.append(types.Content.model_validate_json(item))
        except Exception:
            pass
    return out


def save_history(key: str, history: list):
    put(f"hist:{key}", [c.model_dump_json(exclude_none=True) for c in history])


# ---------------------------------------------------------------- oila
def add_family(user_id: int, role: str, name: str):
    db.execute("INSERT OR REPLACE INTO family VALUES (?, ?, ?, ?)", (user_id, role, name, time.time()))
    db.commit()


def family_role(user_id: int) -> str | None:
    row = db.execute("SELECT role FROM family WHERE user_id=?", (user_id,)).fetchone()
    return row["role"] if row else None


def family_by_role(role: str) -> int | None:
    row = db.execute("SELECT user_id FROM family WHERE role=?", (role,)).fetchone()
    return row["user_id"] if row else None


def family_list() -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM family ORDER BY added").fetchall()


def remove_family(role: str):
    db.execute("DELETE FROM family WHERE role=?", (role,))
    db.commit()


# ---------------------------------------------------------------- eslatmalar
def add_reminder(chat_id: int, due: float, text: str) -> int:
    cur = db.execute("INSERT INTO reminders (chat_id, due, text) VALUES (?, ?, ?)", (chat_id, due, text))
    db.commit()
    return cur.lastrowid


def due_reminders(now: float) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM reminders WHERE done=0 AND due<=?", (now,)).fetchall()


def pending_reminders(chat_id: int) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM reminders WHERE done=0 AND chat_id=? ORDER BY due", (chat_id,)).fetchall()


def finish_reminder(rid: int):
    db.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
    db.commit()


# ---------------------------------------------------------------- uzoq muddatli xotira
def remember(text: str):
    db.execute("INSERT INTO memory (text, added) VALUES (?, ?)", (text, time.time()))
    db.commit()


def forget(fragment: str) -> int:
    cur = db.execute("DELETE FROM memory WHERE text LIKE ?", (f"%{fragment}%",))
    db.commit()
    return cur.rowcount


def memories() -> list[str]:
    return [r["text"] for r in db.execute("SELECT text FROM memory ORDER BY id")]


# ---------------------------------------------------------------- bozor budjeti
def add_expense(user_id: int, amount: int, note: str):
    db.execute("INSERT INTO expenses (user_id, ts, amount, note) VALUES (?, ?, ?, ?)",
               (user_id, time.time(), amount, note))
    db.commit()


def expenses_since(ts: float) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM expenses WHERE ts>=? ORDER BY ts", (ts,)).fetchall()

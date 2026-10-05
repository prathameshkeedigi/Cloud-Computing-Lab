"""
Notification Service (port 8004)
Responsibility: record notifications sent to members (borrow / return messages).
Database: its own SQLite file (notifications.db).
"""

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "data/notifications.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notifications (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   member_id INTEGER NOT NULL,
                   message TEXT NOT NULL,
                   created_at TEXT NOT NULL)"""
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Notification Service", version="1.0", lifespan=lifespan)


class NotificationIn(BaseModel):
    member_id: int
    message: str


@app.get("/health")
def health():
    return {"service": "notification-service", "status": "healthy"}


@app.post("/notifications", status_code=201)
def send_notification(note: NotificationIn):
    created = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO notifications (member_id, message, created_at) VALUES (?, ?, ?)",
            (note.member_id, note.message, created))
    return {"id": cur.lastrowid, "member_id": note.member_id,
            "message": note.message, "created_at": created}


@app.get("/notifications")
def list_notifications(member_id: int | None = None):
    with get_db() as conn:
        if member_id is None:
            rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM notifications WHERE member_id = ? ORDER BY id DESC",
                                (member_id,)).fetchall()
    return [dict(r) for r in rows]

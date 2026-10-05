"""
Borrow Service (port 8003) - entry point for multi-service requests
Responsibility: issue and return books. It talks to the other three services:
  - Member Service        -> is the member valid and active?
  - Book Service          -> does the book exist and is it available? update availability
  - Notification Service  -> send a message to the member
Database: its own SQLite file (borrows.db).

Other services are reached by their Docker Compose service names
(e.g. http://book-service:8001). The URLs come from environment variables so the
same code also runs locally (http://127.0.0.1:8001).
"""

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "data/borrows.db")
BOOK_URL = os.getenv("BOOK_SERVICE_URL", "http://127.0.0.1:8001")
MEMBER_URL = os.getenv("MEMBER_SERVICE_URL", "http://127.0.0.1:8002")
NOTIFY_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8004")

client = httpx.Client(timeout=5.0)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS borrows (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   member_id INTEGER NOT NULL,
                   book_id INTEGER NOT NULL,
                   borrowed_at TEXT NOT NULL,
                   returned_at TEXT)"""
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    client.close()


app = FastAPI(title="Borrow Service", version="1.0", lifespan=lifespan)


class BorrowIn(BaseModel):
    member_id: int
    book_id: int


def call(method, url, **kwargs):
    """Call another microservice; turn network errors into a clear 503."""
    try:
        return client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Cannot reach {url}: {exc.__class__.__name__}")


def fetch_member(member_id):
    r = call("GET", f"{MEMBER_URL}/members/{member_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Member not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Member Service returned an error")
    return r.json()


def fetch_book(book_id):
    r = call("GET", f"{BOOK_URL}/books/{book_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Book not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Book Service returned an error")
    return r.json()


def set_book_available(book_id, available):
    r = call("PATCH", f"{BOOK_URL}/books/{book_id}/availability", json={"available": available})
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Book Service could not update availability")


def notify(member_id, message):
    """Send a notification. If the Notification Service is down, the borrow/return
    still succeeds; only the message is skipped."""
    try:
        r = client.post(f"{NOTIFY_URL}/notifications",
                        json={"member_id": member_id, "message": message})
        r.raise_for_status()
        return r.json()["message"]
    except httpx.HTTPError:
        return "Not sent (Notification Service unavailable)"


@app.get("/health")
def health():
    return {"service": "borrow-service", "status": "healthy"}


@app.get("/services/status")
def services_status():
    """Ping every other service over the Docker network."""
    result = {"borrow-service": "healthy"}
    for name, url in [("book-service", BOOK_URL), ("member-service", MEMBER_URL),
                      ("notification-service", NOTIFY_URL)]:
        try:
            r = client.get(f"{url}/health")
            result[name] = r.json().get("status", "unknown")
        except httpx.RequestError:
            result[name] = "unreachable"
    return result


@app.get("/borrow/check")
def check_borrow(member_id: int, book_id: int):
    """Read-only end-to-end request (Client -> Borrow -> Member + Book).
    Used for workload testing because it does not change any data."""
    member = fetch_member(member_id)
    book = fetch_book(book_id)
    can_borrow = member["active"] and book["available"]
    return {"member": member["name"], "book": book["title"],
            "member_active": member["active"], "book_available": book["available"],
            "can_borrow": can_borrow}


@app.post("/borrow", status_code=201)
def borrow_book(req: BorrowIn):
    """Full end-to-end request touching all four services."""
    member = fetch_member(req.member_id)
    if not member["active"]:
        raise HTTPException(status_code=400, detail="Member is not active")
    book = fetch_book(req.book_id)
    if not book["available"]:
        raise HTTPException(status_code=409, detail="Book is already borrowed")

    set_book_available(req.book_id, False)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute("INSERT INTO borrows (member_id, book_id, borrowed_at) VALUES (?, ?, ?)",
                           (req.member_id, req.book_id, now))
        borrow_id = cur.lastrowid
    note = notify(req.member_id, f"You borrowed '{book['title']}' (borrow #{borrow_id}).")
    return {"borrow_id": borrow_id, "member": member["name"], "book": book["title"],
            "borrowed_at": now, "notification": note}


@app.post("/return/{borrow_id}")
def return_book(borrow_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM borrows WHERE id = ?", (borrow_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Borrow record not found")
    if row["returned_at"]:
        raise HTTPException(status_code=409, detail="Book already returned")

    book = fetch_book(row["book_id"])
    set_book_available(row["book_id"], True)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute("UPDATE borrows SET returned_at = ? WHERE id = ?", (now, borrow_id))
    note = notify(row["member_id"], f"You returned '{book['title']}'.")
    return {"borrow_id": borrow_id, "book": book["title"], "returned_at": now,
            "notification": note}


@app.get("/borrows")
def list_borrows():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM borrows ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]

"""
Book Service (port 8001)
Responsibility: manage the library book catalogue and book availability.
Database: its own SQLite file (books.db).
"""

import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "data/books.db")

SEED_BOOKS = [
    ("Clean Code", "Robert C. Martin"),
    ("Introduction to Algorithms", "Cormen et al."),
    ("Operating System Concepts", "Silberschatz"),
    ("Computer Networks", "Andrew Tanenbaum"),
    ("Cloud Computing: Concepts and Technology", "Thomas Erl"),
    ("Docker Deep Dive", "Nigel Poulton"),
    ("Designing Data-Intensive Applications", "Martin Kleppmann"),
    ("The Pragmatic Programmer", "Hunt and Thomas"),
    ("Database System Concepts", "Silberschatz"),
    ("Building Microservices", "Sam Newman"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS books (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   author TEXT NOT NULL,
                   available INTEGER NOT NULL DEFAULT 1)"""
        )
        if conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            conn.executemany("INSERT INTO books (title, author) VALUES (?, ?)", SEED_BOOKS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Service", version="1.0", lifespan=lifespan)


class BookIn(BaseModel):
    title: str
    author: str


class AvailabilityIn(BaseModel):
    available: bool


def row_to_book(row):
    return {"id": row["id"], "title": row["title"], "author": row["author"],
            "available": bool(row["available"])}


@app.get("/health")
def health():
    return {"service": "book-service", "status": "healthy"}


@app.get("/books")
def list_books():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [row_to_book(r) for r in rows]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row_to_book(row)


@app.post("/books", status_code=201)
def add_book(book: BookIn):
    with get_db() as conn:
        cur = conn.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                           (book.title, book.author))
        book_id = cur.lastrowid
    return get_book(book_id)


@app.patch("/books/{book_id}/availability")
def set_availability(book_id: int, body: AvailabilityIn):
    get_book(book_id)  # 404 if missing
    with get_db() as conn:
        conn.execute("UPDATE books SET available = ? WHERE id = ?",
                     (int(body.available), book_id))
    return get_book(book_id)

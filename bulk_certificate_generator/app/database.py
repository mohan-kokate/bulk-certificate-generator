import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "certificates.db"))

def connect():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            total INTEGER NOT NULL,
            succeeded INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            recipient_name TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            status TEXT NOT NULL,
            file_path TEXT,
            error TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        """)

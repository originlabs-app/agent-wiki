"""Database module — SQLite connection management."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_DB = Path("atlas.db")
_connection: sqlite3.Connection | None = None


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get or create a database connection (singleton per process)."""
    global _connection
    if _connection is None:
        path = db_path or _DEFAULT_DB
        _connection = sqlite3.connect(str(path))
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _init_schema(_connection)
    return _connection


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript(\"""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            tokens INTEGER NOT NULL,
            ts REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            period TEXT NOT NULL,
            total_tokens INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    \""")


@contextmanager
def transaction(db_path: Path | None = None):
    """Context manager for database transactions."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

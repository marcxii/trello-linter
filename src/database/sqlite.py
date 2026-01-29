"""SQLite connection helpers for request-scoped access."""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from flask import current_app, g


def _db_path() -> str:
    path = current_app.config.get("SQLITE_DB_PATH")
    if path:
        return path

    # Default to instance folder (not tracked)
    return os.path.join(current_app.instance_path, "trelloscore.db")


def get_db() -> sqlite3.Connection:
    """Get a request-scoped SQLite connection."""
    conn: Optional[sqlite3.Connection] = g.get("sqlite_db")
    if conn is not None:
        return conn

    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    # Optional pragmas for smoother concurrent access.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=3000;")

    g.sqlite_db = conn
    return conn


def close_db(_error: Exception | None = None) -> None:
    """Close the request-scoped SQLite connection, if any."""
    conn: Optional[sqlite3.Connection] = g.pop("sqlite_db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    """Initialize SQLite schema if missing."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            board_ref TEXT,
            report_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runs_session_created
        ON runs(session_id, created_at)
        """
    )
    conn.commit()

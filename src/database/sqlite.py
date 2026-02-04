"""Flask-aware SQLite database connection management.

This module provides Flask integration for SQLite:
- get_db(): Returns connection using app.config["SQLITE_DB_PATH"]
- init_db(): Initializes database schema from schema.sql
- close_db(): Cleanup on request teardown
- cleanup_runs(): Wrapper for cleanup function
"""
from __future__ import annotations


import sqlite3
from flask import current_app, g
from pathlib import Path

def get_db():
    """Get database connection for current request."""
    if 'db' not in g:
        db_path = current_app.config.get('SQLITE_DB_PATH')

        # in case DB path is not config properly
        if not db_path:
            raise RuntimeError("SQLITE_DB_PATH not configured in Flask app")
    
        #create connection
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row

        #set important sqllite pragams
        g.db.execute("PRAGMA foreign_keys = ON")           # Enable FK constraints
        g.db.execute("PRAGMA journal_mode = WAL")          # Write-Ahead Logging (better concurrency)
        g.db.execute("PRAGMA busy_timeout = 5000")         # Wait 5 seconds on lock (prevents "database is locked")
        g.db.execute("PRAGMA synchronous = NORMAL")        # Balance safety and performance
        g.db.execute("PRAGMA cache_size = -64000")         # 64MB cache (better performance)
        g.db.execute("PRAGMA temp_store = MEMORY")         # Use memory for temp tables
    return g.db

def close_db(exception=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with schema."""
    db = get_db()
    
    # Load schema from file, should be in same directory as this file
    schema_path = Path(__file__).parent / 'schema.sql'

    if not schema_path.exists():
        raise FileNotFoundError(
            f"Database schema not found at: {schema_path}"
            f"Create src/database/schema.sql with your table functions"
        )

    #Execute db schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    
    db.commit()

def cleanup_runs(ttl_seconds: int):
    """Clean up old runs."""
    from src.database.db_functions import cleanup_old_runs
    db = get_db()
    return cleanup_old_runs(db, ttl_seconds)
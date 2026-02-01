
import sqlite3
from flask import current_app, g
from pathlib import Path

def get_db():
    """Get database connection for current request."""
    if 'db' not in g:
        db_path = current_app.config.get('instance', 'trelloscore.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(exception=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with schema."""
    db = get_db()
    
    # Load schema from file
    schema_path = Path(__file__).parent / 'schema.sql'
    with open(schema_path, 'r') as f:
        db.executescript(f.read())
    
    db.commit()

def cleanup_runs(ttl_seconds: int):
    """Clean up old runs."""
    from src.database.db_functions import cleanup_old_runs
    db = get_db()
    return cleanup_old_runs(db, ttl_seconds)
import json
import sqlite3
from datetime import datetime, timezone


def test_count_overdue_cards(app):
    from src.linter.rule_engine import count_overdue_cards

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    cur = conn.execute(
        """
        INSERT INTO runs (session_id, created_at, board_ref, report_json)
        VALUES (?, ?, ?, ?)
        """,
        ("test-session", "2026-01-10T00:00:00+00:00", "Test Board", json.dumps({})),
    )
    run_id = cur.lastrowid
    conn.executemany(
        """
        INSERT INTO cards (run_id, card_name, due)
        VALUES (?, ?, ?)
        """,
        [
            (run_id, "Past Due A", "2026-01-08T00:00:00.000Z"),
            (run_id, "Past Due B", "2026-01-09T23:59:59.000Z"),
            (run_id, "Future", "2026-01-12T00:00:00.000Z"),
            (run_id, "No Due", None),
        ],
    )
    conn.commit()
    conn.close()

    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    with app.app_context():
        count = count_overdue_cards(run_id, now=now)

    assert count == 2

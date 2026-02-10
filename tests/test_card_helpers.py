import io
import json
import sqlite3

from src.database.db_functions import get_card_for_run, get_findings_for_card


def _insert_run(conn):
    cur = conn.execute(
        "INSERT INTO runs (session_id, created_at, board_ref) VALUES (?, ?, ?)",
        ("sess", "2026-02-06T00:00:00+00:00", "Board"),
    )
    conn.commit()
    return cur.lastrowid


def test_get_card_for_run_returns_card(app):
    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    conn.row_factory = sqlite3.Row

    run_id = _insert_run(conn)
    conn.execute(
        """
        INSERT INTO cards (
            run_id, card_id, card_name, card_desc, list_id, list_name,
            due, is_closed, members, labels, checklists
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            "c1",
            "Card One",
            "desc",
            "l1",
            "To Do",
            "2026-02-06T04:16:56+00:00",
            0,
            "[]",
            "[]",
            "[]",
        ),
    )
    conn.commit()

    card = get_card_for_run(conn, run_id, "c1")
    conn.close()

    assert card is not None
    assert card["card_id"] == "c1"
    assert card["card_name"] == "Card One"
    assert card["list_name"] == "To Do"


def test_get_findings_for_card_orders_by_severity(app):
    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    conn.row_factory = sqlite3.Row

    run_id = _insert_run(conn)
    conn.executemany(
        """
        INSERT INTO findings (
            run_id, card_id, card_name, rule_name, category, severity,
            description, suggestion, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (run_id, "c1", "Card One", "Rule A", "Cat", "minor", "minor issue", "", "2026-02-06T00:00:00+00:00"),
            (run_id, "c1", "Card One", "Rule B", "Cat", "critical", "critical issue", "", "2026-02-06T00:00:00+00:00"),
            (run_id, "c1", "Card One", "Rule C", "Cat", "major", "major issue", "", "2026-02-06T00:00:00+00:00"),
        ],
    )
    conn.commit()

    findings = get_findings_for_card(conn, run_id, "c1")
    conn.close()

    assert [f["severity"] for f in findings] == ["critical", "major", "minor"]


def test_card_partial_shows_short_url(client, app):
    payload = {
        "name": "Short URL Board",
        "cards": [
            {
                "id": "c-short",
                "name": "Card with URL",
                "idList": "l1",
                "idMembers": [],
                "shortUrl": "https://trello.com/c/abcd1234",
            }
        ],
        "lists": [{"id": "l1", "name": "To Do", "closed": False}],
        "members": [],
    }
    data = {"file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "board.json")}
    res = client.post("/partials/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    run_id = row[0]

    res = client.get(f"/partials/card?run_id={run_id}&card_id=c-short")
    assert res.status_code == 200
    assert b"https://trello.com/c/abcd1234" in res.data

import io
import json
import sqlite3


def _create_run_with_overdue(client, app):
    payload = {
        "name": "Overdue Board",
        "cards": [
            {
                "id": "c1",
                "name": "Overdue Card",
                "idList": "l1",
                "idMembers": ["m1"],
                "due": "2000-01-01T00:00:00.000Z",
            },
            {
                "id": "c2",
                "name": "Not Overdue Card",
                "idList": "l1",
                "idMembers": ["m1"],
                "due": "2099-01-01T00:00:00.000Z",
            },
        ],
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "members": [{"id": "m1", "fullName": "Alex", "username": "alex"}],
    }
    data = {"file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "board.json")}
    res = client.post("/partials/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    return row[0]


def test_results_overdue_uses_rule_results(client, app):
    run_id = _create_run_with_overdue(client, app)
    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT session_id FROM runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    assert row is not None
    session_id = row[0]

    with app.app_context():
        from src.reports.report_builder import load_report_context
        report_ctx = load_report_context(run_id, session_id)

    assert report_ctx is not None
    overdue_cards = report_ctx.get("overdue_cards", [])
    assert len(overdue_cards) == 1
    assert overdue_cards[0].get("name") == "Overdue Card"


def test_card_partial_overdue_uses_rule_results(client, app):
    run_id = _create_run_with_overdue(client, app)
    res = client.get(f"/partials/card?run_id={run_id}&card_id=c1")
    assert res.status_code == 200
    assert b"Overdue:" in res.data

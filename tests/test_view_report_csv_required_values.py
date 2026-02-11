import io
import json
import sqlite3


def _make_payload():
    return {
        "name": "Required Values Board",
        "cards": [
            {
                "id": "c1",
                "name": "Card 1",
                "idList": "l1",
                "idMembers": ["m1"],
                "due": "2099-01-01T00:00:00.000Z",
            }
        ],
        "lists": [{"id": "l1", "name": "To Do", "closed": False}],
        "members": [{"id": "m1", "fullName": "Alex", "username": "alex"}],
    }


def _create_run(client, app):
    data = {
        "file": (
            io.BytesIO(json.dumps(_make_payload()).encode("utf-8")),
            "board.json",
            "application/json",
        )
    }
    res = client.post("/partials/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    return row[0]


def test_results_partial_contains_required_values(client, app):
    run_id = _create_run(client, app)
    res = client.get(f"/partials/results?run_id={run_id}")
    assert res.status_code == 200
    assert b"Overall Quality Score" in res.data
    assert b"Findings by Rule" in res.data
    assert b"Quick Stats" in res.data
    assert b"Board:" in res.data
    assert b"Required Values Board" in res.data


def test_report_overlay_contains_required_values(client, app):
    run_id = _create_run(client, app)
    res = client.get(f"/partials/report?run_id={run_id}")
    assert res.status_code == 200
    assert b"TrelloScore Report" in res.data
    assert b"Scorecard" in res.data
    assert b"Quick Stats" in res.data
    assert b"Required Values Board" in res.data


def test_csv_export_contains_required_sections(client, app):
    run_id = _create_run(client, app)
    res = client.get(f"/export/findings.csv?run_id={run_id}")
    assert res.status_code == 200
    csv_text = res.data.decode("utf-8")
    assert "Run Info" in csv_text
    assert "Quick Stats" in csv_text
    assert "Scorecard" in csv_text
    assert "Findings by Rule" in csv_text
    assert "Required Values Board" in csv_text

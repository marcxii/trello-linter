import io
import json
import sqlite3

from src.controllers import partials_controller


def _make_payload():
    return {
        "name": "Test Board",
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


def _post_analyze(client, payload, filename="board.json", content_type="application/json"):
    data = {
        "file": (
            io.BytesIO(json.dumps(payload).encode("utf-8")),
            filename,
            content_type,
        )
    }
    return client.post("/partials/analyze", data=data, content_type="multipart/form-data")


def test_analyze_missing_file(client):
    res = client.post("/partials/analyze", data={}, content_type="multipart/form-data")
    assert res.status_code == 200
    assert b"Missing file" in res.data


def test_analyze_invalid_file_type(client):
    res = _post_analyze(client, _make_payload(), filename="board.txt")
    assert res.status_code == 200
    assert b"Invalid file type" in res.data


def test_analyze_invalid_mimetype(client):
    res = _post_analyze(client, _make_payload(), content_type="text/plain")
    assert res.status_code == 200
    assert b"Invalid file type" in res.data


def test_analyze_invalid_json(client):
    data = {"file": (io.BytesIO(b"{bad json"), "board.json", "application/json")}
    res = client.post("/partials/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert b"Invalid JSON file" in res.data


def test_analyze_invalid_trello_export(client):
    res = _post_analyze(client, {"cards": []})
    assert res.status_code == 200
    assert b"Invalid Trello export" in res.data


def test_analyze_rule_engine_error(client, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise Exception("boom")

    monkeypatch.setattr(partials_controller.RuleEngine, "run_all_rules", _raise)
    res = _post_analyze(client, _make_payload())
    assert res.status_code == 200
    assert b"Rule engine error: boom" in res.data


def test_analyze_scoring_error(client, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise Exception("boom")

    monkeypatch.setattr(partials_controller, "calculate_overall_score", _raise)
    res = _post_analyze(client, _make_payload())
    assert res.status_code == 200
    assert b"Scoring error: boom" in res.data


def test_analyze_happy_path_persists_run(client, app):
    res = _post_analyze(client, _make_payload())
    assert res.status_code == 200
    assert b"Findings by Rule" in res.data

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None


def test_analyze_saves_findings(client, monkeypatch):
    captured = {}

    def _capture_findings(conn, run_id, findings):
        captured["run_id"] = run_id
        captured["findings"] = findings

    def _rule_results(*_args, **_kwargs):
        return [
            {
                "rule_id": "card_ownership",
                "rule_name": "Card Ownership",
                "fail_count": 1,
                "eligible_count": 1,
                "passed": False,
                "failures": [
                    {
                        "card_id": "c1",
                        "card_name": "Card 1",
                        "reason": "No owner",
                    }
                ],
            }
        ]

    monkeypatch.setattr(partials_controller.RuleEngine, "run_all_rules", _rule_results)
    monkeypatch.setattr(partials_controller, "save_findings", _capture_findings)

    res = _post_analyze(client, _make_payload())
    assert res.status_code == 200
    assert captured.get("findings")
    assert captured["findings"][0]["rule_name"] == "Card Ownership"


def test_results_partial_missing_run_id(client):
    res = client.get("/partials/results")
    assert res.status_code == 200
    assert b"Report not found" in res.data


def test_report_partial_missing_run_id(client):
    res = client.get("/partials/report")
    assert res.status_code == 200
    assert b"Missing run ID" in res.data

import io
import json
import sqlite3
from pathlib import Path

import yaml

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


RULE_IDS = [
    "card_ownership",
    "card_due_date",
    "card_descriptiveness",
    "story_point_estimation",
    "past_due_violation",
    "progress_threshold",
    "progress_monitoring",
    "card_completion",
    "card_effort",
    "description_canonicalization",
]


def _save_settings(client, overrides):
    data = {f"rule_{rule_id}": "on" for rule_id in overrides.get("enabled_rules", [])}
    data.update(overrides.get("thresholds", {}))
    return client.post("/partials/report-settings", data=data)


def _latest_report_json(app):
    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT report_json FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    return json.loads(row[0])


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


def test_analyze_includes_rule_description_tooltip(client):
    res = _post_analyze(client, _make_payload())
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    expected = config.get("card_descriptiveness", {}).get("description", "")
    assert f'data-tooltip="{expected}"' in html


def test_rule_settings_persist_and_disable_rule(client, app):
    enabled_rules = [rule_id for rule_id in RULE_IDS if rule_id != "card_ownership"]
    _save_settings(
        client,
        {
            "enabled_rules": enabled_rules,
            "thresholds": {
                "minimum_desc_char": "20",
                "max_wip_per_member": "3",
                "threshold_num_days": "5",
            },
        },
    )

    payload = {
        "name": "Ownership Disabled",
        "cards": [
            {
                "id": "c1",
                "name": "Unowned",
                "idList": "l1",
                "idMembers": [],
            }
        ],
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "members": [],
    }
    res = _post_analyze(client, payload)
    assert res.status_code == 200
    assert b"Card Ownership" not in res.data

    report = _latest_report_json(app)
    rule_ids = {rule.get("rule_id") for rule in report.get("rule_results", [])}
    assert "card_ownership" not in rule_ids
    assert report.get("rule_settings", {}).get("rules", {}).get("card_ownership") is False


def test_progress_threshold_override_affects_results(client, app):
    enabled_rules = RULE_IDS
    _save_settings(
        client,
        {
            "enabled_rules": enabled_rules,
            "thresholds": {
                "minimum_desc_char": "20",
                "max_wip_per_member": "5",
                "threshold_num_days": "5",
            },
        },
    )

    payload = {
        "name": "Progress Threshold",
        "cards": [
            {"id": "c1", "name": "A", "idList": "l1", "idMembers": ["m1"]},
            {"id": "c2", "name": "B", "idList": "l1", "idMembers": ["m1"]},
            {"id": "c3", "name": "C", "idList": "l1", "idMembers": ["m1"]},
            {"id": "c4", "name": "D", "idList": "l1", "idMembers": ["m1"]},
        ],
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "members": [{"id": "m1", "fullName": "Alex", "username": "alex"}],
    }
    res = _post_analyze(client, payload)
    assert res.status_code == 200

    report = _latest_report_json(app)
    progress_rule = next(
        rule for rule in report.get("rule_results", [])
        if rule.get("rule_id") == "progress_threshold"
    )
    assert progress_rule["fail_count"] == 0


def test_settings_ui_includes_enabled_rules(client):
    res = client.get("/partials/report-settings")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    config_path = Path("config") / "rules_config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    deprecated = {
        "weekly_workload",
        "individual_overload",
        "near_term_overcommitment",
        "unscheduled_work",
        "flow_progress_signal",
    }
    ignore_sections = {"weights", "lists", "scoring"}
    for rule_id, rule_cfg in config.items():
        if not isinstance(rule_cfg, dict):
            continue
        if rule_id in ignore_sections:
            continue
        if rule_id in deprecated:
            continue
        if rule_cfg.get("enabled", True):
            assert f'name="rule_{rule_id}"' in html


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

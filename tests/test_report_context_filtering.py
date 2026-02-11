from src.database.db_functions import save_cards, save_members, save_run
from src.database.sqlite import get_db
from src.reports.report_builder import load_report_context


def _seed_run(app, session_id="test-session"):
    board_data = {
        "board": {"id": "b1", "name": "Test Board", "desc": ""},
        "lists": [{"id": "l1", "name": "To Do"}],
        "members": [
            {"id": "m1", "fullName": "Alice", "username": "alice"},
            {"id": "m2", "fullName": "Bob", "username": "bob"},
        ],
        "cards": [
            {
                "id": "c1",
                "name": "Card A",
                "desc": "",
                "list_id": "l1",
                "due": "2000-01-01T00:00:00.000Z",
                "closed": False,
                "members": ["m1"],
            },
            {
                "id": "c2",
                "name": "Card B",
                "desc": "",
                "list_id": "l1",
                "due": "2000-01-02T00:00:00.000Z",
                "closed": False,
                "members": ["m2"],
            },
            {
                "id": "c3",
                "name": "Card C",
                "desc": "",
                "list_id": "l1",
                "due": None,
                "closed": False,
                "members": [],
            },
        ],
    }

    report_json = {
        "board": {
            "name": "Test Board",
            "cards_count": 3,
            "lists_count": 1,
            "members_count": 2,
        },
        "scores": {"overall_score": 90},
        "summary": {},
        "rule_results": [
            {
                "rule_id": "rule_one",
                "rule_name": "Rule One",
                "fail_count": 2,
                "eligible_count": 2,
                "failures": [
                    {"card_id": "c1"},
                    {"card_id": "c3", "card_name": "Card C", "list_name": "To Do"},
                ],
            },
            {
                "rule_id": "rule_two",
                "rule_name": "Rule Two",
                "fail_count": 1,
                "eligible_count": 1,
                "failures": [
                    {"member_name": "Bob", "reason": "Overloaded"},
                ],
            },
        ],
    }

    scores = {
        "overall_score": 90,
        "category_scores": {},
        "total_findings": 3,
        "critical_findings": 0,
        "major_findings": 3,
        "minor_findings": 0,
    }

    with app.app_context():
        db = get_db()
        run_id = save_run(db, session_id, board_data, scores, report_json)
        list_map = {lst["id"]: lst["name"] for lst in board_data["lists"]}
        save_cards(db, run_id, board_data["cards"], list_map=list_map)
        save_members(db, run_id, board_data["members"])

    return run_id


def test_report_context_filters_rule_rows_by_member(app):
    run_id = _seed_run(app)

    with app.app_context():
        ctx = load_report_context(run_id, "test-session", ["Alice"])

    assert ctx is not None
    rule_results = ctx.get("rule_results", [])
    assert rule_results
    failure = rule_results[0]["failures"][0]
    assert failure.get("members") == ["Alice"]
    rule_rows = ctx["rule_rows"]
    assert rule_rows
    assert all(row[3] == "Alice" for row in rule_rows)
    assert all("Bob" not in row for row in rule_rows)


def test_report_overlay_uses_card_lookup_for_members_and_due(app, client):
    run_id = _seed_run(app, session_id="overlay-session")

    with client.session_transaction() as session:
        session["session_id"] = "overlay-session"

    res = client.get(f"/partials/report?run_id={run_id}&members=Alice")
    assert res.status_code == 200
    assert b"Alice" in res.data
    assert b"2000-01-01" in res.data
    assert b"Bob" not in res.data


def test_results_findings_use_partial_and_expanded(client, app):
    run_id = _seed_run(app, session_id="results-session")
    with client.session_transaction() as session:
        session["session_id"] = "results-session"
    res = client.get(f"/partials/results?run_id={run_id}&expanded=rule_one")
    assert res.status_code == 200
    assert b"Rule One" in res.data
    assert b"View Card" in res.data
    assert b"data-rule-id=\"rule_one\"" in res.data

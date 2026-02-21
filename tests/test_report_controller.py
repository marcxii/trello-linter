from tests.helpers import create_run_from_payload


def _make_payload():
    return {
        "name": "Report Controller Board",
        "cards": [
            {
                "id": "c1",
                "name": "Card 1",
                "idList": "l1",
                "idMembers": [],
                "due": None,
                "closed": False,
            }
        ],
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "members": [{"id": "m1", "fullName": "Alex", "username": "alex"}],
    }


def _create_run(client, app):
    return create_run_from_payload(client, app, _make_payload())


def test_report_route_returns_404_for_missing_run(client):
    res = client.get("/report/999999")
    assert res.status_code == 404
    assert b"Report not found for this session." in res.data


def test_report_route_renders_report_page(client, app):
    run_id = _create_run(client, app)
    res = client.get(f"/report/{run_id}")
    assert res.status_code == 200
    assert b"TrelloScore Report" in res.data
    assert b"Scorecard" in res.data
    assert b"Report Controller Board" in res.data


def test_report_route_supports_print_mode(client, app):
    run_id = _create_run(client, app)
    res = client.get(f"/report/{run_id}?print=1")
    assert res.status_code == 200
    assert b"print-mode" in res.data


def test_report_latest_placeholder_returns_400(client):
    res = client.get("/report")
    assert res.status_code == 400
    assert b"No report selected" in res.data


def test_report_route_recalculates_when_rule_disabled(client, app):
    payload = {
        "name": "Disabled Rule Report Board",
        "cards": [{"id": "c1", "name": "Card 1", "idList": "l1", "idMembers": [], "due": None, "closed": False}],
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "members": [],
    }
    run_id = create_run_from_payload(client, app, payload)
    with client.session_transaction() as sess:
        sess["rule_settings_overrides"] = {"rules": {"card_due_date": False}}

    res = client.get(f"/report/{run_id}")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "card_due_date" not in html

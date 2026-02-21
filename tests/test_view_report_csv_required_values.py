from tests.helpers import create_run_from_payload


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
    return _create_run_with_payload(client, app, _make_payload())


def _create_run_with_payload(client, app, payload):
    return create_run_from_payload(client, app, payload)


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


def test_csv_export_filters_rows_by_selected_member(client, app):
    payload = {
        "name": "Member Filter Board",
        "cards": [
            {"id": "c1", "name": "Alex Card", "idList": "l1", "idMembers": ["m1"], "due": None, "closed": False},
            {"id": "c2", "name": "Bob Card", "idList": "l1", "idMembers": ["m2"], "due": None, "closed": False},
        ],
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "members": [
            {"id": "m1", "fullName": "Alex", "username": "alex"},
            {"id": "m2", "fullName": "Bob", "username": "bob"},
        ],
    }
    run_id = _create_run_with_payload(client, app, payload)
    res = client.get(f"/export/findings.csv?run_id={run_id}&members=Alex")
    assert res.status_code == 200
    csv_text = res.data.decode("utf-8")
    assert "Alex Card" in csv_text
    assert "Bob Card" not in csv_text


def test_csv_export_excludes_disabled_rules(client, app):
    payload = {
        "name": "Disabled Rule Board",
        "cards": [
            {"id": "c1", "name": "Due Missing", "idList": "l1", "idMembers": ["m1"], "due": None, "closed": False},
            {"id": "c2", "name": "Unowned Done", "idList": "l2", "idMembers": [], "due": None, "closed": False},
        ],
        "lists": [
            {"id": "l1", "name": "In Progress", "closed": False},
            {"id": "l2", "name": "Done", "closed": False},
        ],
        "members": [{"id": "m1", "fullName": "Alex", "username": "alex"}],
    }
    run_id = _create_run_with_payload(client, app, payload)
    with client.session_transaction() as sess:
        sess["rule_settings_overrides"] = {"rules": {"card_due_date": False}}

    res = client.get(f"/export/findings.csv?run_id={run_id}")
    assert res.status_code == 200
    csv_text = res.data.decode("utf-8")
    assert "Card Ownership" in csv_text
    assert "Card Due Date" not in csv_text

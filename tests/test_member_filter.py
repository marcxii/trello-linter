import io
import json
import sqlite3


def _payload_with_members():
    return {
        "name": "Filter Board",
        "cards": [
            {
                "id": "c1",
                "name": "Card Paul",
                "idList": "l1",
                "idMembers": ["m1"],
                "due": "2000-01-01T00:00:00.000Z",
            },
            {
                "id": "c2",
                "name": "Card Amy",
                "idList": "l1",
                "idMembers": ["m2"],
                "due": "2000-01-02T00:00:00.000Z",
            },
            {
                "id": "c3",
                "name": "Card None",
                "idList": "l1",
                "idMembers": [],
                "due": "2000-01-03T00:00:00.000Z",
            },
        ],
        "lists": [
            {"id": "l1", "name": "To Do", "closed": False},
        ],
        "members": [
            {"id": "m1", "fullName": "Paul", "username": "paul"},
            {"id": "m2", "fullName": "Amy", "username": "amy"},
        ],
    }


def _create_run(client, app):
    payload = json.dumps(_payload_with_members()).encode("utf-8")
    data = {"file": (io.BytesIO(payload), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    return row[0]


def test_results_filter_by_member_name(client, app):
    run_id = _create_run(client, app)

    res = client.get(f"/partials/results?run_id={run_id}&members=Paul")
    assert res.status_code == 200
    assert b"Card Paul" in res.data
    assert b"Card Amy" not in res.data
    assert b"Card None" not in res.data


def test_results_filter_unassigned_only(client, app):
    run_id = _create_run(client, app)

    res = client.get(f"/partials/results?run_id={run_id}&members=Unassigned")
    assert res.status_code == 200
    assert b"Card None" in res.data
    assert b"Card Paul" not in res.data
    assert b"Card Amy" not in res.data

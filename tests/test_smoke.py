import io
import json
import re
import sqlite3


def _valid_trello_payload():
    return {
        "name": "Sample Board",
        "cards": [
            {"id": "c1", "name": "Card One", "idList": "l1", "due": None},
        ],
        "lists": [
            {"id": "l1", "name": "To Do", "closed": False},
        ],
        "members": [
            {"id": "m1", "fullName": "Alex Example", "username": "alex"},
        ],
    }


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_partials_upload_get(client):
    res = client.get("/partials/upload")
    assert res.status_code == 200
    assert b'id="dropZone"' in res.data


def test_partials_analyze_requires_file(client):
    res = client.post("/partials/analyze", data={}, content_type="multipart/form-data")
    assert res.status_code == 200
    assert b"Missing file" in res.data


def test_partials_analyze_rejects_wrong_type(client):
    data = {"file": (io.BytesIO(b"not-json"), "notes.txt")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200
    assert b"Invalid file type" in res.data


def test_partials_analyze_accepts_json(client):
    payload = json.dumps(_valid_trello_payload()).encode("utf-8")
    data = {"file": (io.BytesIO(payload), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200
    assert b'id="results"' in res.data
    assert b'class="results active"' in res.data


def test_session_id_set_on_first_load(client):
    client.get("/")
    with client.session_transaction() as sess:
        assert sess.get("session_id")


def test_session_id_persists_across_requests(client):
    client.get("/")
    with client.session_transaction() as sess:
        first_id = sess.get("session_id")

    client.get("/health")
    with client.session_transaction() as sess:
        assert sess.get("session_id") == first_id


def test_analyze_creates_run_scoped_to_session(client, app):
    client.get("/")
    with client.session_transaction() as sess:
        session_id = sess.get("session_id")

    payload = json.dumps(_valid_trello_payload()).encode("utf-8")
    data = {"file": (io.BytesIO(payload), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute(
        "SELECT id, session_id FROM runs WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    conn.close()
    assert row is not None


def test_other_session_cannot_access_run(client, app):
    payload = json.dumps(_valid_trello_payload()).encode("utf-8")
    data = {"file": (io.BytesIO(payload), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute(
        "SELECT id FROM runs ORDER BY id DESC LIMIT 1",
    ).fetchone()
    conn.close()
    assert row is not None
    run_id = row[0]

    other = app.test_client()
    res_other = other.get(f"/report/{run_id}")
    assert res_other.status_code == 404


def test_partials_results_missing_run_returns_upload_error(client):
    res = client.get("/partials/results?run_id=999999")
    assert res.status_code == 200
    assert b"Report not found" in res.data
    assert b'id="dropZone"' in res.data


def test_partials_card_includes_back_to_report_run_id(client):
    res = client.get("/partials/card?run_id=123")
    assert res.status_code == 200
    assert b"Back to Report" in res.data
    assert b"run_id=123" in res.data


def test_partials_results_valid_run_renders_board_name(client, app):
    client.get("/")
    with client.session_transaction() as sess:
        session_id = sess.get("session_id")

    payload = json.dumps(_valid_trello_payload()).encode("utf-8")
    data = {"file": (io.BytesIO(payload), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute(
        "SELECT id FROM runs WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    conn.close()
    assert row is not None
    run_id = row[0]

    res_results = client.get(f"/partials/results?run_id={run_id}")
    assert res_results.status_code == 200
    assert b"Sample Board" in res_results.data


def test_partials_results_includes_view_card_links(client, app):
    client.get("/")
    with client.session_transaction() as sess:
        session_id = sess.get("session_id")

    payload = json.dumps(_valid_trello_payload()).encode("utf-8")
    data = {"file": (io.BytesIO(payload), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute(
        "SELECT id FROM runs WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    conn.close()
    assert row is not None
    run_id = row[0]

    res_results = client.get(f"/partials/results?run_id={run_id}")
    assert res_results.status_code == 200
    assert f"/partials/card?run_id={run_id}".encode("utf-8") in res_results.data


def test_index_has_help_panel(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b'id="helpButton"' in res.data
    assert b'id="helpPanel"' in res.data

    

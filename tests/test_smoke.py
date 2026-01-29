import io
import re
import sqlite3


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
    data = {"file": (io.BytesIO(b"{\"ok\": true}"), "board.json")}
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

    data = {"file": (io.BytesIO(b"{\"ok\": true}"), "board.json")}
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
    data = {"file": (io.BytesIO(b"{\"ok\": true}"), "board.json")}
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

    

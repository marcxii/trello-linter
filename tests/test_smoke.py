import io


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_partials_upload_get(client):
    res = client.get("/partials/upload")
    assert res.status_code == 200
    assert b'id="dropZone"' in res.data


def test_partials_analyze_requires_file(client):
    res = client.post("/partials/analyze", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert b"Missing file" in res.data


def test_partials_analyze_rejects_wrong_type(client):
    data = {"file": (io.BytesIO(b"not-json"), "notes.txt")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 400
    assert b"Invalid file type" in res.data


def test_partials_analyze_accepts_json(client):
    data = {"file": (io.BytesIO(b"{\"ok\": true}"), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200
    assert b'id="results"' in res.data

    

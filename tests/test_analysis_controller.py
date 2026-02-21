import io
import json


def test_api_analyze_missing_file_returns_400(client):
    res = client.post("/api/analyze", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["error"] == "Missing file"


def test_api_analyze_with_file_returns_501_stub(client):
    payload = {"name": "Board", "cards": [], "lists": [], "members": []}
    data = {"file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "board.json")}
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 501
    body = res.get_json()
    assert body["status"] == "not_implemented"
    assert body["received"]["filename"] == "board.json"


def test_upload_alias_routes_to_partials_analyze(client):
    payload = {"name": "Alias Board", "cards": [], "lists": [], "members": []}
    data = {"file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "board.json")}
    res = client.post("/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert b"Overall Quality Score" in res.data

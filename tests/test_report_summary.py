import io
import json


def test_results_shows_counts_and_generated_at(client):
    payload = {
        "name": "Demo Board",
        "cards": [{"name": "Card A"}, {"name": "Card B"}],
        "lists": [{"name": "List 1"}, {"name": "List 2"}, {"name": "List 3"}],
        "members": [
            {"fullName": "Member 1"},
            {"fullName": "Member 2"},
            {"fullName": "Member 3"},
            {"fullName": "Member 4"},
        ],
    }
    data = {"file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "board.json")}
    res = client.post("/partials/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert b"Cards" in res.data
    assert b"Cards:</strong> 2" in res.data
    assert b"Lists" in res.data
    assert b"Lists:</strong> 3" in res.data
    assert b"Members" in res.data
    assert b"Members:</strong> 4" in res.data
    assert b"Created" in res.data
    assert b"data-iso=" in res.data

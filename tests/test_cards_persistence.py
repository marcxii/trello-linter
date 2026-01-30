import io
import json
import sqlite3


def test_analyze_persists_cards(app, client):
    payload = {
        "name": "Demo Board",
        "cards": [
            {"name": "Card A", "due": "2026-01-20T12:00:00.000Z"},
            {"name": "Card B", "due": None},
        ],
        "members": [],
    }

    data = {"file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "board.json")}
    res = client.post("/partials/analyze", data=data)
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    rows = conn.execute("SELECT card_name, due FROM cards ORDER BY id").fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0][0] == "Card A"
    assert rows[1][0] == "Card B"

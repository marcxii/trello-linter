import io
import json
import sqlite3


def create_run_from_payload(client, app, payload):
    data = {
        "file": (
            io.BytesIO(json.dumps(payload).encode("utf-8")),
            "board.json",
            "application/json",
        )
    }
    res = client.post("/partials/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200

    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    return row[0]

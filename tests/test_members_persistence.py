import sqlite3

from src.database.db_functions import save_members, get_members_for_run


def test_save_members_skips_missing_ids(app):
    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    conn.row_factory = sqlite3.Row

    save_members(
        conn=conn,
        run_id=1,
        members=[
            {"fullName": "No Id"},
            {"id": None, "fullName": "Also No Id"},
        ],
    )

    rows = conn.execute("SELECT COUNT(*) FROM members").fetchone()
    conn.close()

    assert rows[0] == 0


def test_get_members_for_run_maps_display_name(app):
    conn = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    conn.row_factory = sqlite3.Row

    save_members(
        conn=conn,
        run_id=1,
        members=[
            {"id": "m1", "fullName": "Full Name", "username": "full"},
            {"id": "m2", "username": "useronly"},
            {"id": "m3"},
        ],
    )

    mapping = get_members_for_run(conn, run_id=1)
    conn.close()

    assert mapping["m1"] == "Full Name"
    assert mapping["m2"] == "useronly"
    assert mapping["m3"] == "m3"

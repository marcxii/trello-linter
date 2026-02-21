from src.database.db_functions import (
    cleanup_old_runs,
    get_findings_by_category,
    get_recent_runs,
    save_findings,
    save_run,
)
from src.database.sqlite import get_db


def _board(name):
    return {"board": {"id": "b1", "name": name, "desc": ""}, "cards": [], "lists": [], "members": []}


def _scores():
    return {"overall_score": 90, "total_findings": 0}


def test_get_recent_runs_scoped_by_session(app):
    with app.app_context():
        db = get_db()
        save_run(db, "s1", _board("Board 1"), _scores(), report_json={"board": {"name": "Board 1"}})
        save_run(db, "s2", _board("Board 2"), _scores(), report_json={"board": {"name": "Board 2"}})

        s1_runs = get_recent_runs(db, session_id="s1", limit=10)
        all_runs = get_recent_runs(db, session_id=None, limit=10)

        assert len(s1_runs) == 1
        assert s1_runs[0]["session_id"] == "s1"
        assert len(all_runs) == 2


def test_get_findings_by_category_groups_rows(app):
    with app.app_context():
        db = get_db()
        run_id = save_run(db, "s1", _board("Board"), _scores(), report_json={"board": {"name": "Board"}})
        save_findings(
            db,
            run_id,
            [
                {
                    "card_id": "c1",
                    "card_name": "Card 1",
                    "rule_name": "Card Ownership",
                    "category": "assignment",
                    "severity": "major",
                    "description": "Missing owner",
                    "suggestion": "Assign member",
                },
                {
                    "card_id": "c2",
                    "card_name": "Card 2",
                    "rule_name": "Card Due Date",
                    "category": "assignment",
                    "severity": "critical",
                    "description": "Missing due",
                    "suggestion": "Set due date",
                },
            ],
        )

        grouped = get_findings_by_category(db, run_id)
        assert "assignment" in grouped
        assert len(grouped["assignment"]) == 2


def test_cleanup_old_runs_deletes_expired(app):
    with app.app_context():
        db = get_db()
        run_id = save_run(db, "s1", _board("Old Board"), _scores(), report_json={"board": {"name": "Old Board"}})
        db.execute("UPDATE runs SET created_at = ? WHERE id = ?", ("2000-01-01T00:00:00+00:00", run_id))
        db.commit()

        deleted = cleanup_old_runs(db, ttl_seconds=1)
        assert deleted >= 1

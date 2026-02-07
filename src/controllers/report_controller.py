

"""Report controller.

This controller will eventually:
- Load a persisted LintRun by run_id
- Render the dashboard view (screen + print-friendly)

For Commit 1, keep this as a simple placeholder so routing and MVC structure can
be reviewed without requiring Postgres or the analysis pipeline.
"""

from __future__ import annotations

import json

from flask import Blueprint, render_template, request

from src.database.sqlite import get_db
from src.utils.session import get_or_set_session_id

report_bp = Blueprint("report", __name__)


@report_bp.get("/report/<run_id>")
def report(run_id: str):
    """Render a report dashboard page for a given run_id.

    Stub behavior:
    - Renders the existing `report_template.html` with placeholder data.
    - Supports a lightweight print mode via query param `?print=1`.

    NOTE: Do not add database reads in this commit.
    """

    is_print = request.args.get("print") in {"1", "true", "yes"}

    session_id = get_or_set_session_id()
    db = get_db()
    row = db.execute(
        """
        SELECT id, session_id, created_at, board_ref, report_json
        FROM runs
        WHERE id = ? AND session_id = ?
        """,
        (run_id, session_id),
    ).fetchone()

    if row is None:
        return "Report not found for this session.", 404

    run = {
        "id": row["id"],
        "created_at": row["created_at"],
        "board_ref": row["board_ref"] or "(unknown)",
        "source_type": "upload",
    }

    report_data = json.loads(row["report_json"] or "{}")

    return render_template(
        "report_template.html",
        run=run,
        report=report_data,
        is_print=is_print,
    )


@report_bp.get("/report")
def report_latest_placeholder():
    """Placeholder route.

    In later commits, this may redirect to the most recent run for the current
    session/user. For now, it provides a friendly response.
    """
    return (
        "No report selected. Run an analysis first, then open /report/<run_id>.",
        400,
    )

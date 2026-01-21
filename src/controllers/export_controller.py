"""Export controller.

This controller will eventually generate CSV exports backed by a persisted LintRun.
For Commit 1, it provides placeholder endpoints so routes and UI wiring can be
built and reviewed without depending on Postgres or the analysis pipeline.
"""

from __future__ import annotations

from flask import Blueprint, Response, request

export_bp = Blueprint("export", __name__)


def _csv_stub(filename: str, comment: str) -> Response:
    """Return a minimal CSV file response with a single comment row."""

    csv_body = f"# {comment}\n"
    resp = Response(csv_body, mimetype="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return resp


@export_bp.get("/export/findings.csv")
def export_findings_csv():
    """Download findings CSV for a given run.

    Query params:
      - run_id: identifier of the lint run

    Stub behavior:
      - Returns a one-line CSV comment indicating not implemented.
    """

    run_id = request.args.get("run_id", "")
    filename = "findings.csv" if not run_id else f"findings_{run_id}.csv"
    return _csv_stub(filename, "CSV export not implemented yet. Wire to persisted LintRun by run_id.")


@export_bp.get("/export/affected_cards.csv")
def export_affected_cards_csv():
    """Download affected-cards CSV for a given run.

    Query params:
      - run_id: identifier of the lint run

    Stub behavior:
      - Returns a one-line CSV comment indicating not implemented.
    """

    run_id = request.args.get("run_id", "")
    filename = "affected_cards.csv" if not run_id else f"affected_cards_{run_id}.csv"
    return _csv_stub(filename, "CSV export not implemented yet. Wire to persisted LintRun by run_id.")

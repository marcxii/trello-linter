

"""Report controller.

This controller will eventually:
- Load a persisted LintRun by run_id
- Render the dashboard view (screen + print-friendly)

For Commit 1, keep this as a simple placeholder so routing and MVC structure can
be reviewed without requiring Postgres or the analysis pipeline.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request

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

    # Minimal placeholder structure expected by the template.
    # Replace with real persisted report JSON later.
    report_data = {
        "run_id": run_id,
        "overall_score": "—",
        "category_scores": {},
        "metrics": {},
        "findings": [],
        "generated_at": "(not yet generated)",
    }

    return render_template(
        "report_template.html",
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
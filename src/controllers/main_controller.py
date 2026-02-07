"""Main (home) controller.

This module holds routes that are not specific to analysis/report/export workflows.
Keep this controller thin: it should only render views or return simple health info.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request, url_for

# Blueprint name: "main"; import name: __name__
main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    """Landing page.

    Shows the entry UI where a user can provide a board snapshot (JSON upload or API
    connection details, depending on what is enabled).
    """
    run_id = request.args.get("run_id", type=int)
    initial_partial_url = (
        url_for("partials.results_partial", run_id=run_id)
        if run_id
        else url_for("partials.upload_partial")
    )
    return render_template("index.html", initial_partial_url=initial_partial_url)


@main_bp.get("/health")
def health():
    """Simple health check endpoint for hosting/monitoring."""
    return {"status": "ok"}, 200

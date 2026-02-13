"""Main (home) controller for non-report routes.

Responsibilities:
- Serve the landing page and initial HTMX entrypoint.
- Provide a simple health check endpoint.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from flask import Blueprint, current_app, render_template, request, url_for

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
    faqs = []
    faqs_override = current_app.config.get("HELP_FAQS_PATH") or os.getenv("HELP_FAQS_PATH")
    faqs_path = Path(faqs_override) if faqs_override else Path(__file__).parent.parent.parent / "config" / "help_faqs.yaml"
    if faqs_path.exists():
        try:
            with faqs_path.open("r", encoding="utf-8") as handle:
                faqs = yaml.safe_load(handle) or []
        except yaml.YAMLError:
            faqs = []

    return render_template("index.html", initial_partial_url=initial_partial_url, faqs=faqs)


@main_bp.get("/health")
def health():
    """Simple health check endpoint for hosting/monitoring."""
    return {"status": "ok"}, 200

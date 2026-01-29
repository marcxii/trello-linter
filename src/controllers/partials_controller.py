"""HTMX partials controller.

Purpose
-------
Owns the HTML fragment endpoints used by the single-page shell.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request

partials_bp = Blueprint("partials", __name__)


# -------------------------
# HTMX partial endpoints
# -------------------------
@partials_bp.get("/partials/upload")
def upload_partial():
    """Return the upload UI fragment for the single-page shell."""
    return render_template("partials/upload.html")


@partials_bp.post("/partials/analyze")
def analyze_partial():
    """Accept an uploaded Trello JSON export and return a results fragment.

    This is a scaffold-only endpoint:
    - Validates that a file was provided (no JSON parsing yet)
    - Returns placeholder metrics in `partials/results.html`

    Later commits will:
    - Parse JSON
    - Run rules/scoring
    - Save a run (optional) and drive exports from persisted results
    """
    uploaded = request.files.get("file") or request.files.get("trello_file")
    if uploaded is None:
        return render_template(
            "partials/error.html",
            message="Missing file. Please upload a Trello JSON export.",
        ), 400

    filename = uploaded.filename or "(unnamed)"
    name_ok = filename.lower().endswith(".json")
    type_ok = uploaded.mimetype in {"application/json", "text/json", ""} or uploaded.mimetype is None
    if not name_ok or not type_ok:
        return render_template(
            "partials/error.html",
            message="Invalid file type. Please upload a Trello JSON export.",
        ), 400

    # Placeholder output for scaffold validation (no real linting yet)
    # `run_id` is a stub for now; if/when you add persistence, replace with real id.
    placeholder = {
        "run_id": 1,
        "overall_score": 100,
        "category_scores": {
            "Hygiene": 100,
            "Structure": 100,
            "Done Evidence": 100,
            "Accountability": 100,
        },
        "total_findings": 0,
        "critical": 0,
        "major": 0,
        "minor": 0,
        "filename": filename,
    }

    return render_template("partials/results.html", **placeholder)

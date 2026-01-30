"""HTMX partials controller.

Purpose
-------
Owns the HTML fragment endpoints used by the single-page shell.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, render_template, request

from src.database.sqlite import cleanup_runs, get_db
from src.parser.trello_parser import parse_board_summary, parse_cards
from src.utils.session import get_or_set_session_id

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
        )

    filename = uploaded.filename or "(unnamed)"
    name_ok = filename.lower().endswith(".json")
    type_ok = uploaded.mimetype in {
        "application/json",
        "text/json",
        "application/octet-stream",
        "",
    } or uploaded.mimetype is None
    if not name_ok or not type_ok:
        return render_template(
            "partials/error.html",
            message="Invalid file type. Please upload a Trello JSON export.",
        )

    try:
        payload = json.load(uploaded.stream)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return render_template(
            "partials/error.html",
            message="Invalid JSON file. Please export a valid Trello JSON file.",
        )
    finally:
        uploaded.stream.seek(0)

    summary = parse_board_summary(payload)
    cards = parse_cards(payload)

    # Placeholder output for scaffold validation (no real linting yet)
    # `run_id` is a stub for now; if/when you add persistence, replace with real id.
    placeholder = {
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
        "board_name": summary["board_name"],
        "cards_count": summary["cards_count"],
        "members_count": summary["members_count"],
    }

    session_id = get_or_set_session_id()
    cleanup_runs(int(current_app.config.get("RUN_TTL_SECONDS", 0)))
    created_at = datetime.now(timezone.utc).isoformat()
    report_data = {
        "board": {
            "name": summary["board_name"],
            "cards_count": summary["cards_count"],
            "members_count": summary["members_count"],
        },
        "scores": {
            "overall_score": placeholder["overall_score"],
            "total_findings": placeholder["total_findings"],
            "critical_findings": placeholder["critical"],
            "major_findings": placeholder["major"],
            "category_scores": placeholder["category_scores"],
        },
        "summary": {
            "note": "Placeholder report data. Connect the pipeline to populate this.",
        },
        "findings": [],
    }

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO runs (session_id, created_at, board_ref, report_json)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, created_at, summary["board_name"] or filename, json.dumps(report_data)),
    )
    run_id = cur.lastrowid

    if cards:
        db.executemany(
            """
            INSERT INTO cards (run_id, card_name, due)
            VALUES (?, ?, ?)
            """,
            [(run_id, card["name"], card["due"]) for card in cards],
        )

    db.commit()
    placeholder["run_id"] = run_id

    return render_template("partials/results.html", **placeholder)


@partials_bp.post("/reset")
def reset_session_runs():
    """Clear session-scoped runs and return the upload partial."""
    session_id = get_or_set_session_id()
    db = get_db()
    db.execute("DELETE FROM runs WHERE session_id = ?", (session_id,))
    db.commit()
    return render_template("partials/upload.html")

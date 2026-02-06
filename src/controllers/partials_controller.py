"""HTMX partials controller.

Purpose
-------
Owns the HTML fragment endpoints used by the single-page shell.

Updated to use:
- New database functions from db_functions.py
- Full board parsing with parse_full_board()
- Proper data persistence with separate findings table
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, render_template, request

from src.database.sqlite import get_db
from src.database.db_functions import (
    save_run,
    save_cards,
    save_members,
    save_findings,
    cleanup_old_runs,
    delete_session_runs,
    get_run_summary,
    get_cards_for_run,
    get_members_for_run,
)
from src.linter.rule_engine import count_overdue_cards
from src.linter.rules.due_date_rule import evaluate_due_date
from src.linter.scoring_engine import compute_overall_score
from src.parser.trello_parser import (
    parse_board_summary,
    parse_cards,
    parse_full_board,
    TrelloParseError,
)
from src.utils.session import get_or_set_session_id

partials_bp = Blueprint("partials", __name__)


def _get_overdue_cards(run_id: int) -> list[dict]:
    """Return overdue cards for a run with metadata."""
    db = get_db()
    cards = get_cards_for_run(db, run_id)
    member_map = get_members_for_run(db, run_id)
    overdue_cards = []
    for card in cards:
        if card.get("is_closed"):
            continue
        result = evaluate_due_date(card.get("due"))
        if result["overdue"]:
            member_names = [
                member_map.get(member_id, member_id) for member_id in (card.get("members") or [])
            ]
            overdue_cards.append(
                {
                    "name": card.get("card_name") or "(untitled card)",
                    "days_past_due": result["days_past_due"],
                    "list_name": card.get("list_name") or "",
                    "members": member_names,
                    "due": card.get("due"),
                }
            )
    overdue_cards.sort(key=lambda item: item["days_past_due"], reverse=True)
    return overdue_cards


# -------------------------
# HTMX partial endpoints
# -------------------------
@partials_bp.get("/partials/upload")
def upload_partial():
    """Return the upload UI fragment for the single-page shell."""
    return render_template("partials/upload.html")

@partials_bp.get("/partials/results")
def results_partial():
    """Return results fragment for a given run_id (fallbacks to placeholder)."""
    run_id = request.args.get("run_id", type=int)
    if run_id:
        session_id = get_or_set_session_id()
        db = get_db()
        row = db.execute(
            "SELECT report_json FROM runs WHERE id = ? AND session_id = ?",
            (run_id, session_id),
        ).fetchone()
        if row:
            report = json.loads(row["report_json"])
            board = report.get("board", {})
            scores = report.get("scores", {})
            summary = report.get("summary", {})
            overdue_cards = _get_overdue_cards(run_id)
            return render_template(
                "partials/results.html",
                overall_score=scores.get("overall_score", 0),
                total_findings=scores.get("total_findings", 0),
                critical=scores.get("critical_findings", 0),
                major=scores.get("major_findings", 0),
                minor=scores.get("minor_findings", 0),
                filename=summary.get("filename", "(unknown)"),
                board_name=board.get("name", "(unknown)"),
                cards_count=board.get("cards_count", 0),
                lists_count=board.get("lists_count", 0),
                members_count=board.get("members_count", 0),
                generated_at=report.get("generated_at", datetime.now(timezone.utc).isoformat()),
                run_id=run_id,
                overdue_cards=overdue_cards,
            )

    return render_template(
        "partials/upload.html",
        message="Report not found. Please analyze a board.",
    )


@partials_bp.get("/partials/report")
def report_overlay_partial():
    """Return printable report as an overlay partial for a given run_id."""
    run_id = request.args.get("run_id", type=int)
    if not run_id:
        return render_template(
            "partials/error.html",
            message="Missing run ID. Please open a report from results.",
        )

    session_id = get_or_set_session_id()
    db = get_db()
    row = db.execute(
        """
        SELECT id, created_at, board_ref, report_json
        FROM runs
        WHERE id = ? AND session_id = ?
        """,
        (run_id, session_id),
    ).fetchone()

    if row is None:
        return render_template(
            "partials/error.html",
            message="Report not found for this session.",
        )

    run = {
        "id": row["id"],
        "created_at": row["created_at"],
        "board_ref": row["board_ref"] or "(unknown)",
        "source_type": "upload",
    }
    report_data = json.loads(row["report_json"] or "{}")
    board = report_data.get("board", {})
    scores = report_data.get("scores", {})
    summary = report_data.get("summary", {})
    overdue_cards = _get_overdue_cards(run_id)
    return render_template(
        "partials/report_overlay.html",
        run=run,
        report=report_data,
        overall_score=scores.get("overall_score", 0),
        total_findings=scores.get("total_findings", 0),
        critical=scores.get("critical_findings", 0),
        major=scores.get("major_findings", 0),
        minor=scores.get("minor_findings", 0),
        filename=summary.get("filename", "(unknown)"),
        board_name=board.get("name", "(unknown)"),
        cards_count=board.get("cards_count", 0),
        lists_count=board.get("lists_count", 0),
        members_count=board.get("members_count", 0),
        generated_at=report_data.get("generated_at", datetime.now(timezone.utc).isoformat()),
        overdue_cards=overdue_cards,
    )


@partials_bp.get("/partials/report-settings")
def report_settings_partial():
    """Return report settings overlay."""
    return render_template("partials/report_settings.html")


@partials_bp.post("/partials/analyze")
def analyze_partial():
    """Accept an uploaded Trello JSON export and return a results fragment.

    Flow:
    1. Validate uploaded file
    2. Parse Trello JSON (board, lists, cards, members, checklists)
    3. Run linting rules (TODO: wire up full rule engine)
    4. Calculate scores
    5. Save to database (runs, cards, findings)
    6. Return results HTML fragment
    """
    # -------------------------
    # Step 1: Validate file
    # -------------------------
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

    # -------------------------
    # Step 2: Parse JSON
    # -------------------------
    try:
        payload = json.load(uploaded.stream)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return render_template(
            "partials/error.html",
            message="Invalid JSON file. Please export a valid Trello JSON file.",
        )
    finally:
        uploaded.stream.seek(0)

    # Validate it's a Trello export
    try:
        # Quick summary for immediate counts
        summary = parse_board_summary(payload)
        lists_count = len(payload.get("lists") or [])
        
        # Full parse for rule engine (when we wire it up)
        board_data = parse_full_board(payload)
        
    except TrelloParseError as e:
        return render_template(
            "partials/error.html",
            message=f"Invalid Trello export: {str(e)}",
        )

    # -------------------------
    # Step 3: Run Analysis
    # -------------------------
    session_id = get_or_set_session_id()
    db = get_db()
    
    # Cleanup old runs
    ttl_seconds = int(current_app.config.get("RUN_TTL_SECONDS", 21600))
    cleanup_old_runs(db, ttl_seconds)

    # TODO: Replace placeholder with real rule engine
    # For now, using placeholder scores
    # When ready: 
    #   from src.linter.rule_engine import RuleEngine
    #   from src.scoring.scorer import Scorer
    #   
    #   rule_engine = RuleEngine()
    #   findings = rule_engine.run_all_rules(board_data)
    #   
    #   scorer = Scorer()
    #   scores = scorer.calculate_score(findings)
    
    # Placeholder findings (empty for now)
    findings = []
    
    # Placeholder scores
    scores = {
        "overall_score": 100,
        "category_scores": {
            "Story Quality": 100,
            "Acceptance Criteria": 100,
            "Sprint Management": 100,
            "Ownership": 100,
            "Done Evidence": 100,
        },
        "total_findings": 0,
        "critical_findings": 0,
        "major_findings": 0,
        "minor_findings": 0,
    }

    # Calculate overdue count (existing logic)
    cards = parse_cards(payload)
    overdue_count = 0
    if cards:
        # Temporarily save cards to calculate overdue
        # (This is a workaround until we refactor count_overdue_cards)
        temp_cur = db.execute(
            "INSERT INTO runs (session_id, created_at, board_ref) VALUES (?, ?, ?)",
            (session_id, datetime.now(timezone.utc).isoformat(), "temp")
        )
        temp_run_id = temp_cur.lastrowid
        
        db.executemany(
            "INSERT INTO cards (run_id, card_name, due) VALUES (?, ?, ?)",
            [(temp_run_id, card["name"], card["due"]) for card in cards],
        )
        db.commit()
        
        overdue_count = count_overdue_cards(temp_run_id)
        
        # Clean up temp run
        db.execute("DELETE FROM runs WHERE id = ?", (temp_run_id,))
        db.commit()

    # Adjust overall score based on overdue cards
    overall_score = compute_overall_score(overdue_count)
    scores["overall_score"] = overall_score

    # -------------------------
    # Step 4: Build Report JSON
    # -------------------------
    report_data = {
        "board": {
            "name": summary["board_name"],
            "cards_count": summary["cards_count"],
            "lists_count": lists_count,
            "members_count": summary["members_count"],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scores": {
            "overall_score": scores["overall_score"],
            "total_findings": scores["total_findings"],
            "critical_findings": scores["critical_findings"],
            "major_findings": scores["major_findings"],
            "minor_findings": scores["minor_findings"],
            "category_scores": scores["category_scores"],
            "overdue_count": overdue_count,
        },
        "summary": {
            "note": "Analysis complete. Connect rule engine to populate findings.",
        },
        "findings": findings,  # Will be populated when rule engine is wired
    }

    # -------------------------
    # Step 5: Save to Database
    # -------------------------
    
    # Save the run
    run_id = save_run(
        conn=db,
        session_id=session_id,
        board_data=board_data,
        scores=scores,
        report_json=report_data,
    )

    # Save cards with list mapping
    list_map = {lst['id']: lst['name'] for lst in board_data.get('lists', [])}
    save_cards(
        conn=db,
        run_id=run_id,
        cards=board_data.get('cards', []),
        list_map=list_map,
    )

    # Save members for name lookups
    save_members(
        conn=db,
        run_id=run_id,
        members=board_data.get('members', []),
    )

    # Save findings (when rule engine is wired, findings will be populated)
    if findings:
        save_findings(conn=db, run_id=run_id, findings=findings)

    overdue_cards = _get_overdue_cards(run_id)

    # -------------------------
    # Step 6: Return Results
    # -------------------------
    
    # Build template context
    context = {
        "run_id": run_id,
        "overall_score": scores["overall_score"],
        "category_scores": scores["category_scores"],
        "total_findings": scores["total_findings"],
        "critical": scores["critical_findings"],
        "major": scores["major_findings"],
        "minor": scores["minor_findings"],
        "filename": filename,
        "board_name": summary["board_name"],
        "cards_count": summary["cards_count"],
        "lists_count": lists_count,
        "members_count": summary["members_count"],
        "generated_at": report_data["generated_at"],
        "overdue_cards": overdue_cards,
    }

    return render_template("partials/results.html", **context)


@partials_bp.post("/reset")
def reset_session_runs():
    """Clear session-scoped runs and return the upload partial."""
    session_id = get_or_set_session_id()
    db = get_db()
    
    # Use new delete function (cascades to cards, findings, etc.)
    delete_session_runs(db, session_id)
    
    return render_template("partials/upload.html")


@partials_bp.get("/partials/card")
def card_partial():
    """Return a placeholder single-card view fragment."""
    run_id = request.args.get("run_id", type=int) or 0
    return render_template("partials/card.html", run_id=run_id)

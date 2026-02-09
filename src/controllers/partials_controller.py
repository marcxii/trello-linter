"""HTMX partials controller.

Purpose
-------
Owns the HTML fragment endpoints used by the single-page shell.

Updated to use:
- Full rule engine with 14 individual rules
- Individual rule-based scoring
- New database functions from db_functions.py
- Full board parsing with parse_full_board()
- Proper data persistence with separate findings table
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, render_template, request

from src.database.db_functions import (
    cleanup_old_runs,
    delete_session_runs,
    get_card_for_run,
    get_cards_for_run,
    get_findings_for_card,
    get_members_for_run,
    get_run_summary,
    save_cards,
    save_findings,
    save_members,
    save_run,
)
from src.database.sqlite import get_db
from src.linter.rule_engine import RuleEngine, count_overdue_cards
from src.linter.scoring_engine import calculate_overall_score, get_grade_from_score
from src.linter.rules.due_date_rule import evaluate_due_date
from src.linter.scoring_engine import compute_overall_score
from src.parser.trello_parser import (
    TrelloParseError,
    parse_board_summary,
    parse_cards,
    parse_full_board,
)
from src.utils.session import get_or_set_session_id


def _format_due_display(due_value: str | None) -> str | None:
    """Format due date for display as YYYY-MM-DD HH:MM:SS AM/PM."""
    if not due_value or not isinstance(due_value, str):
        return None

    value = due_value.strip()
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    return dt.strftime("%Y-%m-%d %I:%M:%S %p")


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
                    "card_id": card.get("card_id"),
                    "days_past_due": result["days_past_due"],
                    "list_name": card.get("list_name") or "",
                    "members": member_names,
                    "due": card.get("due"),
                }
            )
    overdue_cards.sort(key=lambda item: item["days_past_due"], reverse=True)
    return overdue_cards


def _filter_cards_by_members(cards: list[dict], selected_members: list[str]) -> list[dict]:
    """Filter cards by selected member names (including Unassigned)."""
    if not selected_members:
        return []

    selected_set = set(selected_members)
    include_unassigned = "Unassigned" in selected_set
    selected_set.discard("Unassigned")

    filtered = []
    for card in cards:
        members = card.get("members") or []
        if not members:
            if include_unassigned:
                filtered.append(card)
            continue
        if selected_set and any(member in selected_set for member in members):
            filtered.append(card)

    return filtered


def _average_scores(rule_scores: dict, rule_ids: list) -> float:
    """Calculate average score for a group of rules.
    
    Args:
        rule_scores: Dictionary of all rule scores
        rule_ids: List of rule IDs to average
        
    Returns:
        Average score (0-100)
    """
    scores = []
    for rule_id in rule_ids:
        if rule_id in rule_scores and not rule_scores[rule_id].get("skipped", False):
            scores.append(rule_scores[rule_id]["score"])
    
    if not scores:
        return 100.0  # No applicable rules
    
    return round(sum(scores) / len(scores), 2)


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
            rule_results = report.get("rule_results", [])
            overdue_cards = _get_overdue_cards(run_id)
            member_names = sorted(set(get_members_for_run(db, run_id).values()))
            member_names.append("Unassigned")
            selected_members = request.args.getlist("members")
            expanded_rule_ids = request.args.getlist("expanded")
            if selected_members:
                if selected_members == ["__none__"]:
                    selected_members = []
                else:
                    valid = set(member_names)
                    selected_members = [m for m in selected_members if m in valid]
            else:
                selected_members = member_names

            overdue_cards = _filter_cards_by_members(overdue_cards, selected_members)
            return render_template(
                "partials/results.html",
                overall_score=scores.get("overall_score", 0),
                grade=scores.get("grade", "F"),
                grade_description=scores.get("grade_description", "Unknown"),
                total_findings=scores.get("total_findings", 0),
                rules_passed=scores.get("rules_passed", 0),
                rules_failed=scores.get("rules_failed", 0),
                critical=scores.get("critical_findings", 0),
                major=scores.get("major_findings", 0),
                minor=scores.get("minor_findings", 0),
                category_scores=scores.get("category_scores", {}),
                filename=summary.get("filename", "(unknown)"),
                board_name=board.get("name", "(unknown)"),
                cards_count=board.get("cards_count", 0),
                lists_count=board.get("lists_count", 0),
                members_count=board.get("members_count", 0),
                generated_at=report.get("generated_at", datetime.now(timezone.utc).isoformat()),
                run_id=run_id,
                overdue_cards=overdue_cards,
                member_names=member_names,
                selected_members=selected_members,
                expanded_rule_ids=expanded_rule_ids,
                rule_results=rule_results,
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
    member_names = sorted(set(get_members_for_run(db, run_id).values()))
    member_names.append("Unassigned")
    selected_members = member_names
    overdue_cards = _filter_cards_by_members(overdue_cards, selected_members)
    selected_members = request.args.getlist("members")
    expanded_rule_ids = request.args.getlist("expanded")
    if selected_members:
        if selected_members == ["__none__"]:
            selected_members = []
        else:
            valid = set(member_names)
            selected_members = [m for m in selected_members if m in valid]
    else:
        selected_members = member_names
    overdue_cards = _filter_cards_by_members(overdue_cards, selected_members)
    return render_template(
        "partials/report_overlay.html",
        run=run,
        report=report_data,
        overall_score=scores.get("overall_score", 0),
        grade=scores.get("grade", "F"),
        grade_description=scores.get("grade_description", "Unknown"),
        total_findings=scores.get("total_findings", 0),
        rules_passed=scores.get("rules_passed", 0),
        rules_failed=scores.get("rules_failed", 0),
        critical=scores.get("critical_findings", 0),
        major=scores.get("major_findings", 0),
        minor=scores.get("minor_findings", 0),
        category_scores=scores.get("category_scores", {}),
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
    3. Run all 14 linting rules via RuleEngine
    4. Calculate individual rule-based scores
    5. Save to database (runs, cards, members, findings)
    6. Return results HTML fragment
    """
    # TODO: If this moves beyond scaffolding, split into helpers
    # (parse, scoring, persistence, and response building).
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
        
        # Full parse for rule engine
        board_data = parse_full_board(payload)
        
    except TrelloParseError as e:
        return render_template(
            "partials/error.html",
            message=f"Invalid Trello export: {str(e)}",
        )

    # -------------------------
    # Step 3: Run Rule Engine
    # -------------------------
    session_id = get_or_set_session_id()
    db = get_db()
    
    # Cleanup old runs
    ttl_seconds = int(current_app.config.get("RUN_TTL_SECONDS", 21600))
    cleanup_old_runs(db, ttl_seconds)

    # Initialize rule engine and run all rules
    try:
        engine = RuleEngine()
        rule_results = engine.run_all_rules(board_data)
    except Exception as e:
        return render_template(
            "partials/error.html",
            message=f"Rule engine error: {str(e)}. Please check your config/rules_config.yaml file.",
        )

    # -------------------------
    # Step 4: Calculate Scores
    # -------------------------
    try:
        weights = engine.get_rule_weights()
        scoring_result = calculate_overall_score(rule_results, weights)
        grade_info = get_grade_from_score(scoring_result["overall_score"])
    except Exception as e:
        return render_template(
            "partials/error.html",
            message=f"Scoring error: {str(e)}",
        )

    # -------------------------
    # Step 5: Build Report JSON
    # -------------------------
    
    # Group rules into display categories for UI
    category_scores = {
        "Assignment & Ownership": _average_scores(scoring_result["rule_scores"], 
            ["card_ownership", "card_due_date", "unscheduled_work"]),
        "Quality & Estimation": _average_scores(scoring_result["rule_scores"],
            ["card_descriptiveness", "story_point_estimation", "description_canonicalization"]),
        "Capacity Management": _average_scores(scoring_result["rule_scores"],
            ["progress_threshold", "individual_overload", "weekly_workload", "near_term_overcommitment"]),
        "Due Dates & Flow": _average_scores(scoring_result["rule_scores"],
            ["past_due_violation", "progress_monitoring", "flow_progress_signal", "card_completion"]),
    }
    
    report_data = {
        "board": {
            "name": summary["board_name"],
            "cards_count": summary["cards_count"],
            "lists_count": lists_count,
            "members_count": summary["members_count"],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scores": {
            "overall_score": scoring_result["overall_score"],
            "grade": grade_info["grade"],
            "grade_description": grade_info["description"],
            "total_findings": scoring_result["total_failures"],
            "rules_passed": scoring_result["rules_passed"],
            "rules_failed": scoring_result["rules_failed"],
            "critical_findings": 0,  # Not used in individual rule model
            "major_findings": 0,
            "minor_findings": 0,
            "category_scores": category_scores,
        },
        "summary": {
            "filename": filename,
            "note": "Analysis complete using 14-rule engine",
        },
        "rule_results": rule_results,  # Full rule results for detailed view
    }

    # -------------------------
    # Step 6: Save to Database
    # -------------------------
    
    # Prepare scores for database
    db_scores = {
        "overall_score": scoring_result["overall_score"],
        "category_scores": category_scores,
        "total_findings": scoring_result["total_failures"],
        "critical_findings": 0,
        "major_findings": 0,
        "minor_findings": 0,
    }
    
    # Save the run
    run_id = save_run(
        conn=db,
        session_id=session_id,
        board_data=board_data,
        scores=db_scores,
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

    # Convert rule results to findings format for database
    findings = []
    for rule_result in rule_results:
        for failure in rule_result.get("failures", []):
            findings.append({
                "card_id": failure.get("card_id"),
                "card_name": failure.get("card_name", failure.get("member_name", "Board-level")),
                "rule_name": rule_result["rule_name"],
                "category": "Individual Rule",
                "severity": "major",  # Default severity for individual rules
                "description": failure.get("reason", "Rule violation"),
                "suggestion": f"See rule: {rule_result['rule_name']}",
            })
    
    # Save findings
    if findings:
        save_findings(conn=db, run_id=run_id, findings=findings)

    # Get overdue cards and members for display
    overdue_cards = _get_overdue_cards(run_id)
    member_names = sorted(set(get_members_for_run(db, run_id).values()))
    member_names.append("Unassigned")
    selected_members = request.args.getlist("members")
    if selected_members:
        if selected_members == ["__none__"]:
            selected_members = []
        else:
            valid = set(member_names)
            selected_members = [m for m in selected_members if m in valid]
    else:
        selected_members = member_names
    expanded_rule_ids = []
    overdue_cards = _filter_cards_by_members(overdue_cards, selected_members)

    # -------------------------
    # Step 7: Return Results
    # -------------------------
    
    # Build template context
    context = {
        "run_id": run_id,
        "overall_score": scoring_result["overall_score"],
        "grade": grade_info["grade"],
        "grade_description": grade_info["description"],
        "category_scores": category_scores,
        "total_findings": scoring_result["total_failures"],
        "rules_passed": scoring_result["rules_passed"],
        "rules_failed": scoring_result["rules_failed"],
        "critical": 0,
        "major": 0,
        "minor": 0,
        "filename": filename,
        "board_name": summary["board_name"],
        "cards_count": summary["cards_count"],
        "lists_count": lists_count,
        "members_count": summary["members_count"],
        "generated_at": report_data["generated_at"],
        "overdue_cards": overdue_cards,
        "member_names": member_names,
        "selected_members": selected_members,
        "expanded_rule_ids": expanded_rule_ids,
        "rule_results": rule_results,
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
    """Return a single-card view fragment."""
    run_id = request.args.get("run_id", type=int)
    card_id = request.args.get("card_id", type=str)
    if not run_id:
        return render_template(
            "partials/error.html",
            message="Missing card details. Please return to the report.",
        )

    session_id = get_or_set_session_id()
    db = get_db()
    run_row = db.execute(
        "SELECT id FROM runs WHERE id = ? AND session_id = ?",
        (run_id, session_id),
    ).fetchone()
    if run_row is None:
        return render_template(
            "partials/error.html",
            message="Report not found for this session.",
        )

    if not card_id:
        return render_template(
            "partials/card.html",
            run_id=run_id,
            card_name="(unknown card)",
            list_name="—",
            members=[],
            card_id="—",
            due_date=None,
            issues=[],
        )

    card = get_card_for_run(db, run_id, card_id)
    if card is None:
        return render_template(
            "partials/error.html",
            message="Card not found for this report.",
        )

    member_map = get_members_for_run(db, run_id)
    member_names = [member_map.get(member_id, member_id) for member_id in (card.get("members") or [])]

    issues = []
    due_result = evaluate_due_date(card.get("due"))
    if due_result["overdue"]:
        days = due_result["days_past_due"]
        due_display = _format_due_display(card.get("due")) or "—"
        issues.append(f"Overdue: Due date: {due_display} | +{days} day{'s' if days != 1 else ''} past due")

    findings = get_findings_for_card(db, run_id, card_id)
    for finding in findings:
        issues.append(finding.get("description") or finding.get("rule_name") or "Finding")

    return render_template(
        "partials/card.html",
        run_id=run_id,
        card_name=card.get("card_name") or "(untitled card)",
        list_name=card.get("list_name") or "—",
        members=member_names,
        card_id=card.get("card_id") or "—",
        due_date=_format_due_display(card.get("due")),
        issues=issues,
    )

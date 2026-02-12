"""HTMX partials controller.

Purpose
-------
Owns the HTML fragment endpoints used by the single-page shell.

Notes
-----
The analyze flow is decomposed into helper functions for upload parsing, rule
execution, scoring, report assembly, persistence, and response context.

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

from flask import Blueprint, current_app, render_template, request, session

from src.database.db_functions import (
    cleanup_old_runs,
    delete_session_runs,
    get_card_for_run,
    get_cards_for_run,
    get_findings_for_card,
    get_members_for_run,
    save_cards,
    save_findings,
    save_members,
    save_run,
)
from src.database.sqlite import get_db
from src.linter.rule_engine import RuleEngine
from src.linter.scoring_engine import calculate_overall_score, get_grade_from_score
from src.parser.trello_parser import TrelloParseError, parse_board_summary, parse_full_board
from src.reports.report_builder import load_report_context
from src.utils.session import get_or_set_session_id


def _format_due_display(due_value: str | None) -> str | None:
    """Format due date for display as Mon D, YYYY HH:MM:SS AM/PM."""
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

    return f"{dt.strftime('%b')} {dt.day}, {dt.year} {dt.strftime('%I:%M:%S %p')}"


partials_bp = Blueprint("partials", __name__)


def _build_overdue_cards(
    rule_results: list[dict],
    card_lookup: dict[str, dict[str, object]],
) -> list[dict]:
    """Return overdue cards derived from rule_results (past_due_violation)."""
    overdue_cards = []
    for rule in rule_results or []:
        if rule.get("rule_id") != "past_due_violation":
            continue
        for failure in rule.get("failures") or []:
            card_id = failure.get("card_id")
            lookup = card_lookup.get(card_id) if card_id else None
            overdue_cards.append(
                {
                    "name": failure.get("card_name")
                    or (lookup.get("card_name") if lookup else None)
                    or "(untitled card)",
                    "card_id": card_id,
                    "days_past_due": failure.get("days_overdue", 0),
                    "list_name": failure.get("list_name")
                    or (lookup.get("list_name") if lookup else ""),
                    "members": (lookup.get("members") if lookup else []) or [],
                    "due": failure.get("due_date") or (lookup.get("due") if lookup else None),
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


def _build_card_maps(
    run_id: int,
    member_map: dict[str, str],
) -> tuple[dict[str, dict[str, object]], dict[str, list[str]]]:
    """Return card_id -> card details and card_id -> member names for a run."""
    db = get_db()
    cards = get_cards_for_run(db, run_id)
    lookup: dict[str, dict[str, object]] = {}
    card_members: dict[str, list[str]] = {}
    for card in cards:
        member_ids = card.get("members") or []
        member_names = [member_map.get(member_id, member_id) for member_id in member_ids]
        card_id = card.get("card_id")
        if card_id:
            lookup[card_id] = {
                "card_name": card.get("card_name"),
                "list_name": card.get("list_name"),
                "members": member_names,
                "due": card.get("due"),
            }
            card_members[card_id] = member_names
    return lookup, card_members


def _parse_selected_members(
    args: dict,
    member_names: list[str],
) -> list[str]:
    """Return validated selected member names from request args."""
    selected_members = args.getlist("members")
    if selected_members:
        if selected_members == ["__none__"]:
            return []
        valid = set(member_names)
        return [m for m in selected_members if m in valid]
    return member_names


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
        selected_members = request.args.getlist("members")
        report_ctx = load_report_context(run_id, session_id, selected_members or None)
        if report_ctx:
            board = report_ctx.get("board", {})
            member_names = report_ctx.get("member_names", [])
            selected_members = report_ctx.get("selected_members", [])
            expanded_rule_ids = request.args.getlist("expanded")
            filter_active = set(selected_members) != set(member_names)
            overrides = _get_rule_settings_overrides()
            rule_results = _filter_rule_results_by_overrides(
                report_ctx.get("rule_results", []), overrides
            )
            base_config = _load_rules_config()
            scoring_result, grade_info = _apply_overrides_to_scores(
                rule_results, base_config, overrides
            )
            return render_template(
                "partials/results.html",
                overall_score=scoring_result.get("overall_score", 0),
                grade_description=grade_info.get("description", "Unknown"),
                board_name=board.get("name", "(unknown)"),
                cards_count=board.get("cards_count", 0),
                lists_count=board.get("lists_count", 0),
                members_count=board.get("members_count", 0),
                generated_at=report_ctx.get("generated_at", datetime.now(timezone.utc).isoformat()),
                run_id=run_id,
                member_names=member_names,
                selected_members=selected_members,
                filter_active=filter_active,
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
    selected_members = request.args.getlist("members")
    report_ctx = load_report_context(run_id, session_id, selected_members or None)
    if report_ctx is None:
        return render_template(
            "partials/error.html",
            message="Report not found for this session.",
        )

    board = report_ctx.get("board", {})
    member_names = report_ctx.get("member_names", [])
    selected_members = report_ctx.get("selected_members", [])
    filter_active = set(selected_members) != set(member_names)
    overrides = _get_rule_settings_overrides()
    rule_results = _filter_rule_results_by_overrides(
        report_ctx.get("rule_results", []), overrides
    )
    base_config = _load_rules_config()
    scoring_result, _ = _apply_overrides_to_scores(rule_results, base_config, overrides)
    report = dict(report_ctx.get("report", {}))
    report["scores"] = {
        **(report.get("scores", {}) or {}),
        "overall_score": scoring_result.get("overall_score", 0),
        "total_findings": scoring_result.get("total_failures", 0),
    }
    return render_template(
        "partials/report_overlay.html",
        report=report,
        board_name=board.get("name", "(unknown)"),
        cards_count=board.get("cards_count", 0),
        lists_count=board.get("lists_count", 0),
        members_count=board.get("members_count", 0),
        generated_at=report_ctx.get("generated_at", datetime.now(timezone.utc).isoformat()),
        rule_results=rule_results,
        filter_active=filter_active,
    )


@partials_bp.get("/partials/report-settings")
def report_settings_partial():
    """Return report settings overlay."""
    config = _load_rules_config()
    settings = _merge_rule_settings(config, _get_rule_settings_overrides())
    run_id = request.args.get("run_id", type=int)
    return render_template(
        "partials/report_settings.html",
        rules=settings["rules"],
        card_descriptiveness=settings["card_descriptiveness"],
        progress_threshold=settings["progress_threshold"],
        progress_monitoring=settings["progress_monitoring"],
        run_id=run_id,
        message=settings.get("message"),
    )


@partials_bp.post("/partials/report-settings")
def report_settings_save():
    """Persist rule settings overrides in the session."""
    config = _load_rules_config()
    overrides = _parse_rule_settings_form(request.form, config)
    session["rule_settings_overrides"] = overrides
    settings = _merge_rule_settings(config, overrides)
    settings["message"] = "Settings saved. These will apply to future analyses."
    run_id = request.form.get("run_id")
    run_id = int(run_id) if run_id and run_id.isdigit() else None
    return render_template(
        "partials/report_settings.html",
        rules=settings["rules"],
        card_descriptiveness=settings["card_descriptiveness"],
        progress_threshold=settings["progress_threshold"],
        progress_monitoring=settings["progress_monitoring"],
        run_id=run_id,
        message=settings.get("message"),
    )


def _parse_upload(uploaded_file):
    """Validate and parse an uploaded Trello JSON export."""
    if uploaded_file is None:
        raise ValueError("Missing file. Please upload a Trello JSON export.")

    name = uploaded_file.filename or "(unnamed)"
    name_ok = name.lower().endswith(".json")
    mimetype = uploaded_file.mimetype
    type_ok = mimetype in {
        "application/json",
        "text/json",
        "application/octet-stream",
        "",
    } or mimetype is None
    if not name_ok or not type_ok:
        raise ValueError("Invalid file type. Please upload a Trello JSON export.")

    try:
        payload = json.load(uploaded_file.stream)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Invalid JSON file. Please export a valid Trello JSON file.")
    finally:
        uploaded_file.stream.seek(0)

    try:
        summary = parse_board_summary(payload)
        lists_count = len(payload.get("lists") or [])
        board_data = parse_full_board(payload)
    except TrelloParseError as exc:
        raise ValueError(f"Invalid Trello export: {str(exc)}")

    return name, summary, lists_count, board_data


def _run_rules(board_data, config=None):
    """Run the rule engine against parsed board data."""
    try:
        engine = RuleEngine(config=config)
        rule_results = engine.run_all_rules(board_data)
        return engine, rule_results
    except Exception as exc:
        raise ValueError(
            f"Rule engine error: {str(exc)}. Please check your config/rules_config.yaml file."
        )


def _score_rules(engine, rule_results):
    """Compute overall score and grade metadata for rule results."""
    try:
        weights = engine.get_rule_weights()
        scoring_result = calculate_overall_score(rule_results, weights)
        grade_info = get_grade_from_score(scoring_result["overall_score"])
        return scoring_result, grade_info
    except Exception as exc:
        raise ValueError(f"Scoring error: {str(exc)}")


def _build_report(
    filename,
    summary,
    lists_count,
    board_data,
    scoring_result,
    grade_info,
    rule_results,
    rule_settings=None,
):
    """Assemble report payload and DB score summary."""
    generated_at = datetime.now(timezone.utc).isoformat()
    report_data = {
        "board": {
            "name": summary["board_name"],
            "cards_count": summary["cards_count"],
            "lists_count": lists_count,
            "members_count": summary["members_count"],
        },
        "card_short_urls": {
            card.get("id"): card.get("short_url")
            for card in board_data.get("cards", [])
            if card.get("id") and card.get("short_url")
        },
        "generated_at": generated_at,
        "scores": {
            "overall_score": scoring_result["overall_score"],
            "grade": grade_info["grade"],
            "grade_description": grade_info["description"],
            "total_findings": scoring_result["total_failures"],
            "rules_passed": scoring_result["rules_passed"],
            "rules_failed": scoring_result["rules_failed"],
        },
        "summary": {
            "filename": filename,
            "note": "Analysis complete using 14-rule engine",
        },
        "rule_results": rule_results,
        "rule_settings": rule_settings or {},
    }
    db_scores = {
        "overall_score": scoring_result["overall_score"],
        "total_findings": scoring_result["total_failures"],
    }
    return report_data, db_scores, generated_at


def _persist_run(db_conn, session_id, board_data, db_scores, report_data, rule_results):
    """Persist run, cards, members, and findings; return run_id."""
    run_id = save_run(
        conn=db_conn,
        session_id=session_id,
        board_data=board_data,
        scores=db_scores,
        report_json=report_data,
    )

    list_map = {lst["id"]: lst["name"] for lst in board_data.get("lists", [])}
    save_cards(
        conn=db_conn,
        run_id=run_id,
        cards=board_data.get("cards", []),
        list_map=list_map,
    )

    save_members(
        conn=db_conn,
        run_id=run_id,
        members=board_data.get("members", []),
    )

    findings = []
    for rule_result in rule_results:
        rule_name = rule_result.get("rule_name")
        for failure in rule_result.get("failures", []):
            findings.append(
                {
                    "card_id": failure.get("card_id"),
                    "card_name": failure.get(
                        "card_name",
                        failure.get("member_name", "Board-level"),
                    ),
                    "rule_name": rule_name,
                    "category": "Individual Rule",
                    "severity": "major",
                    "description": failure.get("reason", "Rule violation"),
                    "suggestion": f"See rule: {rule_name}",
                }
            )

    if findings:
        save_findings(conn=db_conn, run_id=run_id, findings=findings)

    return run_id


def _build_results_context(
    db_conn,
    run_id,
    scoring_result,
    grade_info,
    summary,
    lists_count,
    generated_at,
    rule_results,
):
    """Build template context for the results partial."""
    member_map = get_members_for_run(db_conn, run_id)
    member_names = sorted(set(member_map.values()))
    member_names.append("Unassigned")
    selected_members = _parse_selected_members(request.args, member_names)
    expanded_rule_ids = []
    return {
        "run_id": run_id,
        "overall_score": scoring_result["overall_score"],
        "grade_description": grade_info["description"],
        "board_name": summary["board_name"],
        "cards_count": summary["cards_count"],
        "lists_count": lists_count,
        "members_count": summary["members_count"],
        "generated_at": generated_at,
        "member_names": member_names,
        "selected_members": selected_members,
        "expanded_rule_ids": expanded_rule_ids,
        "rule_results": rule_results,
    }


def _filter_rule_results_by_overrides(rule_results, overrides):
    rules_overrides = overrides.get("rules") or {}
    disabled = {rule_id for rule_id, enabled in rules_overrides.items() if not enabled}
    if not disabled:
        return rule_results
    return [rule for rule in rule_results if rule.get("rule_id") not in disabled]


def _apply_overrides_to_scores(rule_results, base_config, overrides):
    effective_config = _apply_rule_settings_overrides(base_config, overrides)
    engine = RuleEngine(config=effective_config)
    weights = engine.get_rule_weights()
    scoring_result = calculate_overall_score(rule_results, weights)
    grade_info = get_grade_from_score(scoring_result["overall_score"])
    return scoring_result, grade_info


def _load_rules_config():
    engine = RuleEngine()
    return engine.config or {}


def _get_rule_settings_overrides():
    return session.get("rule_settings_overrides") or {}


def _merge_rule_settings(config, overrides):
    deprecated = {
        "weekly_workload",
        "individual_overload",
        "near_term_overcommitment",
        "unscheduled_work",
        "flow_progress_signal",
    }
    rule_labels = {
        "card_ownership": "Card Ownership",
        "card_due_date": "Card Due Date",
        "card_descriptiveness": "Card Descriptiveness",
        "story_point_estimation": "Story Point Estimation Coverage",
        "past_due_violation": "Past Due Violation",
        "progress_threshold": "Progress Threshold",
        "progress_monitoring": "Progress Monitoring",
        "card_completion": "Card Completion",
        "card_effort": "Card Effort",
        "description_canonicalization": "Description Canonicalization",
    }

    rules = []
    for rule_id, label in rule_labels.items():
        if rule_id in deprecated:
            continue
        base = config.get(rule_id, {})
        enabled = base.get("enabled", True)
        override_enabled = overrides.get("rules", {}).get(rule_id)
        if override_enabled is not None:
            enabled = override_enabled
        rules.append(
            {
                "id": rule_id,
                "name": label,
                "description": base.get("description", ""),
                "enabled": enabled,
            }
        )

    def _with_override(section, key, default):
        value = config.get(section, {}).get(key, default)
        value = overrides.get(section, {}).get(key, value)
        return value

    return {
        "rules": rules,
        "card_descriptiveness": {
            "minimum_desc_char": _with_override("card_descriptiveness", "minimum_desc_char", 20),
        },
        "progress_threshold": {
            "max_wip_per_member": _with_override("progress_threshold", "max_wip_per_member", 3),
        },
        "progress_monitoring": {
            "threshold_num_days": _with_override("progress_monitoring", "threshold_num_days", 5),
        },
    }


def _parse_rule_settings_form(form, config):
    rule_ids = [
        "card_ownership",
        "card_due_date",
        "card_descriptiveness",
        "story_point_estimation",
        "past_due_violation",
        "progress_threshold",
        "progress_monitoring",
        "card_completion",
        "card_effort",
        "description_canonicalization",
    ]
    overrides = {"rules": {}}

    for rule_id in rule_ids:
        key = f"rule_{rule_id}"
        overrides["rules"][rule_id] = key in form

    def _parse_int(name, section, key, default):
        raw = form.get(name, "").strip()
        if raw == "":
            return
        try:
            value = int(raw)
        except ValueError:
            value = default
        overrides.setdefault(section, {})[key] = max(0, value)

    _parse_int(
        "minimum_desc_char",
        "card_descriptiveness",
        "minimum_desc_char",
        config.get("card_descriptiveness", {}).get("minimum_desc_char", 20),
    )
    _parse_int(
        "max_wip_per_member",
        "progress_threshold",
        "max_wip_per_member",
        config.get("progress_threshold", {}).get("max_wip_per_member", 3),
    )
    _parse_int(
        "threshold_num_days",
        "progress_monitoring",
        "threshold_num_days",
        config.get("progress_monitoring", {}).get("threshold_num_days", 5),
    )
    return overrides


def _apply_rule_settings_overrides(base_config, overrides):
    if not overrides:
        return base_config

    config = json.loads(json.dumps(base_config))
    for rule_id, enabled in overrides.get("rules", {}).items():
        config.setdefault(rule_id, {})["enabled"] = bool(enabled)

    for section in ("card_descriptiveness", "progress_threshold", "progress_monitoring"):
        if section in overrides:
            config.setdefault(section, {}).update(overrides[section])

    return config


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
    # -------------------------
    # Step 1: Validate File & Parse JSON
    # -------------------------
    uploaded = request.files.get("file") or request.files.get("trello_file")
    try:
        filename, summary, lists_count, board_data = _parse_upload(uploaded)
    except ValueError as exc:
        return render_template("partials/error.html", message=str(exc))

    # -------------------------
    # Step 2: Run Rule Engine
    # -------------------------
    session_id = get_or_set_session_id()
    db = get_db()
    
    # Cleanup old runs
    ttl_seconds = int(current_app.config.get("RUN_TTL_SECONDS", 21600))
    cleanup_old_runs(db, ttl_seconds)

    try:
        base_config = _load_rules_config()
        effective_config = _apply_rule_settings_overrides(
            base_config, _get_rule_settings_overrides()
        )
        engine, rule_results = _run_rules(board_data, effective_config)
    except ValueError as exc:
        return render_template("partials/error.html", message=str(exc))

    # -------------------------
    # Step 3: Calculate Scores
    # -------------------------
    try:
        scoring_result, grade_info = _score_rules(engine, rule_results)
    except ValueError as exc:
        return render_template("partials/error.html", message=str(exc))

    # -------------------------
    # Step 4: Build Report JSON
    # -------------------------
    
    report_data, db_scores, generated_at = _build_report(
        filename,
        summary,
        lists_count,
        board_data,
        scoring_result,
        grade_info,
        rule_results,
        rule_settings=_get_rule_settings_overrides(),
    )

    # -------------------------
    # Step 5: Save to Database
    # -------------------------
    
    run_id = _persist_run(db, session_id, board_data, db_scores, report_data, rule_results)
    context = _build_results_context(
        db,
        run_id,
        scoring_result,
        grade_info,
        summary,
        lists_count,
        generated_at,
        rule_results,
    )

    # -------------------------
    # Step 6: Return Results
    # -------------------------
    
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
        "SELECT id, report_json FROM runs WHERE id = ? AND session_id = ?",
        (run_id, session_id),
    ).fetchone()
    if run_row is None:
        return render_template(
            "partials/error.html",
            message="Report not found for this session.",
        )
    report_data = json.loads(run_row["report_json"] or "{}")
    card_short_urls = report_data.get("card_short_urls", {})

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
    rule_results = report_data.get("rule_results", [])
    overdue_days = None
    for rule in rule_results:
        if rule.get("rule_id") != "past_due_violation":
            continue
        for failure in rule.get("failures") or []:
            if failure.get("card_id") == card_id:
                overdue_days = failure.get("days_overdue")
                break
        if overdue_days is not None:
            break

    if overdue_days is not None:
        due_display = _format_due_display(card.get("due")) or "—"
        issues.append(
            f"Overdue: Due date: {due_display} | +{overdue_days} day{'s' if overdue_days != 1 else ''} past due"
        )

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
        short_url=card_short_urls.get(card.get("card_id")),
        issues=issues,
    )

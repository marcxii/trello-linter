"""Report controller for full-page report views.

Responsibilities:
- Fetch the stored report JSON for a session-scoped run.
- Render the full report template (screen or print mode).
- Provide a placeholder route when no run is selected.
"""

from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, render_template, request, session

from src.database.sqlite import get_db
from src.linter.rule_engine import RuleEngine
from src.linter.scoring_engine import calculate_overall_score
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
    run["created_at_display"] = _format_display_date(run.get("created_at"))

    report_data = json.loads(row["report_json"] or "{}")
    overrides = session.get("rule_settings_overrides") or {}
    rules_overrides = overrides.get("rules") or {}
    disabled = {rule_id for rule_id, enabled in rules_overrides.items() if not enabled}
    if disabled and report_data.get("rule_results"):
        rule_results = [
            rule for rule in report_data.get("rule_results", [])
            if rule.get("rule_id") not in disabled
        ]
        base_config = RuleEngine().config or {}
        effective_config = _apply_rule_settings_overrides(base_config, overrides)
        weights = RuleEngine(config=effective_config).get_rule_weights()
        scoring_result = calculate_overall_score(rule_results, weights)
        report_data["rule_results"] = rule_results
        report_data.setdefault("scores", {})
        report_data["scores"]["overall_score"] = scoring_result.get("overall_score", 0)
        report_data["scores"]["total_findings"] = scoring_result.get("total_failures", 0)

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


def _format_display_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        iso = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return str(value)
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"

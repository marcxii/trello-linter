"""CSV export controller.

Responsibilities:
- Validate run_id and session ownership.
- Build report context and serialize it to CSV.
- Return a downloadable attachment with a board-name + run-id filename.
"""

from __future__ import annotations

import json
import re

from flask import Blueprint, Response, request, session

from src.utils.session import get_or_set_session_id
from src.reports.report_builder import load_report_context, _build_rule_rows
from src.reports.csv_exporter import build_report_csv
from src.linter.rule_engine import RuleEngine
from src.linter.scoring_engine import calculate_overall_score

export_bp = Blueprint("export", __name__)


def _slugify_board_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", name.strip())
    return cleaned or "board"


def _build_csv_response(run_id: int) -> Response:
    """Build a CSV export response for a given run."""
    if not run_id:
        return Response("Missing run_id", status=400)

    session_id = get_or_set_session_id()
    selected_members = request.args.getlist("members")
    report_ctx = load_report_context(run_id, session_id, selected_members or None)
    if report_ctx is None:
        return Response("Not found", status=404)

    overrides = session.get("rule_settings_overrides") or {}
    rules_overrides = overrides.get("rules") or {}
    disabled = {rule_id for rule_id, enabled in rules_overrides.items() if not enabled}
    if disabled:
        rule_results = [
            rule for rule in report_ctx.get("rule_results", [])
            if rule.get("rule_id") not in disabled
        ]
        base_config = RuleEngine().config or {}
        effective_config = _apply_rule_settings_overrides(base_config, overrides)
        scoring_engine = RuleEngine(config=effective_config)
        weights = scoring_engine.get_rule_weights()
        scoring_cfg = scoring_engine.get_scoring_config()
        scoring_result = calculate_overall_score(rule_results, weights, scoring_cfg)
        report_ctx["scores"] = {
            **(report_ctx.get("scores", {}) or {}),
            "overall_score": scoring_result.get("overall_score", 0),
            "total_findings": scoring_result.get("total_failures", 0),
        }
        rule_columns, rule_rows = _build_rule_rows(rule_results, report_ctx.get("card_lookup", {}))
        report_ctx["rule_results"] = rule_results
        report_ctx["rule_columns"] = rule_columns
        report_ctx["rule_rows"] = rule_rows

    csv_body = build_report_csv(report_ctx)
    board_name = report_ctx.get("board", {}).get("name", "")
    filename = f"{_slugify_board_name(board_name)}_{run_id}.csv"
    resp = Response(csv_body, mimetype="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return resp


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


@export_bp.get("/export/findings.csv")
def export_findings_csv():
    """Download findings CSV for a given run.

    Query params:
      - run_id: identifier of the lint run
    """

    run_id = request.args.get("run_id", type=int)
    return _build_csv_response(run_id)

"""CSV export controller.

Responsibilities:
- Validate run_id and session ownership.
- Build report context and serialize it to CSV.
- Return a downloadable attachment with a board-name + run-id filename.
"""

from __future__ import annotations

import re

from flask import Blueprint, Response, request

from src.utils.session import get_or_set_session_id
from src.reports.report_builder import load_report_context
from src.reports.csv_exporter import build_report_csv

export_bp = Blueprint("export", __name__)


def _slugify_board_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", name.strip())
    return cleaned or "board"


@export_bp.get("/export/findings.csv")
def export_findings_csv():
    """Download findings CSV for a given run.

    Query params:
      - run_id: identifier of the lint run
    """

    run_id = request.args.get("run_id", type=int)
    if not run_id:
        return Response("Missing run_id", status=400)

    session_id = get_or_set_session_id()
    selected_members = request.args.getlist("members")
    report_ctx = load_report_context(run_id, session_id, selected_members or None)
    if report_ctx is None:
        return Response("Not found", status=404)

    csv_body = build_report_csv(report_ctx)
    board_name = report_ctx.get("board", {}).get("name", "")
    filename = f"{_slugify_board_name(board_name)}_{run_id}.csv"
    resp = Response(csv_body, mimetype="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return resp


@export_bp.get("/export/affected_cards.csv")
def export_affected_cards_csv():
    """Download affected-cards CSV for a given run.

    Query params:
      - run_id: identifier of the lint run
    """

    run_id = request.args.get("run_id", type=int)
    if not run_id:
        return Response("Missing run_id", status=400)

    session_id = get_or_set_session_id()
    selected_members = request.args.getlist("members")
    report_ctx = load_report_context(run_id, session_id, selected_members or None)
    if report_ctx is None:
        return Response("Not found", status=404)

    csv_body = build_report_csv(report_ctx)
    board_name = report_ctx.get("board", {}).get("name", "")
    filename = f"{_slugify_board_name(board_name)}_{run_id}.csv"
    resp = Response(csv_body, mimetype="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return resp

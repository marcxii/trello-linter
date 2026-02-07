"""Build a normalized report context for HTML and CSV outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.database.db_functions import get_cards_for_run, get_members_for_run
from src.database.sqlite import get_db
from src.linter.rules.due_date_rule import evaluate_due_date


def _get_overdue_cards(run_id: int) -> list[dict[str, Any]]:
    """Return overdue cards for a run with metadata."""
    db = get_db()
    cards = get_cards_for_run(db, run_id)
    member_map = get_members_for_run(db, run_id)
    overdue_cards: list[dict[str, Any]] = []

    for card in cards:
        if card.get("is_closed"):
            continue
        result = evaluate_due_date(card.get("due"))
        if not result.get("overdue"):
            continue

        member_names = [
            member_map.get(member_id, member_id) for member_id in (card.get("members") or [])
        ]
        overdue_cards.append(
            {
                "name": card.get("card_name") or "(untitled card)",
                "card_id": card.get("card_id"),
                "days_past_due": result.get("days_past_due", 0),
                "list_name": card.get("list_name") or "",
                "members": member_names,
                "due": card.get("due"),
            }
        )

    overdue_cards.sort(key=lambda item: item.get("days_past_due", 0), reverse=True)
    return overdue_cards


def load_report_context(run_id: int, session_id: str) -> dict[str, Any] | None:
    """Load report context shared by HTML and CSV renderers."""
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
        return None

    report = json.loads(row["report_json"] or "{}")
    board = report.get("board", {})
    scores = report.get("scores", {})
    summary = report.get("summary", {})
    generated_at = report.get("generated_at") or datetime.now(timezone.utc).isoformat()

    run = {
        "id": row["id"],
        "created_at": row["created_at"],
        "board_ref": row["board_ref"] or "(unknown)",
        "source_type": "upload",
    }

    return {
        "run": run,
        "report": report,
        "board": board,
        "scores": scores,
        "summary": summary,
        "generated_at": generated_at,
        "overdue_cards": _get_overdue_cards(run_id),
    }

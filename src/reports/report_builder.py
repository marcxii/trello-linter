"""Report context builder for HTML and CSV exports.

Responsibilities:
- Load a session-scoped run and its stored report JSON.
- Enrich with derived data (overdue cards, normalized rule rows).
- Return a stable context shape for multiple renderers.

Returned context keys:
- run, report, board, scores, summary, generated_at
- overdue_cards, rule_columns, rule_rows
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.database.db_functions import get_cards_for_run, get_members_for_run
from src.database.sqlite import get_db


def _filter_rule_results_by_members(
    rule_results: list[dict[str, Any]],
    selected_members: list[str],
    card_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter rule failures by selected member names."""
    if not selected_members:
        return []

    selected_set = set(selected_members)
    include_unassigned = "Unassigned" in selected_set
    selected_set.discard("Unassigned")

    filtered_results = []
    for rule in rule_results:
        failures = rule.get("failures") or []
        filtered_failures = []
        for failure in failures:
            member_name = failure.get("member_name")
            failure_members = failure.get("members") or []
            if member_name:
                if member_name in selected_set:
                    filtered_failures.append(failure)
                continue
            if failure_members:
                if any(member in selected_set for member in failure_members):
                    filtered_failures.append(failure)
                elif not selected_set and include_unassigned:
                    filtered_failures.append(failure)
                continue

            card_id = failure.get("card_id")
            lookup = card_lookup.get(card_id) if card_id else None
            members = (lookup.get("members") if lookup else None) or []
            if not members:
                if include_unassigned:
                    filtered_failures.append(failure)
            elif any(member in selected_set for member in members):
                filtered_failures.append(failure)

        if filtered_failures:
            filtered_rule = dict(rule)
            filtered_rule["failures"] = filtered_failures
            filtered_rule["fail_count"] = len(filtered_failures)
            filtered_results.append(filtered_rule)

    return filtered_results


def _enrich_rule_results(
    rule_results: list[dict[str, Any]],
    card_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich rule failures with card metadata for display."""
    enriched_results = []
    for rule in rule_results or []:
        failures = rule.get("failures") or []
        enriched_failures = []
        for failure in failures:
            card_id = failure.get("card_id")
            lookup = card_lookup.get(card_id) if card_id else None
            enriched = dict(failure)
            if lookup:
                enriched.setdefault("card_name", lookup.get("card_name"))
                enriched.setdefault("list_name", lookup.get("list_name"))
                enriched.setdefault("members", lookup.get("members", []))
                enriched.setdefault("due", lookup.get("due"))
            enriched_failures.append(enriched)
        enriched_rule = dict(rule)
        enriched_rule["failures"] = enriched_failures
        enriched_results.append(enriched_rule)
    return enriched_results


def _build_overdue_cards(
    rule_results: list[dict[str, Any]],
    card_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return overdue cards derived from rule_results (past_due_violation)."""
    overdue_cards: list[dict[str, Any]] = []
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

    overdue_cards.sort(key=lambda item: item.get("days_past_due", 0), reverse=True)
    return overdue_cards


def _build_card_lookup(run_id: int, member_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Return card_id -> card details for a run."""
    db = get_db()
    cards = get_cards_for_run(db, run_id)
    lookup: dict[str, dict[str, Any]] = {}

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

    return lookup


def _filter_cards_by_members(
    cards: list[dict[str, Any]],
    selected_members: list[str],
) -> list[dict[str, Any]]:
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


def _build_rule_rows(
    rule_results: list[dict[str, Any]],
    card_lookup: dict[str, dict[str, Any]],
) -> tuple[list[str], list[list[str]]]:
    """Return a normalized, flat rule table for CSV/report exports."""
    columns = ["Rule", "Card", "List", "Members", "Due_date"]
    rows: list[list[str]] = []

    for rule in rule_results or []:
        rule_name = rule.get("rule_name") or rule.get("rule_id") or "Rule"
        for failure in rule.get("failures") or []:
            card_id = failure.get("card_id")
            lookup = card_lookup.get(card_id) if card_id else None

            card_name = (
                failure.get("card_name")
                or (lookup.get("card_name") if lookup else None)
                or failure.get("member_name")
                or "Board-level"
            )
            list_name = (
                failure.get("list_name")
                or (lookup.get("list_name") if lookup else None)
                or ""
            )

            if failure.get("member_name"):
                members = [failure.get("member_name")]
            elif failure.get("members"):
                members = list(failure.get("members") or [""])
            else:
                members = (lookup.get("members") if lookup else None) or [""]

            due_value = failure.get("due") or (lookup.get("due") if lookup else "")
            due_date = str(due_value)[:10] if due_value else ""

            for member in members:
                rows.append(
                    [
                        str(rule_name),
                        str(card_name),
                        str(list_name),
                        str(member),
                        str(due_date),
                    ]
                )

    return columns, rows


def load_report_context(
    run_id: int,
    session_id: str,
    selected_members: list[str] | None = None,
) -> dict[str, Any] | None:
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

    rule_results = report.get("rule_results", [])
    member_map = get_members_for_run(db, run_id)
    member_names = sorted(set(member_map.values()))
    member_names.append("Unassigned")
    if selected_members is None:
        selected_members = member_names
    else:
        if selected_members == ["__none__"]:
            selected_members = []
        else:
            valid = set(member_names)
            selected_members = [m for m in selected_members if m in valid]

    card_lookup = _build_card_lookup(run_id, member_map)
    overdue_cards = _build_overdue_cards(rule_results, card_lookup)
    overdue_cards = _filter_cards_by_members(overdue_cards, selected_members)
    if set(selected_members) != set(member_names):
        rule_results = _filter_rule_results_by_members(rule_results, selected_members, card_lookup)
    rule_results = _enrich_rule_results(rule_results, card_lookup)
    rule_columns, rule_rows = _build_rule_rows(rule_results, card_lookup)

    return {
        "run": run,
        "report": report,
        "board": board,
        "scores": scores,
        "summary": summary,
        "generated_at": generated_at,
        "overdue_cards": overdue_cards,
        "rule_columns": rule_columns,
        "rule_rows": rule_rows,
        "rule_results": rule_results,
        "member_names": member_names,
        "selected_members": selected_members,
        "card_lookup": card_lookup,
    }

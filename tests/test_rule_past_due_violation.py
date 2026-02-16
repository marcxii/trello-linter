"""Rule-level tests for past_due_violation behavior.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from datetime import datetime, timedelta, timezone

from src.linter.rules.capacity_rules import check_past_due_violation


def _parsed_data(cards, lists):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": [],
        "checklists": [],
    }


def test_past_due_violation_passes_for_future_due_date():
    future_due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "On Time", "list_id": "l1", "closed": False, "due": future_due}],
    )
    result = check_past_due_violation(parsed, {})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_past_due_violation_fails_for_overdue_open_card():
    past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Late", "list_id": "l1", "closed": False, "due": past_due, "dueComplete": False}],
    )
    result = check_past_due_violation(parsed, {})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1

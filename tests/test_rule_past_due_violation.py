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
        cards=[{"id": "c1", "name": "On Time", "list_id": "l1", "closed": False, "dueComplete": False, "due": future_due}],
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


def test_past_due_violation_missing_due_complete_does_not_fail():
    past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Late", "list_id": "l1", "closed": False, "due": past_due}],
    )
    result = check_past_due_violation(parsed, {})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_past_due_violation_excludes_complete_or_archived_cards():
    past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[
            {"id": "c1", "name": "Complete", "list_id": "l1", "closed": False, "dueComplete": True, "due": past_due},
            {"id": "c2", "name": "Archived", "list_id": "l1", "closed": True, "dueComplete": False, "due": past_due},
        ],
    )
    result = check_past_due_violation(parsed, {})
    assert result["eligible_count"] == 0
    assert result["fail_count"] == 0

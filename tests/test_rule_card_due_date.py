"""Rule-level tests for card_due_date violations.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from src.linter.rules.assignment_rules import check_card_due_date


def _parsed_data(cards, lists):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": [],
        "checklists": [],
    }


def test_card_due_date_passes_when_due_date_exists():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Scheduled", "list_id": "l1", "closed": False, "due": "2026-03-01T10:00:00.000Z"}],
    )
    result = check_card_due_date(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_card_due_date_fails_when_due_date_missing():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Missing Due", "list_id": "l1", "closed": False, "due": None}],
    )
    result = check_card_due_date(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1

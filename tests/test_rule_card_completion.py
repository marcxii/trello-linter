"""Rule-level tests for card_completion violations.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from src.linter.rules.assignment_rules import check_card_completion


def _parsed_data(cards, lists):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": [],
        "checklists": [],
    }


def test_card_completion_passes_when_closed_card_is_in_done():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "Done", "closed": False}],
        cards=[{"id": "c1", "name": "Finished", "list_id": "l1", "closed": True}],
    )
    result = check_card_completion(
        parsed,
        {
            "done_keywords": ["done"],
            "backlog_keywords": ["backlog"],
            "in_progress_keywords": ["in progress"],
        },
    )
    assert result["eligible_count"] == 0
    assert result["fail_count"] == 0


def test_card_completion_fails_when_closed_card_not_in_done():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Misplaced", "list_id": "l1", "closed": True}],
    )
    result = check_card_completion(
        parsed,
        {
            "done_keywords": ["done"],
            "backlog_keywords": ["backlog"],
            "in_progress_keywords": ["in progress"],
        },
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1

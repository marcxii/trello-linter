"""Rule-level tests for card_descriptiveness violations.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from src.linter.rules.estimation_rules import check_card_descriptiveness


def _parsed_data(cards, lists):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": [],
        "checklists": [],
    }


def test_card_descriptiveness_passes_for_long_description():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "Backlog", "closed": False}],
        cards=[{"id": "c1", "name": "Detailed", "list_id": "l1", "closed": False, "desc": "This description is longer than twenty chars."}],
    )
    result = check_card_descriptiveness(
        parsed,
        {
            "backlog_keywords": ["backlog"],
            "in_progress_keywords": ["in progress"],
            "card_descriptiveness": {"minimum_desc_char": 20},
        },
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_card_descriptiveness_fails_for_short_description():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "Backlog", "closed": False}],
        cards=[{"id": "c1", "name": "Short", "list_id": "l1", "closed": False, "desc": "Too short"}],
    )
    result = check_card_descriptiveness(
        parsed,
        {
            "backlog_keywords": ["backlog"],
            "in_progress_keywords": ["in progress"],
            "card_descriptiveness": {"minimum_desc_char": 20},
        },
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_card_descriptiveness_applies_to_any_list():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "Done", "closed": False}],
        cards=[{"id": "c1", "name": "Short", "list_id": "l1", "closed": False, "desc": "tiny"}],
    )
    result = check_card_descriptiveness(
        parsed,
        {"card_descriptiveness": {"minimum_desc_char": 20}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_card_descriptiveness_excludes_archived_cards():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "Backlog", "closed": False}],
        cards=[{"id": "c1", "name": "Archived", "list_id": "l1", "closed": True, "desc": "short"}],
    )
    result = check_card_descriptiveness(
        parsed,
        {"card_descriptiveness": {"minimum_desc_char": 20}},
    )
    assert result["eligible_count"] == 0
    assert result["fail_count"] == 0

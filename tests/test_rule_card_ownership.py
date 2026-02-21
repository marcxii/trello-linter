"""Rule-level tests for card_ownership violations.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from src.linter.rules.assignment_rules import check_card_ownership


def _parsed_data(cards, lists):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": [],
        "checklists": [],
    }


def test_card_ownership_passes_when_member_assigned():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Owned", "list_id": "l1", "closed": False, "members": ["m1"]}],
    )
    result = check_card_ownership(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_card_ownership_fails_when_no_member_assigned():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Unowned", "list_id": "l1", "closed": False, "members": []}],
    )
    result = check_card_ownership(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_card_ownership_ignores_backlog_but_includes_other_lists():
    parsed = _parsed_data(
        lists=[
            {"id": "l1", "name": "Backlog", "closed": False},
            {"id": "l2", "name": "Done", "closed": False},
        ],
        cards=[
            {"id": "c1", "name": "Backlog Unowned", "list_id": "l1", "closed": False, "members": []},
            {"id": "c2", "name": "Done Unowned", "list_id": "l2", "closed": False, "members": []},
        ],
    )
    result = check_card_ownership(
        parsed,
        {"backlog_keywords": ["backlog"]},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert result["failures"][0]["card_id"] == "c2"


def test_card_ownership_excludes_archived_cards():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Archived Unowned", "list_id": "l1", "closed": True, "members": []}],
    )
    result = check_card_ownership(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 0
    assert result["fail_count"] == 0

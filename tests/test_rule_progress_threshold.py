"""Rule-level tests for progress_threshold violations.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from src.linter.rules.capacity_rules import check_progress_threshold


def _parsed_data(cards, lists, members):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": members,
        "checklists": [],
    }


def test_progress_threshold_passes_within_member_limit():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        members=[{"id": "m1", "fullName": "Alex"}],
        cards=[
            {"id": "c1", "name": "A", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c2", "name": "B", "list_id": "l1", "closed": False, "members": ["m1"]},
        ],
    )
    result = check_progress_threshold(
        parsed,
        {"in_progress_keywords": ["in progress"], "progress_threshold": {"max_wip_per_member": 2}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_progress_threshold_fails_when_member_exceeds_limit():
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        members=[{"id": "m1", "fullName": "Alex"}],
        cards=[
            {"id": "c1", "name": "A", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c2", "name": "B", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c3", "name": "C", "list_id": "l1", "closed": False, "members": ["m1"]},
        ],
    )
    result = check_progress_threshold(
        parsed,
        {"in_progress_keywords": ["in progress"], "progress_threshold": {"max_wip_per_member": 2}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert len(result["failures"]) == 3
    assert all(failure.get("card_id") for failure in result["failures"])

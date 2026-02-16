"""Rule-level tests for progress_monitoring staleness checks.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from datetime import datetime, timedelta, timezone

from src.linter.rules.flow_rules import check_progress_monitoring


def _parsed_data(cards, lists):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": lists,
        "cards": cards,
        "members": [],
        "checklists": [],
    }


def test_progress_monitoring_passes_for_recent_activity():
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Active", "list_id": "l1", "closed": False, "dateLastActivity": recent}],
    )
    result = check_progress_monitoring(
        parsed,
        {"in_progress_keywords": ["in progress"], "progress_monitoring": {"threshold_num_days": 5}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_progress_monitoring_fails_for_stale_activity():
    stale = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    parsed = _parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Stale", "list_id": "l1", "closed": False, "dateLastActivity": stale}],
    )
    result = check_progress_monitoring(
        parsed,
        {"in_progress_keywords": ["in progress"], "progress_monitoring": {"threshold_num_days": 5}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1

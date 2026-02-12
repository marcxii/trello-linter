from datetime import datetime, timedelta, timezone

from src.linter.rule_engine import RuleEngine
from src.linter.rules.assignment_rules import (
    check_card_completion,
    check_card_due_date,
    check_card_ownership,
    check_unscheduled_work,
)
from src.linter.rules.capacity_rules import (
    check_past_due_violation,
    check_progress_threshold,
)
from src.linter.rules.estimation_rules import (
    check_card_descriptiveness,
    check_description_canonicalization,
    check_story_point_estimation,
)
from src.linter.rules.flow_rules import (
    check_flow_progress_signal,
    check_progress_monitoring,
)


def _base_parsed_data(cards=None, lists=None, members=None):
    return {
        "board": {"id": "b1", "name": "Board", "desc": ""},
        "lists": lists or [],
        "cards": cards or [],
        "members": members or [],
        "checklists": [],
    }


def test_card_ownership_pass_and_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[
            {"id": "c1", "name": "Owned", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c2", "name": "Unowned", "list_id": "l1", "closed": False, "members": []},
        ],
    )
    result = check_card_ownership(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 2
    assert result["fail_count"] == 1
    assert result["failures"][0]["card_id"] == "c2"


def test_card_due_date_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Missing due", "list_id": "l1", "closed": False}],
    )
    result = check_card_due_date(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert result["failures"][0]["reason"] == "No due date set"


def test_unscheduled_work_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[
            {
                "id": "c1",
                "name": "Committed",
                "list_id": "l1",
                "closed": False,
                "desc": "SP: 3",
                "members": ["m1"],
            }
        ],
    )
    result = check_unscheduled_work(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert result["failures"][0]["card_id"] == "c1"


def test_card_completion_fail():
    parsed = _base_parsed_data(
        lists=[
            {"id": "l1", "name": "Backlog", "closed": False},
            {"id": "l2", "name": "Done", "closed": False},
        ],
        cards=[{"id": "c1", "name": "Closed", "list_id": "l1", "closed": True}],
    )
    result = check_card_completion(
        parsed,
        {"backlog_keywords": ["backlog"], "in_progress_keywords": ["in progress"], "done_keywords": ["done"]},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert result["failures"][0]["reason"] == "Card closed but not in Done list"


def test_card_descriptiveness_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "Backlog", "closed": False}],
        cards=[{"id": "c1", "name": "Short", "list_id": "l1", "closed": False, "desc": "Too short"}],
    )
    result = check_card_descriptiveness(
        parsed,
        {"backlog_keywords": ["backlog"], "in_progress_keywords": ["in progress"], "card_descriptiveness": {"minimum_desc_char": 20}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_story_point_estimation_pass_and_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[
            {"id": "c1", "name": "No SP", "list_id": "l1", "closed": False, "desc": "No points"},
            {"id": "c2", "name": "With SP", "list_id": "l1", "closed": False, "desc": "SP: 5"},
        ],
    )
    result = check_story_point_estimation(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 2
    assert result["fail_count"] == 1
    assert result["failures"][0]["card_id"] == "c1"


def test_description_canonicalization_pass_and_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "Backlog", "closed": False}],
        cards=[
            {"id": "c1", "name": "Bad", "list_id": "l1", "closed": False, "desc": "Just text"},
            {"id": "c2", "name": "Good", "list_id": "l1", "closed": False, "desc": "As a user, I want search"},
        ],
    )
    result = check_description_canonicalization(
        parsed,
        {"backlog_keywords": ["backlog"], "in_progress_keywords": ["in progress"]},
    )
    assert result["eligible_count"] == 2
    assert result["fail_count"] == 1
    assert result["failures"][0]["card_id"] == "c1"


def test_past_due_violation_fail():
    past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[
            {"id": "c1", "name": "Late", "list_id": "l1", "closed": False, "due": past_due},
        ],
    )
    result = check_past_due_violation(parsed)
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert result["failures"][0]["days_overdue"] >= 1


def test_progress_threshold_fail():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[
            {"id": "c1", "name": "A", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c2", "name": "B", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c3", "name": "C", "list_id": "l1", "closed": False, "members": ["m1"]},
            {"id": "c4", "name": "D", "list_id": "l1", "closed": False, "members": ["m1"]},
        ],
        members=[{"id": "m1", "fullName": "Alex", "username": "alex"}],
    )
    result = check_progress_threshold(parsed, {"in_progress_keywords": ["in progress"], "progress_threshold": {"max_wip_per_member": 3}})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1
    assert result["failures"][0]["member_name"] == "Alex"


def test_progress_monitoring_skips_without_dates():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "No Dates", "list_id": "l1", "closed": False}],
    )
    result = check_progress_monitoring(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 0


def test_flow_progress_signal_fail_with_no_completions():
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "WIP", "list_id": "l1", "closed": False}],
    )
    result = check_flow_progress_signal(parsed, {"in_progress_keywords": ["in progress"]})
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_rule_engine_respects_enabled_and_attaches_description():
    config = {
        "card_ownership": {"enabled": False, "description": "Ownership"},
        "card_due_date": {"enabled": True, "description": "Due date"},
        "lists": {"in_progress_keywords": ["in progress"], "backlog_keywords": ["backlog"], "done_keywords": ["done"]},
    }
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Card", "list_id": "l1", "closed": False}],
    )
    engine = RuleEngine(config=config)
    results = engine.run_all_rules(parsed)
    rule_ids = {rule.get("rule_id") for rule in results}
    assert "card_ownership" not in rule_ids
    assert "card_due_date" in rule_ids
    due_rule = next(rule for rule in results if rule.get("rule_id") == "card_due_date")
    assert due_rule.get("description") == "Due date"

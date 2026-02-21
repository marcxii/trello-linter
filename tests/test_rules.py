"""Integration-level rule engine tests.

Behavioral rule pass/fail coverage lives in tests/test_rule_*.py.
This file is intentionally limited to RuleEngine wiring expectations.
"""

from src.linter.rule_engine import RuleEngine


def _base_parsed_data(cards=None, lists=None, members=None):
    return {
        "board": {"id": "b1", "name": "Board", "desc": ""},
        "lists": lists or [],
        "cards": cards or [],
        "members": members or [],
        "checklists": [],
    }


def test_rule_engine_respects_enabled_and_attaches_description():
    config = {
        "card_ownership": {"enabled": False, "description": "Ownership"},
        "card_due_date": {"enabled": True, "description": "Due date"},
        "lists": {
            "in_progress_keywords": ["in progress"],
            "backlog_keywords": ["backlog"],
            "done_keywords": ["done"],
        },
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


def test_run_specific_rules_filters_results_to_requested_ids():
    config = {
        "card_ownership": {"enabled": True},
        "card_due_date": {"enabled": True},
        "lists": {
            "in_progress_keywords": ["in progress"],
            "backlog_keywords": ["backlog"],
            "done_keywords": ["done"],
        },
    }
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        cards=[{"id": "c1", "name": "Card", "list_id": "l1", "closed": False, "members": []}],
    )
    engine = RuleEngine(config=config)
    results = engine.run_specific_rules(parsed, ["card_due_date"])
    assert len(results) == 1
    assert results[0]["rule_id"] == "card_due_date"


def test_get_enabled_rules_reflects_config_flags():
    engine = RuleEngine(
        config={
            "card_ownership": {"enabled": False},
            "card_due_date": {"enabled": True},
            "card_completion": {"enabled": False},
        }
    )
    enabled = engine.get_enabled_rules()
    assert "card_due_date" in enabled
    assert "card_ownership" not in enabled
    assert "card_completion" not in enabled


def test_missing_config_path_falls_back_to_empty_config():
    engine = RuleEngine(config_path="config/does_not_exist.yaml")
    assert engine.config == {}


def test_archived_cards_are_excluded_from_all_rules():
    config = {
        "lists": {
            "in_progress_keywords": ["in progress"],
            "backlog_keywords": ["backlog"],
            "done_keywords": ["done"],
        },
        "card_ownership": {"enabled": True},
        "card_due_date": {"enabled": True},
        "card_descriptiveness": {"enabled": True},
        "story_point_estimation": {"enabled": True},
        "past_due_violation": {"enabled": True},
        "progress_threshold": {"enabled": True, "max_wip_per_member": 1},
        "progress_monitoring": {"enabled": True, "threshold_num_days": 1},
        "card_completion": {"enabled": True},
        "card_effort": {"enabled": True},
        "description_canonicalization": {"enabled": True},
    }
    parsed = _base_parsed_data(
        lists=[{"id": "l1", "name": "In Progress", "closed": False}],
        members=[{"id": "m1", "fullName": "Alex"}],
        cards=[
            {
                "id": "c1",
                "name": "Archived Card",
                "list_id": "l1",
                "closed": True,
                "dueComplete": True,
                "due": None,
                "members": [],
                "desc": "not canonical",
                "dateLastActivity": "2025-01-01T00:00:00.000Z",
            }
        ],
    )
    engine = RuleEngine(config=config)
    rule_ids = [
        "card_ownership",
        "card_due_date",
        "card_descriptiveness",
        "story_point_estimation",
        "past_due_violation",
        "progress_threshold",
        "progress_monitoring",
        "card_completion",
        "card_effort",
        "description_canonicalization",
    ]
    results = engine.run_specific_rules(parsed, rule_ids)
    assert len(results) == len(rule_ids)
    assert all(result.get("eligible_count") == 0 for result in results)
    assert all(result.get("fail_count") == 0 for result in results)

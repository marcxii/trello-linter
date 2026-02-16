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

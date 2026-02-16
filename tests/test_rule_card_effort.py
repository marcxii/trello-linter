from pathlib import Path

import yaml

from src.linter.rules.estimation_rules import check_card_effort


def _parsed_data(descriptions, list_name="In Progress"):
    return {
        "board": {"id": "b1", "name": "Board"},
        "lists": [{"id": "l1", "name": list_name, "closed": False}],
        "cards": [
            {"id": f"c{idx}", "name": f"Card {idx}", "list_id": "l1", "closed": False, "desc": desc}
            for idx, desc in enumerate(descriptions, start=1)
        ],
        "members": [],
        "checklists": [],
    }


def test_card_effort_accepts_effort_variants():
    descriptions = [
        "Effort 3",
        "Effort: 3",
        "effort-hours 2",
        "Effort is 1.5",
        "Hours 6",
        "Minutes 90",
        "Estimation 5",
        "Estimate 4",
        "est 2",
        "Estimated Hours 2",
        "Estimated Time 45",
        "Time Estimate 30",
        "Dev Effort 3",
        "engineeringEffort=5",
    ]
    parsed = _parsed_data(descriptions)
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    result = check_card_effort(
        parsed,
        {"in_progress_keywords": ["in progress"], "card_effort": config.get("card_effort", {})},
    )
    assert result["eligible_count"] == len(descriptions)
    assert result["fail_count"] == 0


def test_card_effort_flags_missing_effort():
    descriptions = [
        "No estimates here",
        "SP 3",
        "Story Point 5",
        "Point Value 8",
        "Size 3",
    ]
    parsed = _parsed_data(descriptions)
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    result = check_card_effort(
        parsed,
        {"in_progress_keywords": ["in progress"], "card_effort": config.get("card_effort", {})},
    )
    assert result["eligible_count"] == len(descriptions)
    assert result["fail_count"] == len(descriptions)

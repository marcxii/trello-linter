"""Rule-level tests for story_point_estimation matching.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from pathlib import Path

import yaml

from src.linter.rules.estimation_rules import check_story_point_estimation


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


def test_story_point_estimation_accepts_story_point():
    descriptions = [
        "Story Point 5",
        "SP 2",
        "Story Points: 8",
        "SP: 3",
        "Story Point is 3.5",
        "story-point 5",
        "point-value 8",
        "pts 3",
        "Point Value 8",
        "Size: 5",
        "points 2",
        "story_point 3",
        "storyPoint 3",
        "point_value=8",
    ]
    parsed = _parsed_data(descriptions)
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    result = check_story_point_estimation(
        parsed,
        {"in_progress_keywords": ["in progress"], "story_point_estimation": config.get("story_point_estimation", {})},
    )
    assert result["eligible_count"] == len(descriptions)
    assert result["fail_count"] == 0


def test_story_point_estimation_flags_missing_story_point():
    descriptions = [
        "No estimates here",
        "Effort 3",
        "est 2",
        "effort_hours 2",
        "timeEstimate 45",
        "Minutes 90",
        "Estimation 13",
        "Estimated Hours 2",
        "Dev Effort 3",
    ]
    parsed = _parsed_data(descriptions)
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    result = check_story_point_estimation(
        parsed,
        {"in_progress_keywords": ["in progress"], "story_point_estimation": config.get("story_point_estimation", {})},
    )
    assert result["eligible_count"] == len(descriptions)
    assert result["fail_count"] == len(descriptions)


def test_story_point_estimation_applies_to_any_list():
    parsed = _parsed_data(["No story points here"], list_name="Backlog")
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    result = check_story_point_estimation(
        parsed,
        {"story_point_estimation": config.get("story_point_estimation", {})},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1

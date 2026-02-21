"""Rule-level tests for description_canonicalization matching.

These tests validate rule behavior directly; engine wiring stays in tests/test_rules.py.
"""

from pathlib import Path

import yaml

from src.linter.rules.estimation_rules import check_description_canonicalization


def _parsed_data(descriptions, list_name="Backlog"):
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


def test_description_canonicalization_accepts_examples():
    descriptions = [
        "As a team member, I must confirm the project scope, so that we avoid rework later.",
        "As the release manager, I’m responsible for tagging and packaging builds, so that deployments are repeatable.",
        "As the project team, we’re accountable for maintaining the project plan, so that deadlines stay visible.",
        "As a developer, I need to refactor the rule engine in order to support configurable weighting.",
        "As a user, I want meaningful error messages so that I understand what went wrong and how to proceed.",
        "As an analyst I have to review the metrics so we can improve the dashboard.",
        "As product owner I need to define the backlog to align on priorities.",
        "As the designer I would like to update the UI so that the team can review it.",
        "As a member of Team XYZ we plan to consolidate requirements so that everyone can agree.",
        "As part of the platform team we will document the APIs to enable onboarding.",
        "As someone responsible for security I must audit dependencies so that risk is reduced.",
        "As the person accountable for QA I should be able to run smoke tests so I can validate releases.",
        "As the owner of infrastructure I can upgrade servers in order to maintain uptime.",
        "As a stakeholder in the roadmap I want to review milestones so our team can adjust.",
        "As a user of the system I need to export data so I can share reports.",
        "As contributors to Project Atlas we need to update the docs so that contributors can proceed.",
        "As stakeholders in Project Atlas we plan to approve scope so that the team can move forward.",
        "As we (the mobile team) we have to finalize requirements so that releases stay on schedule.",
        "As a team we must sync the roadmap to ensure alignment.",
        "As a development team we want to refactor modules so we can improve performance.",
        "As the project team we can communicate progress so everyone can stay informed.",
        "As Team Alpha members we will review the prototype so the team can proceed.",
        "As members of Team Beta we have to define roles so that we can deliver on time.",
        "As the release manager I’m tasked with publishing builds so that deployments are repeatable.",
        "As the release manager I’m accountable for packaging builds so that deployments are repeatable.",
        "As the release manager I’m responsible for packaging builds so that deployments are repeatable.",
        "As the project team we’re responsible for maintaining the plan so that deadlines stay visible.",
        "As the project team we’re accountable for maintaining the plan so that deadlines stay visible.",
        "As the project team we’re tasked with maintaining the plan so that deadlines stay visible.",
        "As a user I will create a profile to enable personalization.",
        "As a user I can reset my password to reduce support tickets.",
        "As a user I plan to update preferences to improve recommendations.",
        "As a developer I need to create the schema and update the migrations so we can deploy.",
        "As a developer I need to create the schema, including indexes, so that queries perform well.",
        "As a developer I need to create the schema by using Alembic so we can deploy.",
        "As a developer I need to create the schema within this sprint so that scope stays controlled.",
        "As a developer I need to review the design with stakeholders so that we can validate the approach.",
        "As a developer I need to generate the report using the CLI so that we can share results.",
        "As a developer I need to add logging to reduce friction during debugging.",
        "As a developer I need to improve caching to meet performance goals.",
        "As a developer I need to add tests to ensure quality.",
        "As a developer I need to align on API contracts to validate assumptions.",
        "As a developer I need to finish the feature to deliver the MVP.",
    ]
    parsed = _parsed_data(descriptions)
    config = yaml.safe_load(Path("config/rules_config.yaml").read_text()) or {}
    result = check_description_canonicalization(
        parsed,
        {
            "backlog_keywords": ["backlog"],
            "in_progress_keywords": ["in progress"],
            "description_canonicalization": config.get("description_canonicalization", {}),
        },
    )
    assert result["eligible_count"] == len(descriptions)
    assert result["fail_count"] == 0


def test_description_canonicalization_flags_invalid():
    parsed = _parsed_data(["Just some notes without the required pattern."])
    result = check_description_canonicalization(
        parsed,
        {"backlog_keywords": ["backlog"], "in_progress_keywords": ["in progress"]},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_description_canonicalization_applies_to_any_list():
    parsed = _parsed_data(["Just some notes without the required pattern."], list_name="Done")
    result = check_description_canonicalization(
        parsed,
        {"description_canonicalization": {}},
    )
    assert result["eligible_count"] == 1
    assert result["fail_count"] == 1


def test_description_canonicalization_excludes_archived_and_missing_description():
    parsed = {
        "board": {"id": "b1", "name": "Board"},
        "lists": [{"id": "l1", "name": "Backlog", "closed": False}],
        "cards": [
            {"id": "c1", "name": "Archived", "list_id": "l1", "closed": True, "desc": "invalid format"},
            {"id": "c2", "name": "No Desc", "list_id": "l1", "closed": False, "desc": ""},
        ],
        "members": [],
        "checklists": [],
    }
    result = check_description_canonicalization(parsed, {"description_canonicalization": {}})
    assert result["eligible_count"] == 0
    assert result["fail_count"] == 0

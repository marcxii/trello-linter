from src.linter.scoring_engine import calculate_overall_score


def test_skipped_rule_when_no_eligible_items():
    results = calculate_overall_score(
        [
            {"rule_id": "card_ownership", "fail_count": 0, "eligible_count": 0, "passed": True},
        ]
    )
    rule_scores = results["rule_scores"]["card_ownership"]
    assert rule_scores["skipped"] is True
    assert rule_scores["eligible_count"] == 0
    assert results["total_failures"] == 0


def test_fail_percentage_and_counts():
    results = calculate_overall_score(
        [
            {"rule_id": "card_due_date", "fail_count": 1, "eligible_count": 4, "passed": False},
            {"rule_id": "card_ownership", "fail_count": 0, "eligible_count": 2, "passed": True},
        ]
    )
    assert results["total_failures"] == 1
    assert results["total_eligible"] == 6
    assert results["rules_failed"] == 1
    assert results["rules_passed"] == 1
    assert results["rule_scores"]["card_due_date"]["fail_percentage"] == 25.0


def test_overall_score_bounds():
    results = calculate_overall_score(
        [
            {"rule_id": "card_due_date", "fail_count": 100, "eligible_count": 100, "passed": False},
        ]
    )
    assert 0 <= results["overall_score"] <= 100


def test_deterministic_scoring():
    rule_results = [
        {"rule_id": "card_due_date", "fail_count": 2, "eligible_count": 4, "passed": False},
        {"rule_id": "card_ownership", "fail_count": 0, "eligible_count": 3, "passed": True},
    ]
    first = calculate_overall_score(rule_results)
    second = calculate_overall_score(rule_results)
    assert first == second

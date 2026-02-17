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


def test_effective_denominator_stabilizes_small_samples():
    rule_results = [
        {"rule_id": "card_due_date", "fail_count": 1, "eligible_count": 1, "passed": False},
    ]
    baseline = calculate_overall_score(
        rule_results,
        {"card_due_date": 1.0},
        {"effective_denominator": {"enabled": False, "n0": 20, "k": 1.0}},
    )
    stabilized = calculate_overall_score(
        rule_results,
        {"card_due_date": 1.0},
        {"effective_denominator": {"enabled": True, "n0": 20, "k": 1.0}},
    )
    assert baseline["overall_score"] == 0.0
    assert stabilized["overall_score"] == 95.0
    assert stabilized["rule_scores"]["card_due_date"]["effective_denominator"] == 20


def test_effective_denominator_k_controls_penalty_strength():
    rule_results = [
        {"rule_id": "card_due_date", "fail_count": 2, "eligible_count": 20, "passed": False},
    ]
    softer = calculate_overall_score(
        rule_results,
        {"card_due_date": 1.0},
        {"effective_denominator": {"enabled": True, "n0": 20, "k": 0.5}},
    )
    harsher = calculate_overall_score(
        rule_results,
        {"card_due_date": 1.0},
        {"effective_denominator": {"enabled": True, "n0": 20, "k": 2.0}},
    )
    assert softer["overall_score"] > harsher["overall_score"]


def test_weights_are_normalized_over_active_rules():
    rule_results = [
        {"rule_id": "r1", "fail_count": 0, "eligible_count": 10, "passed": True},
        {"rule_id": "r2", "fail_count": 10, "eligible_count": 10, "passed": False},
    ]
    scores = calculate_overall_score(
        rule_results,
        {"r1": 2.0, "r2": 1.0},
        {"effective_denominator": {"enabled": False, "n0": 0, "k": 1.0}},
    )
    # r1 score=100, r2 score=0, weighted avg with 2:1 => 66.67
    assert scores["overall_score"] == 66.67
    assert scores["rule_scores"]["r1"]["weight_normalized"] == 0.6667
    assert scores["rule_scores"]["r2"]["weight_normalized"] == 0.3333

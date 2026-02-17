"""Scoring engine for individual rule-based scoring.

This module calculates scores based on individual rule failures,
not category-based scoring. Each rule has its own weight.

Scoring Formula:
    Overall Score = weighted average of per-rule scores

Where:
    rule_penalty_percentage = (k × fail_count / max(eligible_count, N0)) × 100
    rule_score = max(0, 100 - rule_penalty_percentage)
    overall_score = Σ(weight_norm × rule_score), where
        weight_norm = rule_weight / Σ(active_rule_weights)
    If effective denominator is disabled, N0 is ignored and eligible_count is used.
    If eligible_count = 0, rule is skipped.
"""

from __future__ import annotations

from typing import Dict, List, Any


# Default rule weights (can be overridden via config)
DEFAULT_RULE_WEIGHTS = {
    "card_ownership": 1.0,               # Rule 1
    "card_due_date": 1.0,                # Rule 2
    "card_descriptiveness": 1.0,         # Rule 3
    "story_point_estimation": 1.0,       # Rule 4
    "past_due_violation": 1.0,           # Rule 5
    "progress_threshold": 1.0,           # Rule 6
    "progress_monitoring": 1.0,          # Rule 7
    "weekly_workload": 1.0,              # Rule 8 (deprecated)
    "individual_overload": 1.0,          # Rule 9 (deprecated)
    "near_term_overcommitment": 1.0,     # Rule 10 (deprecated)
    "unscheduled_work": 1.0,             # Rule 11 (deprecated)
    "flow_progress_signal": 1.0,         # Rule 12 (deprecated)
    "card_completion": 1.0,              # Rule 13
    "card_effort": 1.0,                  # Rule 14
    "description_canonicalization": 1.0, # Rule 15
}


def calculate_overall_score(
    rule_results: List[Dict[str, Any]],
    weights: Dict[str, float] = None,
    scoring_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Calculate overall score from individual rule results.
    
    Args:
        rule_results: List of rule result dictionaries, each containing:
            - rule_id: str (e.g., "card_ownership")
            - fail_count: int (number of failures)
            - eligible_count: int (number of eligible cards/items)
            - passed: bool (True if rule passed)
        weights: Optional custom weights per rule (defaults to DEFAULT_RULE_WEIGHTS)
        scoring_config: Optional scoring configuration from rules_config.yaml
        
    Returns:
        Dictionary containing:
            - overall_score: float (0-100)
            - rule_scores: dict mapping rule_id to individual score
            - total_failures: int
            - total_eligible: int
            - rules_passed: int
            - rules_failed: int
    """
    if weights is None:
        weights = DEFAULT_RULE_WEIGHTS.copy()

    ed_cfg = (scoring_config or {}).get("effective_denominator", {})
    ed_enabled = bool(ed_cfg.get("enabled", False))
    n0 = max(0, int(ed_cfg.get("n0", 0) or 0))
    k = float(ed_cfg.get("k", 1.0) or 1.0)
    
    weighted_score_sum = 0.0
    total_weight = 0.0
    rule_scores = {}
    total_failures = 0
    total_eligible = 0
    rules_passed = 0
    rules_failed = 0


    for result in rule_results:
        rule_id = result.get("rule_id")
        fail_count = result.get("fail_count", 0)
        eligible_count = result.get("eligible_count", 0)
        
        # Skip rules with no eligible items
        if eligible_count == 0:
            rule_scores[rule_id] = {
                "score": 100.0,
                "fail_count": 0,
                "eligible_count": 0,
                "fail_percentage": 0.0,
                "skipped": True
            }
            continue
        
        # Raw failure percentage for reporting
        fail_percentage = (fail_count / eligible_count) * 100

        # Effective denominator stabilization
        effective_denominator = max(eligible_count, n0) if ed_enabled else eligible_count
        penalty_percentage = (k * fail_count / effective_denominator) * 100
        penalty_percentage = max(0.0, min(100.0, penalty_percentage))
        
        # Get rule weight
        rule_weight = float(weights.get(rule_id, 1.0))
        rule_score = max(0.0, 100.0 - penalty_percentage)

        weighted_score_sum += rule_score * rule_weight
        total_weight += rule_weight
        total_failures += fail_count
        total_eligible += eligible_count
        
        # Track pass/fail
        if fail_count > 0:
            rules_failed += 1
        else:
            rules_passed += 1
        
        # Store individual rule score
        rule_scores[rule_id] = {
            "score": rule_score,
            "fail_count": fail_count,
            "eligible_count": eligible_count,
            "fail_percentage": round(fail_percentage, 2),
            "penalty_percentage": round(penalty_percentage, 2),
            "effective_denominator": effective_denominator,
            "weight": rule_weight,
            "skipped": False
        }
    
    # Calculate overall score as weighted average across active rules.
    if total_weight > 0:
        overall_score = weighted_score_sum / total_weight
    else:
        overall_score = 100.0
    
    if total_weight > 0:
        for rule_data in rule_scores.values():
            if rule_data.get("skipped"):
                continue
            rule_data["weight_normalized"] = round(rule_data.get("weight", 0.0) / total_weight, 4)

    return {
        "overall_score": round(overall_score, 2),
        "rule_scores": rule_scores,
        "total_failures": total_failures,
        "total_eligible": total_eligible,
        "rules_passed": rules_passed,
        "rules_failed": rules_failed,
        "total_rules": len(rule_results),
    }


def get_grade_from_score(score: float) -> Dict[str, str]:
    """Convert numeric score to letter grade.
    
    Args:
        score: Numeric score (0-100)
        
    Returns:
        Dictionary with grade and description
    """
    if score >= 90:
        return {"grade": "A", "description": "Excellent"}
    elif score >= 80:
        return {"grade": "B", "description": "Good"}
    elif score >= 70:
        return {"grade": "C", "description": "Needs Improvement"}
    elif score >= 60:
        return {"grade": "D", "description": "Poor"}
    else:
        return {"grade": "F", "description": "Critical Issues"}


def format_score_report(scoring_result: Dict[str, Any]) -> str:
    """Format scoring results as a readable text report.
    
    Args:
        scoring_result: Output from calculate_overall_score()
        
    Returns:
        Formatted string report
    """
    grade_info = get_grade_from_score(scoring_result["overall_score"])
    
    report = []
    report.append("=" * 60)
    report.append("TRELLO BOARD QUALITY SCORE")
    report.append("=" * 60)
    report.append(f"Overall Score: {scoring_result['overall_score']:.1f}/100")
    report.append(f"Grade: {grade_info['grade']} - {grade_info['description']}")
    report.append("")
    report.append(f"Rules Passed: {scoring_result['rules_passed']}/{scoring_result['total_rules']}")
    report.append(f"Rules Failed: {scoring_result['rules_failed']}/{scoring_result['total_rules']}")
    report.append(f"Total Failures: {scoring_result['total_failures']}")
    report.append("")
    report.append("Individual Rule Scores:")
    report.append("-" * 60)
    
    # Sort by score (worst first)
    sorted_rules = sorted(
        scoring_result["rule_scores"].items(),
        key=lambda x: x[1]["score"]
    )
    
    for rule_id, rule_data in sorted_rules:
        if rule_data.get("skipped"):
            continue
        
        status = "✓" if rule_data["fail_count"] == 0 else "✗"
        report.append(
            f"{status} {rule_id:30s} "
            f"Score: {rule_data['score']:5.1f} "
            f"({rule_data['fail_count']}/{rule_data['eligible_count']} failed)"
        )
    
    report.append("=" * 60)
    
    return "\n".join(report)


# Example usage and testing
if __name__ == "__main__":
    # Sample rule results
    sample_results = [
        {"rule_id": "card_ownership", "fail_count": 3, "eligible_count": 20},
        {"rule_id": "card_due_date", "fail_count": 5, "eligible_count": 20},
        {"rule_id": "past_due_violation", "fail_count": 2, "eligible_count": 15},
        {"rule_id": "progress_threshold", "fail_count": 0, "eligible_count": 8},
        {"rule_id": "card_descriptiveness", "fail_count": 1, "eligible_count": 25},
    ]
    
    # Calculate score
    result = calculate_overall_score(sample_results)
    
    # Print report
    print(format_score_report(result))
    print("\nDetailed Results:")
    print(f"Overall Score: {result['overall_score']}")
    print(f"Rules Passed: {result['rules_passed']}")
    print(f"Rules Failed: {result['rules_failed']}")

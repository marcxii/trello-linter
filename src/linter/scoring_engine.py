"""Scoring engine for individual rule-based scoring.

This module calculates scores based on individual rule failures,
not category-based scoring. Each rule has its own weight.

Scoring Formula:
    Overall Score = 100 - Σ(rule_weight × fail_percentage)
    
Where:
    fail_percentage = (fail_count / eligible_count) × 100
    If eligible_count = 0, rule is skipped
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


def calculate_overall_score(rule_results: List[Dict[str, Any]], weights: Dict[str, float] = None) -> Dict[str, Any]:
    """Calculate overall score from individual rule results.
    
    Args:
        rule_results: List of rule result dictionaries, each containing:
            - rule_id: str (e.g., "card_ownership")
            - fail_count: int (number of failures)
            - eligible_count: int (number of eligible cards/items)
            - passed: bool (True if rule passed)
        weights: Optional custom weights per rule (defaults to DEFAULT_RULE_WEIGHTS)
        
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
    
    total_penalty = 0.0
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
        
        # Calculate failure percentage
        fail_percentage = (fail_count / eligible_count) * 100
        
        # Get rule weight
        rule_weight = weights.get(rule_id, 5.0)  # Default weight if not found
        
        # Calculate penalty (fail_percentage * weight / 100)
        # This normalizes the weight contribution
        penalty = (fail_percentage * rule_weight) / 100
        
        total_penalty += penalty
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
            "score": max(0, 100 - fail_percentage),
            "fail_count": fail_count,
            "eligible_count": eligible_count,
            "fail_percentage": round(fail_percentage, 2),
            "weight": rule_weight,
            "skipped": False
        }
    
    # Calculate overall score
    # Start at 100, subtract weighted penalties
    overall_score = max(0, min(100, 100 - total_penalty))
    
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

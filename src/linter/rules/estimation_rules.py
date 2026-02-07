"""Estimation Rules - Rules 3, 4, 14, 15

Covers:
- Rule 3: Card Descriptiveness
- Rule 4: Story Point Estimation Coverage
- Rule 14: Card Effort
- Rule 15: Description Canonicalization
"""

from __future__ import annotations

import re
from typing import Dict, List, Any, Optional


def extract_story_points(description: str, patterns: List[str]) -> Optional[int]:
    """Extract story points from card description using regex patterns.
    
    Args:
        description: Card description text
        patterns: List of regex patterns to match
        
    Returns:
        Story points as integer, or None if not found
    """
    if not description:
        return None
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    
    return None


def check_card_descriptiveness(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 3: Card has a description length of ≥ 20 characters.
    
    Eligibility: Cards in (BACKLOG, IN_PROGRESS) AND closed=false
    Fail Condition: len(card.desc).strip() < MINIMUM_DESC_CHAR
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    minimum_desc_char = config.get("card_descriptiveness", {}).get("minimum_desc_char", 20)
    backlog_keywords = config.get("backlog_keywords", ["backlog", "to do"])
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find eligible list IDs (Backlog or In Progress)
    eligible_list_ids = []
    for list_id, name in list_map.items():
        is_backlog = any(keyword in name for keyword in backlog_keywords)
        is_in_progress = any(keyword in name for keyword in in_progress_keywords)
        if is_backlog or is_in_progress:
            eligible_list_ids.append(list_id)
    
    # Filter eligible cards
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in eligible_list_ids
        and not card.get("closed", False)
    ]
    
    # Check for failures
    failures = []
    for card in eligible_cards:
        desc = (card.get("desc") or "").strip()
        if len(desc) < minimum_desc_char:
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": f"Description too short ({len(desc)} chars, minimum {minimum_desc_char})",
                "current_length": len(desc)
            })
    
    return {
        "rule_id": "card_descriptiveness",
        "rule_name": "Card Descriptiveness",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_story_point_estimation(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 4: Story points present in description.
    
    Eligibility: Cards in IN_PROGRESS AND closed=false
    Fail Condition: Cannot parse story points from description
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    sp_patterns = config.get("story_point_estimation", {}).get("sp_regex_patterns", [
        r"Story Point[s]?:\s*(\d+)",
        r"SP:\s*(\d+)",
        r"Effort:\s*(\d+)",
        r"Estimation:\s*(\d+)"
    ])
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find IN_PROGRESS list IDs
    in_progress_list_ids = [
        list_id for list_id, name in list_map.items()
        if any(keyword in name for keyword in in_progress_keywords)
    ]
    
    # Filter eligible cards
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in in_progress_list_ids
        and not card.get("closed", False)
    ]
    
    # Check for failures
    failures = []
    for card in eligible_cards:
        desc = card.get("desc", "")
        story_points = extract_story_points(desc, sp_patterns)
        
        if story_points is None:
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": "No story points found in description"
            })
    
    return {
        "rule_id": "story_point_estimation",
        "rule_name": "Story Point Estimation Coverage",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_card_effort(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 14: Card has effort/hours estimation.
    
    Eligibility: Cards in IN_PROGRESS AND closed=true
    Fail Condition: Cannot parse effort hours from description
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    effort_patterns = config.get("card_effort", {}).get("effort_regex_patterns", [
        r"Effort:\s*(\d+)",
        r"Hours:\s*(\d+)"
    ])
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find IN_PROGRESS list IDs
    in_progress_list_ids = [
        list_id for list_id, name in list_map.items()
        if any(keyword in name for keyword in in_progress_keywords)
    ]
    
    # Filter eligible cards (in progress AND closed)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in in_progress_list_ids
        and card.get("closed", False) == True
    ]
    
    # Check for failures
    failures = []
    for card in eligible_cards:
        desc = card.get("desc", "")
        effort_hours = extract_story_points(desc, effort_patterns)  # Reuse same extraction logic
        
        if effort_hours is None:
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": "No effort hours found in description"
            })
    
    return {
        "rule_id": "card_effort",
        "rule_name": "Card Effort",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_description_canonicalization(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 15: Card description follows standard format.
    
    Eligibility: All cards with descriptions
    Fail Condition: Description doesn't match any canonical format
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    story_formats = config.get("description_canonicalization", {}).get("story_formats", [
        r"As a .+, I want .+",
        r"Given .+, [Ww]hen .+, [Tt]hen .+"
    ])
    backlog_keywords = config.get("backlog_keywords", ["backlog", "to do"])
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find eligible list IDs (Backlog or In Progress)
    eligible_list_ids = []
    for list_id, name in list_map.items():
        is_backlog = any(keyword in name for keyword in backlog_keywords)
        is_in_progress = any(keyword in name for keyword in in_progress_keywords)
        if is_backlog or is_in_progress:
            eligible_list_ids.append(list_id)
    
    # Filter eligible cards (cards with descriptions in eligible lists)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in eligible_list_ids
        and not card.get("closed", False)
        and card.get("desc")  # Has description
    ]
    
    # Check for failures
    failures = []
    for card in eligible_cards:
        desc = card.get("desc", "")
        
        # Check if description matches any canonical format
        matches_format = any(
            re.search(pattern, desc, re.IGNORECASE | re.DOTALL)
            for pattern in story_formats
        )
        
        if not matches_format:
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": "Description doesn't follow canonical format (As a.../Given-When-Then)"
            })
    
    return {
        "rule_id": "description_canonicalization",
        "rule_name": "Description Canonicalization",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def run_all_estimation_rules(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Run all estimation-related rules.
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Configuration dictionary from rules_config.yaml
        
    Returns:
        List of rule results
    """
    if config is None:
        config = {}
    
    # Extract list keywords from config
    list_config = {
        "backlog_keywords": config.get("lists", {}).get("backlog_keywords", ["backlog", "to do"]),
        "in_progress_keywords": config.get("lists", {}).get("in_progress_keywords", ["in progress", "doing"]),
        "done_keywords": config.get("lists", {}).get("done_keywords", ["done", "complete"]),
    }
    
    # Merge with specific rule configs
    merged_config = {**config, **list_config}
    
    results = []
    
    # Rule 3: Card Descriptiveness
    if config.get("card_descriptiveness", {}).get("enabled", True):
        results.append(check_card_descriptiveness(parsed_data, merged_config))
    
    # Rule 4: Story Point Estimation
    if config.get("story_point_estimation", {}).get("enabled", True):
        results.append(check_story_point_estimation(parsed_data, merged_config))
    
    # Rule 14: Card Effort
    if config.get("card_effort", {}).get("enabled", False):  # Disabled by default per spec
        results.append(check_card_effort(parsed_data, merged_config))
    
    # Rule 15: Description Canonicalization
    if config.get("description_canonicalization", {}).get("enabled", True):
        results.append(check_description_canonicalization(parsed_data, merged_config))
    
    return results


# Testing
if __name__ == "__main__":
    # Sample test data
    test_data = {
        "lists": [
            {"id": "list1", "name": "Backlog"},
            {"id": "list2", "name": "In Progress"},
            {"id": "list3", "name": "Done"}
        ],
        "cards": [
            {
                "id": "card1",
                "name": "Short desc",
                "list_id": "list2",
                "closed": False,
                "desc": "Too short",  # FAIL Rule 3 (< 20 chars)
                "members": ["user1"]
            },
            {
                "id": "card2",
                "name": "No story points",
                "list_id": "list2",
                "closed": False,
                "desc": "As a user, I want to login so that I can access my account",  # FAIL Rule 4 (no SP)
                "members": ["user1"]
            },
            {
                "id": "card3",
                "name": "Good card",
                "list_id": "list2",
                "closed": False,
                "desc": "As a user, I want to reset password. Story Point: 5",  # PASS all
                "members": ["user1"]
            },
            {
                "id": "card4",
                "name": "Bad format",
                "list_id": "list1",
                "closed": False,
                "desc": "Just implement the feature without proper story format",  # FAIL Rule 15
                "members": []
            }
        ]
    }
    
    results = run_all_estimation_rules(test_data)
    
    for result in results:
        print(f"\n{result['rule_name']}:")
        print(f"  Failed: {result['fail_count']}/{result['eligible_count']}")
        print(f"  Passed: {result['passed']}")
        if result['failures']:
            print("  Failures:")
            for failure in result['failures'][:3]:  # Show first 3
                print(f"    - {failure['card_name']}: {failure['reason']}")
"""Estimation rules.

Covers:
- card_descriptiveness
- story_point_estimation
- card_effort
- description_canonicalization
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
                return int(float(match.group(1)))
            except (ValueError, IndexError):
                continue
    
    return None


def check_card_descriptiveness(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """card_descriptiveness: Card has a description length of ≥ 20 characters.
    
    Eligibility: Cards in any list (open or closed)
    Fail Condition: len(card.desc).strip() < MINIMUM_DESC_CHAR
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    minimum_desc_char = config.get("card_descriptiveness", {}).get("minimum_desc_char", 20)
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}

    # Filter eligible cards (any list, open or closed)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in list_map
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
    """story_point_estimation: Story points present in description.
    
    Eligibility: Cards in any list (open or closed)
    Fail Condition: Cannot parse story points from description
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    rule_cfg = config.get("story_point_estimation", {})
    sp_patterns = rule_cfg.get("sp_regex_patterns", [
        r"\bStory[\s_-]*Point[s]?\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\bSP\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\bPts?\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\bPoints?\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\bPoint[\s_-]*Value\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\bSize\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
    ])
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}

    # Filter eligible cards (any list, open or closed)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in list_map
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
                "reason": "Missing story point estimate in description"
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
    """card_effort: Card has effort/hours estimation.
    
    Eligibility: Cards in any list (open or closed)
    Fail Condition: Cannot parse effort hours from description
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    effort_patterns = config.get("card_effort", {}).get("effort_regex_patterns", [
        r"\bEffort(?:[\s_-]*(?:Hours?|Minutes?))?\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?|m|min|mins|minutes?)?",
        r"\b(?:Estimate|Estimation|Estimated[\s_-]*Hours?|Estimated[\s_-]*Time|Time[\s_-]*Estimate|Est)\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?|m|min|mins|minutes?)?",
        r"\bHours?\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\bMinutes?\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
        r"\b(?:Dev|Engineering)[\s_-]*Effort\b\s*(?::|=|-|is)?\s*(\d+(?:\.\d+)?)",
    ])
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}

    # Filter eligible cards (any list, open or closed)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in list_map
        and not card.get("closed", False)
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
    """description_canonicalization: Card description follows standard format.
    
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
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}

    # Filter eligible cards (cards with descriptions in any list, open or closed)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in list_map
        and card.get("desc")  # Has description
        and not card.get("closed", False)
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
    
    # rule_id: card_descriptiveness
    if config.get("card_descriptiveness", {}).get("enabled", True):
        results.append(check_card_descriptiveness(parsed_data, merged_config))
    
    # rule_id: story_point_estimation
    if config.get("story_point_estimation", {}).get("enabled", True):
        results.append(check_story_point_estimation(parsed_data, merged_config))
    
    # rule_id: card_effort
    if config.get("card_effort", {}).get("enabled", False):  # Disabled by default per spec
        results.append(check_card_effort(parsed_data, merged_config))
    
    # rule_id: description_canonicalization
    if config.get("description_canonicalization", {}).get("enabled", True):
        results.append(check_description_canonicalization(parsed_data, merged_config))
    
    return results

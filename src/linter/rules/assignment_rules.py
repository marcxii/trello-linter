"""Assignment Rules - Rules 1, 2, 11, 13

Covers:
- Rule 1: Card Ownership
- Rule 2: Card Due Date
- Rule 13: Card Completion
"""

from __future__ import annotations

from typing import Dict, List, Any
from datetime import datetime, timezone


def check_card_ownership(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 1: Card has at least one member assigned.
    
    Eligibility: Cards in all non-BACKLOG lists (open or closed)
    Fail Condition: count(card.idMembers) < 1
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    backlog_keywords = config.get("backlog_keywords", ["backlog", "to do"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find non-BACKLOG list IDs
    non_backlog_list_ids = [
        list_id for list_id, name in list_map.items()
        if not any(keyword in name for keyword in backlog_keywords)
    ]
    
    # Filter eligible cards
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in non_backlog_list_ids
        and card.get("closed") == False
       
    ]
    
    # Check for failures
    failures = []
    for card in eligible_cards:
        members = card.get("members", [])
        if len(members) < 1:
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": "No member assigned"
            })
    
    return {
        "rule_id": "card_ownership",
        "rule_name": "Card Ownership",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_card_due_date(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 2: Card has a due date present.
    
    Eligibility: Cards in IN_PROGRESS lists AND closed=false
    Fail Condition: card.due = null
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing", "development"])
    
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
        and card.get("closed") == False #dont evaulate of archived cards
    ]
    
    # Check for failures
    failures = []
    for card in eligible_cards:
        due_date = card.get("due")
        if due_date is None or due_date == "":
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": "No due date set"
            })
    
    return {
        "rule_id": "card_due_date",
        "rule_name": "Card Due Date",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_card_completion(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 13: Complete Card is NOT in a 'Done' List.
    
    Eligibility: Cards where List in (BACKLOG, IN_PROGRESS) AND closed=true
    Fail Condition: Card is marked closed but not in a Done list
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    done_keywords = config.get("done_keywords", ["done", "complete", "deploy"])
    backlog_keywords = config.get("backlog_keywords", ["backlog", "to do"])
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing", "development"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find non-Done list IDs
    non_done_list_ids = []
    for list_id, name in list_map.items():
        is_done = any(keyword in name for keyword in done_keywords)
        if not is_done:
            non_done_list_ids.append(list_id)
        
    
    # Filter eligible cards (closed but in non-Done lists)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if not card.get("closed", False) #not archived cards
        and card.get("list_id") in non_done_list_ids
        and not card.get("dueComplete",True)
    ]
    
    # All eligible cards are failures (closed cards should be in Done)
    failures = []
    for card in eligible_cards:
        failures.append({
            "card_id": card.get("id"),
            "card_name": card.get("name"),
            "list_name": list_map.get(card.get("list_id"), "Unknown"),
            "reason": "Card closed but not in Done list"
        })
    
    return {
        "rule_id": "card_completion",
        "rule_name": "Card Completion",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def run_all_assignment_rules(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Run all assignment-related rules.
    
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
    
    results = []
    
    # Rule 1: Card Ownership
    if config.get("card_ownership", {}).get("enabled", True):
        results.append(check_card_ownership(parsed_data, list_config))
    
    # Rule 2: Card Due Date
    if config.get("card_due_date", {}).get("enabled", True):
        results.append(check_card_due_date(parsed_data, list_config))
    
    # Rule 13: Card Completion
    if config.get("card_completion", {}).get("enabled", True):
        results.append(check_card_completion(parsed_data, list_config))
    
    return results

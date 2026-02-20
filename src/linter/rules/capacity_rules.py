"""Capacity rules.

Covers:
- past_due_violation
- progress_threshold
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


def check_past_due_violation(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """past_due_violation: Past-due active work.
    
    Eligibility: Cards where due != null AND closed=false
    Fail Condition: due < now AND dueComplete != true
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    # Build list map
    list_map = {lst["id"]: lst["name"] for lst in parsed_data.get("lists", [])}
    
    # Filter eligible cards (has due date, not closed)
    eligible_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("due") is not None
        and card.get("due") != ""
        and not card.get("closed", False)
    ]
    
    # Check for failures (past due)
    now = datetime.now(timezone.utc)
    failures = []
    
    for card in eligible_cards:
        due_str = card.get("due")
        
        try:
            # Parse ISO 8601 datetime
            due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            
            # Check if past due and not marked complete
            # Note: dueComplete is not always in export, default to False
            due_complete = card.get("dueComplete", False)
            
            if due_date < now and not due_complete:
                days_overdue = (now - due_date).days
                failures.append({
                    "card_id": card.get("id"),
                    "card_name": card.get("name"),
                    "list_name": list_map.get(card.get("list_id"), "Unknown"),
                    "reason": f"Past due by {days_overdue} days",
                    "due_date": due_str,
                    "days_overdue": days_overdue
                })
        except (ValueError, AttributeError):
            # Invalid date format - skip
            continue
    
    return {
        "rule_id": "past_due_violation",
        "rule_name": "Past Due Violation",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_progress_threshold(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """progress_threshold: WIP per person threshold.
    
    Eligibility: Cards in IN_PROGRESS AND closed=false
    Fail Condition: count(cards.in_progress) grouped by memberID > MAX_WIP_PER_MEMBER
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    max_wip = config.get("progress_threshold", {}).get("max_wip_per_member", 3)
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    
    # Build list and member maps
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    member_map = {m["id"]: m.get("fullName", m.get("username", "Unknown")) 
                  for m in parsed_data.get("members", [])}
    
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
    
    # Group cards by member
    member_wip = defaultdict(list)
    for card in eligible_cards:
        members = card.get("members", [])
        for member_id in members:
            member_wip[member_id].append(card)
    
    # Build card-level failures by member so display can group by member while
    # preserving original scoring semantics (member-based fail/eligible counts).
    failures = []
    member_failures = []
    members_over_threshold = 0
    for member_id, cards in member_wip.items():
        if len(cards) <= max_wip:
            continue
        members_over_threshold += 1
        member_name = member_map.get(member_id, member_id)
        member_failures.append(
            {
                "member_id": member_id,
                "member_name": member_name,
                "wip_count": len(cards),
                "threshold": max_wip,
                "card_names": [c.get("name") for c in cards if c.get("name")],
                "card_ids": [c.get("id") for c in cards if c.get("id")],
            }
        )
        for card in cards:
            card_id = card.get("id")
            if not card_id:
                continue
            failures.append(
                {
                    "card_id": card_id,
                    "card_name": card.get("name"),
                    "list_name": list_map.get(card.get("list_id"), "Unknown"),
                    "member_id": member_id,
                    "member_name": member_name,
                    "wip_count": len(cards),
                    "threshold": max_wip,
                    "reason": f"{member_name} has {len(cards)} cards in progress (max: {max_wip})",
                }
            )
    
    return {
        "rule_id": "progress_threshold",
        "rule_name": "Progress Threshold (WIP per person)",
        "fail_count": members_over_threshold,
        "eligible_count": len(member_wip),  # Count of members with WIP
        "passed": len(failures) == 0,
        "failures": failures,
        "member_failures": member_failures,
    }


def run_all_capacity_rules(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Run all capacity-related rules.
    
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
        "in_progress_keywords": config.get("lists", {}).get("in_progress_keywords", ["in progress", "doing"]),
    }
    
    # Merge configs
    merged_config = {**config, **list_config}
    
    results = []
    
    # rule_id: past_due_violation
    if config.get("past_due_violation", {}).get("enabled", True):
        results.append(check_past_due_violation(parsed_data, merged_config))
    
    # rule_id: progress_threshold
    if config.get("progress_threshold", {}).get("enabled", True):
        results.append(check_progress_threshold(parsed_data, merged_config))
    

    return results

"""Capacity Rules - Rules 5, 6, 8, 9, 10

Covers:
- Rule 5: Past Due Violation
- Rule 6: Progress Threshold (WIP per person)
- Rule 8: Weekly Workload
- Rule 9: Individual Overload
- Rule 10: Near-term Overcommitment
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


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


def check_past_due_violation(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 5: Past-due active work.
    
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
    """Rule 6: WIP per person threshold.
    
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
    
    # Check for failures (members exceeding threshold)
    failures = []
    for member_id, cards in member_wip.items():
        if len(cards) > max_wip:
            member_name = member_map.get(member_id, member_id)
            failures.append({
                "member_id": member_id,
                "member_name": member_name,
                "wip_count": len(cards),
                "threshold": max_wip,
                "reason": f"{member_name} has {len(cards)} cards in progress (max: {max_wip})",
                "card_names": [c.get("name") for c in cards[:5]]  # First 5 cards
            })
    
    return {
        "rule_id": "progress_threshold",
        "rule_name": "Progress Threshold (WIP per person)",
        "fail_count": len(failures),
        "eligible_count": len(member_wip),  # Count of members with WIP
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_weekly_workload(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 8: Weekly workload (SP by due date).
    
    Eligibility: Cards in IN_PROGRESS with due dates and story points
    Fail Condition: Sum of story points per week > WEEKLY_SP_THRESHOLD
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    weekly_threshold = config.get("weekly_workload", {}).get("weekly_sp_threshold", 20)
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    sp_patterns = config.get("story_point_estimation", {}).get("sp_regex_patterns", [
        r"Story Point[s]?:\s*(\d+)",
        r"SP:\s*(\d+)"
    ])
    
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
        and card.get("due") is not None
        and card.get("desc")
    ]
    
    # Group story points by week
    weekly_sp = defaultdict(int)
    cards_by_week = defaultdict(list)
    
    for card in eligible_cards:
        due_str = card.get("due")
        desc = card.get("desc", "")
        sp = extract_story_points(desc, sp_patterns)
        
        if sp is None:
            continue
        
        try:
            due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            # Get week number (ISO week)
            week_key = f"{due_date.year}-W{due_date.isocalendar()[1]}"
            weekly_sp[week_key] += sp
            cards_by_week[week_key].append(card)
        except (ValueError, AttributeError):
            continue
    
    # Check for failures
    failures = []
    for week_key, total_sp in weekly_sp.items():
        if total_sp > weekly_threshold:
            failures.append({
                "week": week_key,
                "total_sp": total_sp,
                "threshold": weekly_threshold,
                "reason": f"Week {week_key} has {total_sp} SP (max: {weekly_threshold})",
                "card_count": len(cards_by_week[week_key])
            })
    
    return {
        "rule_id": "weekly_workload",
        "rule_name": "Weekly Workload",
        "fail_count": len(failures),
        "eligible_count": len(weekly_sp),  # Number of weeks with work
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_individual_overload(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 9: Individual overload (>45 SP per person).
    
    Eligibility: Cards in IN_PROGRESS with story points and members
    Fail Condition: Sum of story points per member > INDIVIDUAL_SP_THRESHOLD
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    individual_threshold = config.get("individual_overload", {}).get("individual_sp_threshold", 45)
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    sp_patterns = config.get("story_point_estimation", {}).get("sp_regex_patterns", [
        r"Story Point[s]?:\s*(\d+)",
        r"SP:\s*(\d+)"
    ])
    
    # Build maps
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
        and card.get("desc")
        and len(card.get("members", [])) > 0
    ]
    
    # Sum story points per member
    member_sp = defaultdict(int)
    member_cards = defaultdict(list)
    
    for card in eligible_cards:
        desc = card.get("desc", "")
        sp = extract_story_points(desc, sp_patterns)
        
        if sp is None:
            continue
        
        members = card.get("members", [])
        for member_id in members:
            member_sp[member_id] += sp
            member_cards[member_id].append(card)
    
    # Check for failures
    failures = []
    for member_id, total_sp in member_sp.items():
        if total_sp > individual_threshold:
            member_name = member_map.get(member_id, member_id)
            failures.append({
                "member_id": member_id,
                "member_name": member_name,
                "total_sp": total_sp,
                "threshold": individual_threshold,
                "reason": f"{member_name} has {total_sp} SP (max: {individual_threshold})",
                "card_count": len(member_cards[member_id])
            })
    
    return {
        "rule_id": "individual_overload",
        "rule_name": "Individual Overload",
        "fail_count": len(failures),
        "eligible_count": len(member_sp),  # Number of members with assigned SP
        "passed": len(failures) == 0,
        "failures": failures
    }


def check_near_term_overcommitment(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 10: Near-term overcommitment.
    
    Eligibility: Cards in IN_PROGRESS with due dates within WINDOW_DAYS
    Fail Condition: Sum of story points in window > WINDOW_SP_THRESHOLD
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    window_days = config.get("near_term_overcommitment", {}).get("window_days", 5)
    window_threshold = config.get("near_term_overcommitment", {}).get("window_sp_threshold", 30)
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    sp_patterns = config.get("story_point_estimation", {}).get("sp_regex_patterns", [
        r"Story Point[s]?:\s*(\d+)",
        r"SP:\s*(\d+)"
    ])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find IN_PROGRESS list IDs
    in_progress_list_ids = [
        list_id for list_id, name in list_map.items()
        if any(keyword in name for keyword in in_progress_keywords)
    ]
    
    # Calculate window
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=window_days)
    
    # Filter eligible cards (in progress, due within window)
    eligible_cards = []
    for card in parsed_data.get("cards", []):
        if (card.get("list_id") not in in_progress_list_ids
            or card.get("closed", False)
            or not card.get("due")
            or not card.get("desc")):
            continue
        
        due_str = card.get("due")
        try:
            due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            if now <= due_date <= window_end:
                eligible_cards.append(card)
        except (ValueError, AttributeError):
            continue
    
    # Sum story points in window
    total_sp = 0
    cards_in_window = []
    
    for card in eligible_cards:
        desc = card.get("desc", "")
        sp = extract_story_points(desc, sp_patterns)
        
        if sp is not None:
            total_sp += sp
            cards_in_window.append(card)
    
    # Check for failure
    failures = []
    if total_sp > window_threshold:
        failures.append({
            "window_days": window_days,
            "total_sp": total_sp,
            "threshold": window_threshold,
            "reason": f"Next {window_days} days has {total_sp} SP (max: {window_threshold})",
            "card_count": len(cards_in_window)
        })
    
    return {
        "rule_id": "near_term_overcommitment",
        "rule_name": "Near-term Overcommitment",
        "fail_count": len(failures),
        "eligible_count": 1 if eligible_cards else 0,  # Boolean-style: 0 or 1
        "passed": len(failures) == 0,
        "failures": failures
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
    
    # Rule 5: Past Due Violation
    if config.get("past_due_violation", {}).get("enabled", True):
        results.append(check_past_due_violation(parsed_data, merged_config))
    
    # Rule 6: Progress Threshold
    if config.get("progress_threshold", {}).get("enabled", True):
        results.append(check_progress_threshold(parsed_data, merged_config))
    
    # Rule 8: Weekly Workload
    if config.get("weekly_workload", {}).get("enabled", True):
        results.append(check_weekly_workload(parsed_data, merged_config))
    
    # Rule 9: Individual Overload
    if config.get("individual_overload", {}).get("enabled", True):
        results.append(check_individual_overload(parsed_data, merged_config))
    
    # Rule 10: Near-term Overcommitment
    if config.get("near_term_overcommitment", {}).get("enabled", True):
        results.append(check_near_term_overcommitment(parsed_data, merged_config))
    
    return results
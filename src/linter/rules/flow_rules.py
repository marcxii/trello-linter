"""Flow Rules - Rules 7, 12

Covers:
- Rule 7: Progress Monitoring (Stale work)
- Rule 12: Flow Progress Signal

Note: These rules require card action/movement data that may not be
available in standard Trello JSON exports. Placeholder logic is provided.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional


def get_last_activity_date(card: Dict[str, Any]) -> Optional[datetime]:
    """Extract last activity date from card.
    
    Tries multiple sources:
    1. card.dateLastActivity (if available)
    2. Most recent action date from card.actions
    3. None if unavailable
    
    Args:
        card: Card dictionary
        
    Returns:
        Last activity datetime or None
    """
    # Try dateLastActivity field
    if card.get("dateLastActivity"):
        try:
            return datetime.fromisoformat(card["dateLastActivity"].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    # Try actions array
    actions = card.get("actions", [])
    if actions and isinstance(actions, list):
        try:
            # Actions are usually sorted newest first
            latest_action = actions[0]
            date_str = latest_action.get("date")
            if date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError, IndexError):
            pass
    
    return None


def get_moved_to_in_progress_date(card: Dict[str, Any]) -> Optional[datetime]:
    """Extract date when card was moved to In Progress list.
    
    Searches card.actions for updateCard action that changed idList.
    This data may not be available in all Trello exports.
    
    Args:
        card: Card dictionary
        
    Returns:
        Movement datetime or None
    """
    actions = card.get("actions", [])
    if not actions:
        return None
    
    # Search actions for list movement
    for action in actions:
        if action.get("type") == "updateCard":
            data = action.get("data", {})
            list_after = data.get("listAfter", {})
            list_before = data.get("listBefore", {})
            
            # Check if moved to In Progress
            if list_after.get("name"):
                list_name = list_after.get("name", "").lower()
                if any(kw in list_name for kw in ["in progress", "doing", "development"]):
                    date_str = action.get("date")
                    if date_str:
                        try:
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            continue
    
    return None


def check_progress_monitoring(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 7: Progress Monitoring - Stale In-Progress work.
    
    Eligibility: Cards in IN_PROGRESS AND closed=false
    Fail Condition: (now - card.moved_to_in_progress) >= THRESHOLD_DAYS
                    AND (now - card.last_activity) >= THRESHOLD_DAYS
    
    Note: Requires action history data. If unavailable, uses placeholder logic.
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    threshold_days = config.get("progress_monitoring", {}).get("threshold_num_days", 5)
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
    
    now = datetime.now(timezone.utc)
    threshold_delta = timedelta(days=threshold_days)
    failures = []
    
    for card in eligible_cards:
        # Try to get movement and activity dates
        moved_date = get_moved_to_in_progress_date(card)
        last_activity = get_last_activity_date(card)
        
        # PLACEHOLDER LOGIC if dates not available:
        # If we can't determine dates, we skip this card
        # In production, you might want to fail-safe differently
        if not moved_date and not last_activity:
            # No date information available - skip
            continue
        
        # Check staleness
        is_stale_by_movement = False
        is_stale_by_activity = False
        
        if moved_date:
            days_in_progress = (now - moved_date).days
            is_stale_by_movement = days_in_progress >= threshold_days
        
        if last_activity:
            days_since_activity = (now - last_activity).days
            is_stale_by_activity = days_since_activity >= threshold_days
        
        # Fail if BOTH conditions met (or if only one is available and stale)
        if (moved_date and last_activity and is_stale_by_movement and is_stale_by_activity) or \
           (moved_date and not last_activity and is_stale_by_movement) or \
           (last_activity and not moved_date and is_stale_by_activity):
            
            days_stale = max(
                (now - moved_date).days if moved_date else 0,
                (now - last_activity).days if last_activity else 0
            )
            
            failures.append({
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "list_name": list_map.get(card.get("list_id"), "Unknown"),
                "reason": f"Stale for {days_stale} days (threshold: {threshold_days})",
                "days_stale": days_stale,
                "last_activity": last_activity.isoformat() if last_activity else "Unknown"
            })
    
    return {
        "rule_id": "progress_monitoring",
        "rule_name": "Progress Monitoring (Stale Work)",
        "fail_count": len(failures),
        "eligible_count": len(eligible_cards),
        "passed": len(failures) == 0,
        "failures": failures,
        "note": "Requires card action history. Some cards may be skipped if data unavailable."
    }


def get_completion_date(card: Dict[str, Any]) -> Optional[datetime]:
    """Extract completion date from card.
    
    Tries multiple sources:
    1. Look for action where card was moved to Done list
    2. Look for action where card was closed
    3. Use dateLastActivity if card is closed
    
    Args:
        card: Card dictionary
        
    Returns:
        Completion datetime or None
    """
    if not card.get("closed", False):
        return None
    
    actions = card.get("actions", [])
    if not actions:
        # Fallback: use dateLastActivity if closed
        if card.get("dateLastActivity"):
            try:
                return datetime.fromisoformat(card["dateLastActivity"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        return None
    
    # Search for completion action
    for action in actions:
        action_type = action.get("type")
        
        # Check if moved to Done list
        if action_type == "updateCard":
            data = action.get("data", {})
            list_after = data.get("listAfter", {})
            list_name = list_after.get("name", "").lower()
            
            if any(kw in list_name for kw in ["done", "complete", "deploy"]):
                date_str = action.get("date")
                if date_str:
                    try:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        continue
        
        # Check if card was closed
        if action_type == "updateCard":
            data = action.get("data", {})
            card_data = data.get("card", {})
            if card_data.get("closed") == True:
                date_str = action.get("date")
                if date_str:
                    try:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        continue
    
    return None


def check_flow_progress_signal(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rule 12: Flow Progress Signal.
    
    Measures whether work is flowing by comparing recent completions to WIP.
    
    Eligibility: Board-level check (not per-card)
    Fail Condition: flow_ratio = completed_recent / wip < MIN_FLOW_RATIO
    
    Note: Requires completion date data. Uses placeholder logic if unavailable.
    
    Args:
        parsed_data: Full board data from parse_full_board()
        config: Rule configuration
        
    Returns:
        Dictionary with rule_id, fail_count, eligible_count, failures list
    """
    lookback_days = config.get("flow_progress_signal", {}).get("lookback_days", 5)
    min_flow_ratio = config.get("flow_progress_signal", {}).get("min_flow_ratio", 0.20)
    in_progress_keywords = config.get("in_progress_keywords", ["in progress", "doing"])
    
    # Build list map
    list_map = {lst["id"]: lst["name"].lower() for lst in parsed_data.get("lists", [])}
    
    # Find IN_PROGRESS list IDs
    in_progress_list_ids = [
        list_id for list_id, name in list_map.items()
        if any(keyword in name for keyword in in_progress_keywords)
    ]
    
    # Count current WIP
    wip_cards = [
        card for card in parsed_data.get("cards", [])
        if card.get("list_id") in in_progress_list_ids
        and not card.get("closed", False)
    ]
    wip_count = len(wip_cards)
    
    # Count recent completions
    now = datetime.now(timezone.utc)
    lookback_date = now - timedelta(days=lookback_days)
    
    recent_completions = []
    for card in parsed_data.get("cards", []):
        if not card.get("closed", False):
            continue
        
        completion_date = get_completion_date(card)
        if completion_date and completion_date >= lookback_date:
            recent_completions.append(card)
    
    completed_count = len(recent_completions)
    
    # Calculate flow ratio
    if wip_count == 0:
        # No WIP - perfect flow (or no work)
        flow_ratio = 1.0
    else:
        flow_ratio = completed_count / wip_count
    
    # Check for failure
    failures = []
    if flow_ratio < min_flow_ratio:
        failures.append({
            "flow_ratio": round(flow_ratio, 2),
            "min_flow_ratio": min_flow_ratio,
            "wip_count": wip_count,
            "completed_recent": completed_count,
            "lookback_days": lookback_days,
            "reason": f"Low flow: {completed_count} completed vs {wip_count} WIP (ratio: {flow_ratio:.2f}, min: {min_flow_ratio})"
        })
    
    return {
        "rule_id": "flow_progress_signal",
        "rule_name": "Flow Progress Signal",
        "fail_count": len(failures),
        "eligible_count": 1,  # Board-level check (boolean)
        "passed": len(failures) == 0,
        "failures": failures,
        "metrics": {
            "wip_count": wip_count,
            "completed_recent": completed_count,
            "flow_ratio": round(flow_ratio, 2)
        },
        "note": "Requires completion dates. May use dateLastActivity as fallback."
    }


def run_all_flow_rules(parsed_data: Dict[str, Any], config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Run all flow-related rules.
    
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
    
    # Rule 7: Progress Monitoring
    if config.get("progress_monitoring", {}).get("enabled", True):
        results.append(check_progress_monitoring(parsed_data, merged_config))
    
    # Rule 12: Flow Progress Signal
    if config.get("flow_progress_signal", {}).get("enabled", True):
        results.append(check_flow_progress_signal(parsed_data, merged_config))
    
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
                "name": "Stale card",
                "list_id": "list2",
                "closed": False,
                "dateLastActivity": "2025-01-15T12:00:00Z",  # 21 days ago
                "actions": []
            },
            {
                "id": "card2",
                "name": "Active card",
                "list_id": "list2",
                "closed": False,
                "dateLastActivity": "2025-02-04T12:00:00Z",  # Yesterday
                "actions": []
            },
            {
                "id": "card3",
                "name": "Completed recently",
                "list_id": "list3",
                "closed": True,
                "dateLastActivity": "2025-02-03T12:00:00Z",
                "actions": []
            }
        ]
    }
    
    results = run_all_flow_rules(test_data)
    
    for result in results:
        print(f"\n{result['rule_name']}:")
        print(f"  Failed: {result['fail_count']}/{result['eligible_count']}")
        print(f"  Passed: {result['passed']}")
        if result.get('metrics'):
            print(f"  Metrics: {result['metrics']}")
        if result['failures']:
            print("  Failures:")
            for failure in result['failures']:
                print(f"    - {failure.get('reason', 'N/A')}")
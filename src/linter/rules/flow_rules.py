"""Flow rules.

Covers:
- progress_monitoring

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
    """progress_monitoring: Stale In-Progress work.
    
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
    
    # rule_id: progress_monitoring
    if config.get("progress_monitoring", {}).get("enabled", True):
        results.append(check_progress_monitoring(parsed_data, merged_config))
    
    
    return results

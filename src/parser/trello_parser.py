"""Parse Trello board exports into normalized Python structures.

This module provides simple functions for extracting data from Trello JSON exports.
All functions follow the same pattern:
1. Validate the payload
2. Extract the data safely
3. Return normalized results

Example:
    >>> import json
    >>> with open('board.json') as f:
    ...     data = json.load(f)
    >>> 
    >>> summary = parse_board_summary(data)
    >>> cards = parse_cards(data)
    >>> print(f"{summary['board_name']} has {summary['cards_count']} cards")
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from pathlib import Path


# -------------------------
# Custom Exception
# -------------------------

class TrelloParseError(Exception):
    """Raised when Trello JSON parsing fails."""
    pass


# -------------------------
# Internal Validation Helpers
# -------------------------

def _validate_payload(payload: Dict[str, Any]) -> None:
    """Check that payload looks like valid Trello JSON.
    
    Args:
        payload: Dictionary to validate
        
    Raises:
        TrelloParseError: If payload is invalid
    """
    if not isinstance(payload, dict):
        raise TrelloParseError("Payload must be a dictionary")
    
    # Trello exports always have a 'name' field for the board
    if 'name' not in payload:
        raise TrelloParseError("Missing 'name' field - not a valid Trello export")


def _safe_get_list(payload: Dict[str, Any], key: str) -> List[Dict]:
    """Safely extract a list from payload, returning empty list if missing.
    
    Args:
        payload: Source dictionary
        key: Key to extract (e.g., 'cards', 'lists', 'members')
        
    Returns:
        List from payload, or empty list if missing or not a list
    """
    value = payload.get(key)
    return value if isinstance(value, list) else []


# -------------------------
# Public Parsing Functions
# -------------------------

def parse_board_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract board name and basic counts from Trello JSON.
    
    Args:
        payload: Dictionary containing Trello board JSON data
        
    Returns:
        Dictionary with:
            - board_name (str): Name of the board
            - cards_count (int): Number of cards
            - members_count (int): Number of members
            
    Raises:
        TrelloParseError: If payload is invalid
        
    Example:
        >>> summary = parse_board_summary(trello_data)
        >>> print(f"{summary['board_name']}: {summary['cards_count']} cards")
        Sprint 23 Board: 42 cards
    """
    _validate_payload(payload)
    
    board_name = payload.get("name") or "(unknown)"
    cards = _safe_get_list(payload, "cards")
    members = _safe_get_list(payload, "members")
    
    return {
        "board_name": board_name,
        "cards_count": len(cards),
        "members_count": len(members),
    }


def parse_cards(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract card names and due dates from Trello JSON.
    
    Args:
        payload: Dictionary containing Trello board JSON data
        
    Returns:
        List of dictionaries, each with:
            - name (str): Card name (or "(unnamed)" if missing)
            - due (str | None): ISO datetime string for due date
            
    Raises:
        TrelloParseError: If payload is invalid
        
    Example:
        >>> cards = parse_cards(trello_data)
        >>> for card in cards:
        ...     if card['due']:
        ...         print(f"{card['name']} due: {card['due']}")
    """
    _validate_payload(payload)
    
    cards = _safe_get_list(payload, "cards")
    result = []
    
    for card in cards:
        if not isinstance(card, dict):
            continue
            
        result.append({
            "name": card.get("name") or "(unnamed)",
            "due": card.get("due"),
        })
    
    return result


def parse_full_board(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse complete board data including all cards, lists, members, and checklists.
    
    This is the main parsing function for the rule engine.
    
    Args:
        payload: Dictionary containing Trello board JSON data
        
    Returns:
        Dictionary with:
            - board: Board metadata (id, name, desc)
            - lists: All lists with id, name, closed status
            - cards: All cards with full details
            - members: All board members
            - checklists: All checklists with items
            
    Raises:
        TrelloParseError: If payload is invalid
        
    Example:
        >>> data = parse_full_board(trello_data)
        >>> print(data['board']['name'])
        >>> print(f"Found {len(data['cards'])} cards")
        >>> print(f"Found {len(data['lists'])} lists")
    """
    _validate_payload(payload)
    
    return {
        'board': _parse_board_metadata(payload),
        'lists': _parse_lists(payload),
        'cards': _parse_cards_full(payload),
        'members': _parse_members(payload),
        'checklists': _parse_checklists(payload),
    }


# -------------------------
# Internal Parsing Helpers
# -------------------------

def _parse_board_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract board-level metadata.
    
    Args:
        payload: Validated Trello board JSON
        
    Returns:
        Dictionary with id, name, and description
    """
    return {
        'id': payload.get('id'),
        'name': payload.get('name'),
        'desc': payload.get('desc', ''),
    }


def _parse_lists(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all lists from the board.
    
    Args:
        payload: Validated Trello board JSON
        
    Returns:
        List of dictionaries with list id, name, and closed status
    """
    lists = _safe_get_list(payload, 'lists')
    result = []
    
    for lst in lists:
        if not isinstance(lst, dict):
            continue
            
        result.append({
            'id': lst.get('id'),
            'name': lst.get('name'),
            'closed': lst.get('closed', False),
        })
    
    return result


def _parse_cards_full(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all cards with complete details.
    
    Args:
        payload: Validated Trello board JSON
        
    Returns:
        List of dictionaries with full card details
    """
    cards = _safe_get_list(payload, 'cards')
    result = []
    
    for card in cards:
        if not isinstance(card, dict):
            continue
            
        result.append({
            'id': card.get('id'),
            'name': card.get('name'),
            'desc': card.get('desc', ''),
            'list_id': card.get('idList'),
            'dateLastActivity': card.get('dateLastActivity'),
            'members': card.get('idMembers', []),
            'labels': card.get('labels', []),
            'checklists': card.get('idChecklists', []),
            'closed': card.get('closed', False),
            'due': card.get('due'),
            'dueComplete': card.get('dueComplete'),
            'short_url': card.get('shortUrl'),
            'actions': card.get('actions', []),
        })
    
    return result


def _parse_members(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all board members.
    
    Args:
        payload: Validated Trello board JSON
        
    Returns:
        List of dictionaries with member id, fullName, and username
    """
    members = _safe_get_list(payload, 'members')
    result = []
    
    for member in members:
        if not isinstance(member, dict):
            continue
            
        result.append({
            'id': member.get('id'),
            'fullName': member.get('fullName'),
            'username': member.get('username'),
        })
    
    return result


def _parse_checklists(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all checklists from the board.
    
    Args:
        payload: Validated Trello board JSON
        
    Returns:
        List of dictionaries with checklist id, name, and items
    """
    checklists = _safe_get_list(payload, 'checklists')
    result = []
    
    for checklist in checklists:
        if not isinstance(checklist, dict):
            continue
            
        result.append({
            'id': checklist.get('id'),
            'name': checklist.get('name', ''),
            'checkItems': checklist.get('checkItems', []),
        })
    
    return result


# -------------------------
# Utility Functions
# -------------------------

def load_trello_file(file_path: str) -> Dict[str, Any]:
    """Load and validate a Trello JSON file.
    
    Args:
        file_path: Path to Trello JSON export file
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        TrelloParseError: If file is invalid or not valid JSON
        
    Example:
        >>> data = load_trello_file('my_board.json')
        >>> summary = parse_board_summary(data)
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        raise TrelloParseError(f"Invalid JSON in file: {e}")
    except UnicodeDecodeError as e:
        raise TrelloParseError(f"File encoding error: {e}")
    
    _validate_payload(payload)
    return payload


def get_list_by_name(payload: Dict[str, Any], list_name: str) -> Dict[str, Any] | None:
    """Find a list by name (case-insensitive).
    
    Args:
        payload: Trello board JSON data
        list_name: Name of the list to find
        
    Returns:
        List dictionary if found, None otherwise
        
    Example:
        >>> done_list = get_list_by_name(data, 'Done')
        >>> if done_list:
        ...     print(f"Found list: {done_list['id']}")
    """
    lists = _safe_get_list(payload, 'lists')
    list_name_lower = list_name.lower()
    
    for lst in lists:
        if isinstance(lst, dict) and lst.get('name', '').lower() == list_name_lower:
            return lst
    
    return None


def get_cards_in_list(payload: Dict[str, Any], list_id: str) -> List[Dict[str, Any]]:
    """Get all cards in a specific list.
    
    Args:
        payload: Trello board JSON data
        list_id: ID of the list
        
    Returns:
        List of card dictionaries in that list
        
    Example:
        >>> done_list = get_list_by_name(data, 'Done')
        >>> done_cards = get_cards_in_list(data, done_list['id'])
        >>> print(f"Done list has {len(done_cards)} cards")
    """
    cards = _safe_get_list(payload, 'cards')
    result = []
    
    for card in cards:
        if isinstance(card, dict) and card.get('idList') == list_id:
            result.append(card)
    
    return result


# -------------------------
# Quick Reference
# -------------------------

"""
QUICK REFERENCE - Common Use Cases
===================================

1. Get board summary:
    summary = parse_board_summary(data)
    
2. Get all cards with due dates:
    cards = parse_cards(data)
    
3. Parse complete board for analysis:
    full_data = parse_full_board(data)
    
4. Load from file:
    data = load_trello_file('board.json')
    
5. Find specific list:
    done_list = get_list_by_name(data, 'Done')
    
6. Get cards in a list:
    cards = get_cards_in_list(data, list_id)
"""

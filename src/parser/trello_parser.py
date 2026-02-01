"""Parse Trello board exports into normalized Python structures.
Includes:
- TrelloParser class for full-file parsing
- Methods for board summary counts and card field extraction
"""
import json
from typing import Any, Dict, List
from datetime import datetime


class TrelloParser:
    def __init__(self, json_file_path: str = None):
        """Initialize parser with optional file path.
        
        Args:
            json_file_path: Path to Trello JSON export file. Optional if using
                          parse_from_dict() or lightweight methods.
        """
        self.json_file_path = json_file_path
        self.board_data = None
    
    def parse(self) -> Dict:
        """Parse Trello JSON export from file.
        
        Returns:
            Dictionary containing parsed board, lists, cards, and members
        """
        if not self.json_file_path:
            raise ValueError("json_file_path must be provided to parse from file")
            
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            self.board_data = json.load(f)
        
        return {
            'board': self._parse_board(),
            'lists': self._parse_lists(),
            'cards': self._parse_cards(),
            'members': self._parse_members()
        }
    
    def parse_from_dict(self, payload: Dict[str, Any]) -> Dict:
        """Parse Trello data from an already-loaded dictionary.
        
        Args:
            payload: Dictionary containing Trello board JSON data
            
        Returns:
            Dictionary containing parsed board, lists, cards, and members
        """
        self.board_data = payload
        
        return {
            'board': self._parse_board(),
            'lists': self._parse_lists(),
            'cards': self._parse_cards(),
            'members': self._parse_members()
        }
    
    def get_board_summary(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract board name and basic counts from Trello JSON payload.
        
        Args:
            payload: Optional dictionary containing Trello board data.
                    If not provided, uses self.board_data.
        
        Returns:
            Dictionary with board_name, cards_count, and members_count
        """
        data = payload if payload is not None else self.board_data
        
        if data is None:
            raise ValueError("No board data available. Call parse() first or provide payload.")
        
        board_name = data.get("name") or "(unknown)"
        cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        members = data.get("members") if isinstance(data.get("members"), list) else []
        
        return {
            "board_name": board_name,
            "cards_count": len(cards),
            "members_count": len(members),
        }
    
    def get_cards_with_due_dates(self, payload: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract card name and due date from Trello JSON payload.
        
        Args:
            payload: Optional dictionary containing Trello board data.
                    If not provided, uses self.board_data.
        
        Returns:
            List of dictionaries with 'name' and 'due' fields for each card
        """
        data = payload if payload is not None else self.board_data
        
        if data is None:
            raise ValueError("No board data available. Call parse() first or provide payload.")
        
        cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        parsed = []
        
        for card in cards:
            parsed.append({
                "name": card.get("name") or "(unnamed)",
                "due": card.get("due"),
            })
        
        return parsed
    
    def _parse_board(self) -> Dict:
        """Parse board metadata."""
        return {
            'id': self.board_data.get('id'),
            'name': self.board_data.get('name'),
            'desc': self.board_data.get('desc', '')
        }
    
    def _parse_lists(self) -> List[Dict]:
        """Parse all lists on the board."""
        return [{
            'id': lst.get('id'),
            'name': lst.get('name'),
            'closed': lst.get('closed', False)
        } for lst in self.board_data.get('lists', [])]
    
    def _parse_cards(self) -> List[Dict]:
        """Parse all cards on the board."""
        cards = []
        for card in self.board_data.get('cards', []):
            cards.append({
                'id': card.get('id'),
                'name': card.get('name'),
                'desc': card.get('desc', ''),
                'list_id': card.get('idList'),
                'members': card.get('idMembers', []),
                'labels': card.get('labels', []),
                'checklists': card.get('idChecklists', []),
                'closed': card.get('closed', False)
            })
        return cards
    
    def _parse_members(self) -> List[Dict]:
        """Parse all members on the board."""
        return [{
            'id': member.get('id'),
            'fullName': member.get('fullName'),
            'username': member.get('username')
        } for member in self.board_data.get('members', [])]
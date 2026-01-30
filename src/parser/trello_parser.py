# src/parser/trello_parser.py
import json
from typing import Any, Dict, List
from datetime import datetime

class TrelloParser:
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.board_data = None
    
    def parse(self) -> Dict:
        """Parse Trello JSON export"""
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            self.board_data = json.load(f)
        
        return {
            'board': self._parse_board(),
            'lists': self._parse_lists(),
            'cards': self._parse_cards(),
            'members': self._parse_members()
        }
    
    def _parse_board(self) -> Dict:
        return {
            'id': self.board_data.get('id'),
            'name': self.board_data.get('name'),
            'desc': self.board_data.get('desc', '')
        }
    
    def _parse_lists(self) -> List[Dict]:
        return [{
            'id': lst.get('id'),
            'name': lst.get('name'),
            'closed': lst.get('closed', False)
        } for lst in self.board_data.get('lists', [])]
    
    def _parse_cards(self) -> List[Dict]:
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
        return [{
            'id': member.get('id'),
            'fullName': member.get('fullName'),
            'username': member.get('username')
        } for member in self.board_data.get('members', [])]


def parse_board_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract board name and basic counts from a Trello JSON payload."""
    board_name = payload.get("name") or "(unknown)"
    cards = payload.get("cards") if isinstance(payload.get("cards"), list) else []
    members = payload.get("members") if isinstance(payload.get("members"), list) else []

    return {
        "board_name": board_name,
        "cards_count": len(cards),
        "members_count": len(members),
    }

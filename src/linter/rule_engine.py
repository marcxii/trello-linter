"""Master Rule Engine - Orchestrates all rule checks.

This is the main entry point for running all linting rules against a Trello board.

Usage:
    from src.linter.rule_engine import RuleEngine
    from src.parser.trello_parser import parse_full_board
    
    # Parse board
    board_data = parse_full_board(trello_json)
    
    # Run rules
    engine = RuleEngine(config_path='config/rules_config.yaml')
    results = engine.run_all_rules(board_data)
    
    # Get scores
    from src.linter.scoring_engine import calculate_overall_score
    scores = calculate_overall_score(results)
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import all rule groups
from src.linter.rules.assignment_rules import run_all_assignment_rules
from src.linter.rules.estimation_rules import run_all_estimation_rules
from src.linter.rules.capacity_rules import run_all_capacity_rules
from src.linter.rules.flow_rules import run_all_flow_rules


class RuleEngine:
    """Main rule engine that orchestrates all linting rules."""
    
    def __init__(self, config_path: Optional[str] = None, config: Optional[Dict] = None):
        """Initialize rule engine with configuration.
        
        Args:
            config_path: Path to rules_config.yaml file
            config: Direct config dictionary (overrides config_path)
        """
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
        else:
            # Try default path
            default_path = Path(__file__).parent.parent.parent / "config" / "rules_config.yaml"
            if default_path.exists():
                self.config = self._load_config(str(default_path))
            else:
                self.config = {}
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file not found at {config_path}, using defaults")
            return {}
        except yaml.YAMLError as e:
            print(f"Warning: Error parsing config file: {e}, using defaults")
            return {}
    
    def run_all_rules(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all enabled rules against the board data.
        
        Args:
            parsed_data: Full board data from parse_full_board()
            
        Returns:
            List of rule result dictionaries, each containing:
                - rule_id: str
                - rule_name: str
                - fail_count: int
                - eligible_count: int
                - passed: bool
                - failures: list of failure details
        """
        all_results = []
        
        # Run assignment rules (Rules 1, 2, 11, 13)
        assignment_results = run_all_assignment_rules(parsed_data, self.config)
        all_results.extend(assignment_results)
        
        # Run estimation rules (Rules 3, 4, 14, 15)
        estimation_results = run_all_estimation_rules(parsed_data, self.config)
        all_results.extend(estimation_results)
        
        # Run capacity rules (Rules 5, 6, 8, 9, 10)
        capacity_results = run_all_capacity_rules(parsed_data, self.config)
        all_results.extend(capacity_results)
        
        # Run flow rules (Rules 7, 12)
        flow_results = run_all_flow_rules(parsed_data, self.config)
        all_results.extend(flow_results)
        
        return all_results
    
    def run_specific_rules(self, parsed_data: Dict[str, Any], rule_ids: List[str]) -> List[Dict[str, Any]]:
        """Run only specific rules by their IDs.
        
        Args:
            parsed_data: Full board data from parse_full_board()
            rule_ids: List of rule IDs to run (e.g., ['card_ownership', 'past_due_violation'])
            
        Returns:
            List of rule results for specified rules only
        """
        all_results = self.run_all_rules(parsed_data)
        return [r for r in all_results if r.get('rule_id') in rule_ids]
    
    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule IDs from configuration.
        
        Returns:
            List of enabled rule IDs
        """
        enabled = []
        
        rule_ids = [
            'card_ownership', 'card_due_date', 'card_descriptiveness',
            'story_point_estimation', 'past_due_violation', 'progress_threshold',
            'progress_monitoring', 'weekly_workload', 'individual_overload',
            'near_term_overcommitment', 'unscheduled_work', 'flow_progress_signal',
            'card_completion', 'card_effort', 'description_canonicalization'
        ]
        
        for rule_id in rule_ids:
            if self.config.get(rule_id, {}).get('enabled', True):
                enabled.append(rule_id)
        
        return enabled
    
    def get_rule_weights(self) -> Dict[str, float]:
        """Get configured weights for all rules.
        
        Returns:
            Dictionary mapping rule IDs to their weights
        """
        return self.config.get('weights', {})


# Legacy compatibility function (for existing code that uses count_overdue_cards)
def count_overdue_cards(run_id: int) -> int:
    """Legacy function for backward compatibility.
    
    Counts overdue cards from database for a specific run.
    This is maintained for compatibility with existing controller code.
    
    Args:
        run_id: Database run ID
        
    Returns:
        Count of overdue cards
    """
    from src.database.sqlite import get_db
    from datetime import datetime, timezone
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    cursor = db.execute("""
        SELECT COUNT(*) as count
        FROM cards
        WHERE run_id = ?
        AND due IS NOT NULL
        AND due < ?
    """, (run_id, now))
    
    row = cursor.fetchone()
    return row['count'] if row else 0


# Example usage and testing
if __name__ == "__main__":
    # Sample test data
    test_data = {
        "board": {"id": "board1", "name": "Test Board", "desc": ""},
        "lists": [
            {"id": "list1", "name": "Backlog"},
            {"id": "list2", "name": "In Progress"},
            {"id": "list3", "name": "Done"}
        ],
        "members": [
            {"id": "user1", "fullName": "Alice Smith", "username": "alice"},
            {"id": "user2", "fullName": "Bob Jones", "username": "bob"}
        ],
        "cards": [
            {
                "id": "card1",
                "name": "Implement login",
                "list_id": "list2",
                "closed": False,
                "members": [],  # FAIL: No owner
                "due": None,    # FAIL: No due date
                "desc": "Short",  # FAIL: Too short
                "labels": [],
                "checklists": []
            },
            {
                "id": "card2",
                "name": "Good card",
                "list_id": "list2",
                "closed": False,
                "members": ["user1"],
                "due": "2025-02-10T12:00:00Z",
                "desc": "As a user, I want to login so I can access my account. Story Point: 3",
                "labels": [],
                "checklists": []
            },
            {
                "id": "card3",
                "name": "Overdue card",
                "list_id": "list2",
                "closed": False,
                "members": ["user2"],
                "due": "2025-01-01T12:00:00Z",  # FAIL: Past due
                "desc": "As a user, I want to reset password. SP: 5",
                "labels": [],
                "checklists": []
            }
        ],
        "checklists": []
    }
    
    # Initialize engine (without config file for testing)
    engine = RuleEngine(config={
        "lists": {
            "backlog_keywords": ["backlog"],
            "in_progress_keywords": ["in progress"],
            "done_keywords": ["done"]
        },
        "card_ownership": {"enabled": True},
        "card_due_date": {"enabled": True},
        "card_descriptiveness": {"enabled": True, "minimum_desc_char": 20},
        "past_due_violation": {"enabled": True},
    })
    
    # Run all rules
    results = engine.run_all_rules(test_data)
    
    # Display results
    print("Rule Engine Test Results")
    print("=" * 60)
    
    for result in results:
        status = "✓ PASS" if result['passed'] else "✗ FAIL"
        print(f"\n{status} {result['rule_name']}")
        print(f"   Failures: {result['fail_count']}/{result['eligible_count']}")
        
        if result['failures'] and len(result['failures']) <= 3:
            for failure in result['failures']:
                card_name = failure.get('card_name', failure.get('member_name', 'N/A'))
                print(f"   - {card_name}: {failure.get('reason', 'N/A')}")
    
    print("\n" + "=" * 60)
    print(f"Total rules run: {len(results)}")
    print(f"Rules passed: {sum(1 for r in results if r['passed'])}")
    print(f"Rules failed: {sum(1 for r in results if not r['passed'])}")
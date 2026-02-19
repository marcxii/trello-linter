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
        
        # Run assignment rules (Rules 1, 2, 13)
        assignment_results = run_all_assignment_rules(parsed_data, self.config)
        all_results.extend(assignment_results)
        
        # Run estimation rules (Rules 3, 4, 14, 15)
        estimation_results = run_all_estimation_rules(parsed_data, self.config)
        all_results.extend(estimation_results)
        
        # Run capacity rules (Rules 5, 6)
        capacity_results = run_all_capacity_rules(parsed_data, self.config)
        all_results.extend(capacity_results)
        
        # Run flow rules (Rules 7)
        flow_results = run_all_flow_rules(parsed_data, self.config)
        all_results.extend(flow_results)

        return self._attach_rule_descriptions(all_results)

    def _attach_rule_descriptions(self, rule_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Attach rule descriptions from config onto rule results."""
        if not rule_results:
            return []

        for result in rule_results:
            rule_id = result.get("rule_id")
            if not rule_id:
                continue
            description = self.config.get(rule_id, {}).get("description")
            if description:
                result["description"] = description
        return rule_results
    
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
            'progress_monitoring',
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

    def get_scoring_config(self) -> Dict[str, Any]:
        """Get scoring configuration section."""
        return self.config.get("scoring", {})




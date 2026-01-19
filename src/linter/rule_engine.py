# src/linter/rule_engine.py
from typing import List, Dict
from .rules import sprint_structure, done_evidence, user_story, acceptance_criteria, ownership

class RuleEngine:
    def __init__(self):
        self.rules = [
            sprint_structure.SprintStructureRule(),
            done_evidence.DoneEvidenceRule(),
            user_story.UserStoryRule(),
            acceptance_criteria.AcceptanceCriteriaRule(),
            ownership.OwnershipRule()
        ]
    
    def run_all_rules(self, parsed_data: Dict) -> List[Dict]:
        """Run all linting rules and collect findings"""
        all_findings = []
        
        for rule in self.rules:
            findings = rule.check(parsed_data)
            all_findings.extend(findings)
        
        return all_findings
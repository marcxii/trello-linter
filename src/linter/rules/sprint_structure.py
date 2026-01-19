# src/linter/rules/sprint_structure.py
from typing import Dict,List 

class SprintStructureRule:
    def __init__(self):
        self.name = "Sprint Structure"
        self.category = "Sprint Management"
    
    def check(self, parsed_data: Dict) -> List[Dict]:
        findings = []
        lists = parsed_data.get('lists', [])
        
        # Check for standard sprint lists
        required_lists = ['Backlog', 'To Do', 'In Progress', 'Done']
        list_names = [lst['name'] for lst in lists]
        
        for required in required_lists:
            if not any(required.lower() in name.lower() for name in list_names):
                findings.append({
                    'rule_name': self.name,
                    'severity': 'major',
                    'category': self.category,
                    'description': f'Missing standard list: {required}',
                    'suggestion': f'Create a "{required}" list to follow standard sprint structure'
                })
        
        return findings

# src/linter/rule_engine.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from src.database.sqlite import get_db

from .rules import acceptance_criteria, done_evidence, ownership, sprint_structure, user_story
from .rules.due_date_rule import evaluate_due_date

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


def count_overdue_cards(run_id: int, now: Optional[datetime] = None) -> int:
    """Evaluate cards for a run and return count of overdue cards."""
    db = get_db()
    rows = db.execute(
        "SELECT due FROM cards WHERE run_id = ?",
        (run_id,),
    ).fetchall()

    overdue = 0
    for row in rows:
        result = evaluate_due_date(row["due"], now=now)
        if result["overdue"]:
            overdue += 1

    return overdue

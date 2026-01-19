# src/scoring/scorer.py
from typing import List, Dict

class Scorer:
    WEIGHTS = {
        'Sprint Management': 0.20,
        'Story Quality': 0.25,
        'Acceptance Criteria': 0.25,
        'Ownership': 0.15,
        'Done Evidence': 0.15
    }
    
    SEVERITY_IMPACT = {
        'critical': -15,
        'major': -10,
        'minor': -5
    }
    
    def calculate_score(self, findings: List[Dict]) -> Dict:
        """Calculate overall and category scores"""
        category_scores = {}
        
        for category in self.WEIGHTS.keys():
            category_findings = [f for f in findings if f.get('category') == category]
            category_score = 100
            
            for finding in category_findings:
                severity = finding.get('severity', 'minor')
                category_score += self.SEVERITY_IMPACT.get(severity, -5)
            
            category_score = max(0, min(100, category_score))
            category_scores[category] = category_score
        
        # Calculate weighted overall score
        overall_score = sum(
            category_scores[cat] * weight 
            for cat, weight in self.WEIGHTS.items()
        )
        
        return {
            'overall_score': round(overall_score, 2),
            'category_scores': category_scores,
            'total_findings': len(findings),
            'critical_findings': len([f for f in findings if f['severity'] == 'critical']),
            'major_findings': len([f for f in findings if f['severity'] == 'major']),
            'minor_findings': len([f for f in findings if f['severity'] == 'minor'])
        }
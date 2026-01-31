"""Compute overall quality scores for a Trello analysis run.

Currently this is a placeholder scoring policy:
- start at 100
- subtract 1 point per overdue card
- clamp to the 0–100 range
"""

from __future__ import annotations


def compute_overall_score(overdue_count: int) -> int:
    """Return a score out of 100, subtracting 1 per overdue card."""
    score = 100 - int(overdue_count or 0)
    if score < 0:
        return 0
    if score > 100:
        return 100
    return score

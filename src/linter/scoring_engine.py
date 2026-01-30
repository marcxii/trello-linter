"""Compute overall quality scores."""

from __future__ import annotations


def compute_overall_score(overdue_count: int) -> int:
    """Return a score out of 100, subtracting 1 per overdue card."""
    score = 100 - int(overdue_count or 0)
    if score < 0:
        return 0
    if score > 100:
        return 100
    return score

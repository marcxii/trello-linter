"""Evaluate Trello card due dates for overdue status.

This module provides a small, pure function that:
- parses Trello ISO-8601 due timestamps (including trailing "Z")
- normalizes timezones to UTC when missing
- reports whether a card is overdue and how many whole days past due
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _parse_due(due_value: Optional[str]) -> Optional[datetime]:
    if not due_value:
        return None

    if not isinstance(due_value, str):
        return None

    value = due_value.strip()
    if not value:
        return None

    # Handle common Trello export format with trailing Z.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def evaluate_due_date(due_value: Optional[str], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return whether a due date is overdue and days past due."""
    due_dt = _parse_due(due_value)
    if due_dt is None:
        return {"overdue": False, "days_past_due": 0}

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    if due_dt >= current:
        return {"overdue": False, "days_past_due": 0}

    delta = current - due_dt
    return {"overdue": True, "days_past_due": delta.days}

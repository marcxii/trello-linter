"""Session helpers for per-user scoping.

Ensures every browser session has a stable, signed identifier
so database rows can be isolated per user.
"""

from __future__ import annotations

import uuid

from flask import session


def get_or_set_session_id() -> str:
    """Return the existing session_id or create a new UUID."""
    session_id = session.get("session_id")
    if session_id:
        return session_id

    session_id = uuid.uuid4().hex
    session["session_id"] = session_id
    return session_id

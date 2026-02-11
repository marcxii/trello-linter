"""Analysis controller for non-HTMX analysis endpoints.

Responsibilities:
- Provide a temporary alias endpoint during refactor.
- Expose a JSON API stub for future clients.

Scaffold behavior:
- Does not run the analysis pipeline.
- Does not persist analysis results.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

analysis_bp = Blueprint("analysis", __name__)


# -------------------------
# Backward-compatible alias
# -------------------------
@analysis_bp.post("/upload")
def upload_alias():
    """Alias route retained temporarily during refactor."""
    from src.controllers.partials_controller import analyze_partial

    return analyze_partial()


# -------------------------
# Optional JSON API stub
# -------------------------
@analysis_bp.post("/api/analyze")
def api_analyze():
    """JSON API stub for analysis.

    Intentionally returns 501 until the pipeline is wired.
    Useful for smoke tests or future non-HTMX clients.
    """
    uploaded = request.files.get("file") or request.files.get("trello_file")
    if uploaded is None:
        return jsonify({"error": "Missing file", "field": "file"}), 400

    return (
        jsonify(
            {
                "status": "not_implemented",
                "message": "Analysis pipeline not wired yet (scaffold stub).",
                "received": {
                    "filename": uploaded.filename or "(unnamed)",
                    "content_type": uploaded.mimetype,
                },
            }
        ),
        501,
    )



"""Analysis controller.

This controller will eventually handle:
- Accepting a board snapshot input (JSON upload OR Trello API connection details)
- Running the analysis pipeline
- Persisting a LintRun and redirecting to the report view

For Commit 1, keep it intentionally minimal so the MVC scaffolding can be reviewed
without coupling to the analysis implementation.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.post("/analyze")
def analyze():
    """Accept an analysis request.

    Option A stub:
    - Accepts an uploaded Trello JSON export under form field name `trello_file`
      (this is a placeholder contract; adjust later if needed).
    - Returns a 501 response indicating the pipeline is not wired yet.

    NOTE: Do not add database calls or pipeline imports in this commit.
    """

    uploaded = request.files.get("trello_file")
    if uploaded is None:
        return (
            jsonify(
                {
                    "error": "Missing file",
                    "message": "Upload a Trello JSON export as form field 'trello_file'.",
                }
            ),
            400,
        )

    # Basic filename presence check only (no parsing/validation in Commit 1)
    filename = uploaded.filename or "(unnamed)"

    return (
        jsonify(
            {
                "status": "not_implemented",
                "message": "Analysis pipeline not wired yet. This endpoint is a stub for MVC scaffolding.",
                "received": {"filename": filename, "content_type": uploaded.mimetype},
                "next": "Wire services.analysis_service.run_analysis(...) and redirect to /report/<run_id>",
            }
        ),
        501,
    )


# Backward-compatible alias route (optional):
@analysis_bp.post("/upload")
def upload_alias():
    """Alias for /analyze to avoid breaking existing forms during refactor."""
    return analyze()
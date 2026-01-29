"""TrelloScore Flask application entrypoint.

Commit 1 refactor target:
- Use an app factory (create_app)
- Register MVC controller blueprints
- Keep this module free of business logic (parsing/linting/scoring) and DB wiring

Later commits will add Postgres + SQLAlchemy + Alembic and wire services.
"""

from __future__ import annotations

import os

from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask app."""

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Basic config (keep minimal for Commit 1)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")

    from src.utils.session import get_or_set_session_id

    @app.before_request
    def ensure_session_id():
        get_or_set_session_id()

    # Register controller blueprints
    from src.controllers.main_controller import main_bp
    from src.controllers.analysis_controller import analysis_bp
    from src.controllers.partials_controller import partials_bp
    from src.controllers.report_controller import report_bp
    from src.controllers.export_controller import export_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(partials_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(export_bp)

    return app


# WSGI app instance for `flask run` or gunicorn (later)
app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

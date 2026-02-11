"""TrelloScore Flask application entrypoint.

Commit 1 refactor target:
- Use an app factory (create_app)
- Register MVC controller blueprints
- Keep this module free of business logic (parsing/linting/scoring) and DB wiring

Later commits will add Postgres + SQLAlchemy + Alembic and wire services.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template
from werkzeug.exceptions import RequestEntityTooLarge


def create_app() -> Flask:
    """Create and configure the Flask app."""

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Determine project root
    project_root = Path(__file__).parent.parent
    default_db_path = project_root / "instance" / "trelloscore.db"
    
    # Ensure instance directory exists
    instance_dir = project_root / "instance"
    instance_dir.mkdir(exist_ok=True)

    # Basic config (keep minimal for Commit 1)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["SQLITE_DB_PATH"] = os.getenv("SQLITE_DB_PATH", str(default_db_path))
    app.config["RUN_TTL_SECONDS"] = int(os.getenv("RUN_TTL_SECONDS", "21600"))
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))

    from src.utils.session import get_or_set_session_id
    from src.database.sqlite import close_db, init_db

    @app.before_request
    def ensure_session_id():
        get_or_set_session_id()

    @app.errorhandler(RequestEntityTooLarge)
    def handle_oversize(_err):
        return render_template(
            "partials/error.html",
            message="File too large. Please upload a smaller Trello JSON export.",
        )

    @app.teardown_appcontext
    def teardown_sqlite(exception=None):
        close_db(exception)

    with app.app_context():
        init_db()

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

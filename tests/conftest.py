import pytest

from src.database.sqlite import init_db
from src.main import create_app


@pytest.fixture()
def app(tmp_path):
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLITE_DB_PATH=str(tmp_path / "trelloscore.db"),
        RUN_TTL_SECONDS=0,
    )

    with app.app_context():
        init_db()

    return app


@pytest.fixture()
def client(app):
    return app.test_client()

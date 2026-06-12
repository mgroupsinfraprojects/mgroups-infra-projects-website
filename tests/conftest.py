import os
import tempfile
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app import app as flask_app, db


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        from app import init_db
        init_db()
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()

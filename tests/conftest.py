import os
import sys

# Ensure project root is on path before any app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Keep application startup deterministic under pytest.
os.environ["DEBUG"] = "false"
os.environ["STOCK_DAILY_SYNC_ENABLED"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.config import Settings

# Use a separate test DB file so we don't clobber dev data
TEST_DATABASE_URL = "sqlite:///./test_app.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test db file
    if os.path.exists("test_app.db"):
        os.remove("test_app.db")


@pytest.fixture(scope="function")
def db_session():
    """Provide a fresh DB session for each test, with rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Yield a TestClient with DB dependency overridden."""
    from fastapi.testclient import TestClient
    from app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Auth Helpers ─────────────────────────────────────────

def register_user(client, username="testuser", email="test@example.com", password="Password123!"):
    return client.post("/api/v1/users", json={
        "username": username,
        "email": email,
        "password": password,
    })


def login_user(client, username="testuser", password="Password123!"):
    return client.post("/api/v1/sessions", json={
        "username": username,
        "password": password,
    })


@pytest.fixture(scope="function")
def auth_client(client):
    """Yield a TestClient with an authenticated user."""
    register_user(client)
    login_resp = login_user(client)
    token = login_resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client
    client.headers.pop("Authorization", None)


# ─── Stock Fixtures ───────────────────────────────────────

@pytest.fixture(scope="function")
def sample_stocks(db_session):
    """Seed sample stocks into the test DB."""
    from app.models import Stock
    stocks = [
        Stock(symbol="2330", name="台積電", market="TWSE", industry="半導體業"),
        Stock(symbol="2317", name="鴻海", market="TWSE", industry="電子零組件業"),
        Stock(symbol="2454", name="聯發科", market="TWSE", industry="半導體業"),
    ]
    for s in stocks:
        db_session.add(s)
    db_session.commit()
    for s in stocks:
        db_session.refresh(s)
    return stocks

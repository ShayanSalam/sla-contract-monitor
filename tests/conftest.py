"""
Shared test fixtures.

Uses an in-memory SQLite database, completely isolated from the real
PostgreSQL database - running the test suite never touches real data.
The get_db dependency is overridden per-test so FastAPI's TestClient hits
this test database instead of whatever DATABASE_URL points to in .env.
"""
import os

# Set required env vars before any app module is imported, since
# app.core.config.Settings reads them at import time.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-used-in-tests")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.main import app

# Rate limiting is a real feature we want active in production, but it would
# incorrectly block the test suite itself (which creates several users in
# rapid succession, on purpose, from the same test-client "IP").
limiter.enabled = False

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the same in-memory DB alive across connections
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Fresh tables before every test, dropped after - full isolation
    between tests so one test's data can never leak into another."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_user_credentials():
    return {"email": "test@example.com", "password": "testpassword123"}


@pytest.fixture
def authenticated_client(client, test_user_credentials):
    """A TestClient with a real signed-up user and a valid auth header
    already attached - saves every test that needs auth from repeating
    the signup/login dance."""
    client.post("/auth/signup", json=test_user_credentials)
    login_res = client.post(
        "/auth/login",
        data={"username": test_user_credentials["email"], "password": test_user_credentials["password"]},
    )
    token = login_res.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

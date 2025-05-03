import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.database import Base, get_db
from app.api.main import app

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Create a test client with a fresh database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_match_data():
    return {
        "team_a": {
            "name": "Test Team A",
            "players": [
                {
                    "aim_rating": 75.0,
                    "reaction_time": 180.0,
                    "movement_accuracy": 0.8,
                    "spray_control": 0.7,
                    "clutch_iq": 0.6
                }
                for _ in range(5)
            ]
        },
        "team_b": {
            "name": "Test Team B",
            "players": [
                {
                    "aim_rating": 75.0,
                    "reaction_time": 180.0,
                    "movement_accuracy": 0.8,
                    "spray_control": 0.7,
                    "clutch_iq": 0.6
                }
                for _ in range(5)
            ]
        },
        "map_name": "ascent",
        "agent_assignments": {
            "A1": "Jett",
            "B1": "Sage"
        }
    }

@pytest.fixture
def created_match(client, sample_match_data):
    """Create a match and return its ID."""
    response = client.post("/matches/", json=sample_match_data)
    assert response.status_code == 200
    return response.json()["match_id"] 
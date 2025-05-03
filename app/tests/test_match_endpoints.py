import pytest
from fastapi.testclient import TestClient

def test_create_match(client, sample_match_data):
    """Test creating a new match."""
    response = client.post("/matches/", json=sample_match_data)
    assert response.status_code == 200
    data = response.json()
    assert "match_id" in data
    assert data["status"] == "created"

def test_create_match_invalid_map(client, sample_match_data):
    """Test creating a match with invalid map."""
    sample_match_data["map_name"] = "invalid_map"
    response = client.post("/matches/", json=sample_match_data)
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()

def test_get_match_state(client, created_match):
    """Test getting match state."""
    response = client.get(f"/matches/{created_match}")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == created_match
    assert data["team_a_score"] == 0
    assert data["team_b_score"] == 0
    assert data["current_round"] == 1
    assert not data["is_overtime"]
    assert "players" in data
    assert "current_round_state" in data

def test_get_nonexistent_match(client):
    """Test getting a match that doesn't exist."""
    response = client.get("/matches/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_simulate_next_round(client, created_match):
    """Test simulating the next round."""
    response = client.post(f"/matches/{created_match}/rounds/next")
    assert response.status_code == 200
    data = response.json()
    assert "round_number" in data
    assert "winner" in data
    assert "end_condition" in data
    assert "round_summary" in data

def test_get_round_state(client, created_match):
    """Test getting round state."""
    # First simulate a round
    client.post(f"/matches/{created_match}/rounds/next")
    
    response = client.get(f"/matches/{created_match}/rounds/1")
    assert response.status_code == 200
    data = response.json()
    assert data["round_number"] == 1
    assert "state" in data
    assert "events" in data

def test_get_nonexistent_round(client, created_match):
    """Test getting a round that hasn't been played."""
    response = client.get(f"/matches/{created_match}/rounds/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_match_stats(client, created_match):
    """Test getting match statistics."""
    # First simulate a round
    client.post(f"/matches/{created_match}/rounds/next")
    
    response = client.get(f"/matches/{created_match}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == created_match
    assert "duration" in data
    assert "team_a_score" in data
    assert "team_b_score" in data
    assert "rounds" in data
    assert "player_stats" in data
    assert "team_stats" in data

def test_list_maps(client):
    """Test listing available maps."""
    response = client.get("/maps/")
    assert response.status_code == 200
    maps = response.json()
    assert isinstance(maps, list)
    assert "ascent" in maps

def test_list_agents(client):
    """Test listing available agents."""
    response = client.get("/agents/")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    assert "Jett" in agents
    assert "Sage" in agents

def test_list_ai_types(client):
    """Test listing available AI types."""
    response = client.get("/ai_types/")
    assert response.status_code == 200
    ai_types = response.json()
    assert isinstance(ai_types, list)
    assert "greedy" in ai_types 
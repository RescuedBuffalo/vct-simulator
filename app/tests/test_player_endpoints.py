import pytest
from fastapi.testclient import TestClient

def test_assign_agent(client, created_match):
    """Test assigning an agent to a player."""
    response = client.post(
        f"/matches/{created_match}/players/A1/agent",
        json={"agent_name": "Jett"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == "A1"
    assert data["agent"] == "Jett"
    assert data["status"] == "updated"

def test_assign_invalid_agent(client, created_match):
    """Test assigning an invalid agent to a player."""
    response = client.post(
        f"/matches/{created_match}/players/A1/agent",
        json={"agent_name": "InvalidAgent"}
    )
    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()

def test_assign_agent_nonexistent_player(client, created_match):
    """Test assigning an agent to a nonexistent player."""
    response = client.post(
        f"/matches/{created_match}/players/INVALID/agent",
        json={"agent_name": "Jett"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_assign_ai(client, created_match):
    """Test assigning an AI to a player."""
    response = client.post(
        f"/matches/{created_match}/players/A1/ai",
        json={"ai_type": "greedy", "skill_level": 0.8}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == "A1"
    assert data["ai_type"] == "greedy"
    assert data["status"] == "updated"

def test_assign_invalid_ai_type(client, created_match):
    """Test assigning an invalid AI type to a player."""
    response = client.post(
        f"/matches/{created_match}/players/A1/ai",
        json={"ai_type": "invalid", "skill_level": 0.8}
    )
    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()

def test_assign_ai_invalid_skill_level(client, created_match):
    """Test assigning an AI with invalid skill level."""
    response = client.post(
        f"/matches/{created_match}/players/A1/ai",
        json={"ai_type": "greedy", "skill_level": 1.5}  # Should be between 0 and 1
    )
    assert response.status_code == 422  # Validation error

def test_assign_ai_nonexistent_player(client, created_match):
    """Test assigning an AI to a nonexistent player."""
    response = client.post(
        f"/matches/{created_match}/players/INVALID/ai",
        json={"ai_type": "greedy", "skill_level": 0.8}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_player_state_in_match(client, created_match):
    """Test that player state is correctly reflected in match state."""
    # First assign an agent and AI
    client.post(
        f"/matches/{created_match}/players/A1/agent",
        json={"agent_name": "Jett"}
    )
    client.post(
        f"/matches/{created_match}/players/A1/ai",
        json={"ai_type": "greedy", "skill_level": 0.8}
    )
    
    # Get match state and check player
    response = client.get(f"/matches/{created_match}")
    assert response.status_code == 200
    data = response.json()
    player = data["players"]["A1"]
    assert player["agent"] == "Jett"
    assert player["health"] == 100
    assert player["armor"] == 0
    assert player["alive"] is True

def test_player_state_after_round(client, created_match):
    """Test that player state updates after round simulation."""
    # First assign agents
    client.post(
        f"/matches/{created_match}/players/A1/agent",
        json={"agent_name": "Jett"}
    )
    client.post(
        f"/matches/{created_match}/players/B1/agent",
        json={"agent_name": "Sage"}
    )
    
    # Simulate a round
    client.post(f"/matches/{created_match}/rounds/next")
    
    # Get match state and check players
    response = client.get(f"/matches/{created_match}")
    assert response.status_code == 200
    data = response.json()
    
    # Check that player states have been updated
    for player in data["players"].values():
        assert "kills" in player["stats"]
        assert "deaths" in player["stats"]
        assert "assists" in player["stats"] 
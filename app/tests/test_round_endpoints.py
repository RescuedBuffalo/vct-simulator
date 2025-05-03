import pytest
from fastapi.testclient import TestClient

def test_round_progression(client, created_match):
    """Test that rounds progress correctly."""
    # Simulate multiple rounds
    for i in range(3):
        response = client.post(f"/matches/{created_match}/rounds/next")
        assert response.status_code == 200
        data = response.json()
        assert data["round_number"] == i + 1
        assert data["winner"] in ["attackers", "defenders"]
        assert data["end_condition"] in ["elimination", "spike_detonation", "spike_defused", "time_expired"]

def test_round_state_tracking(client, created_match):
    """Test that round state is tracked correctly."""
    # Simulate a round
    client.post(f"/matches/{created_match}/rounds/next")
    
    # Get round state
    response = client.get(f"/matches/{created_match}/rounds/1")
    assert response.status_code == 200
    data = response.json()
    
    # Check round state structure
    state = data["state"]
    assert state["round_number"] == 1
    assert state["phase"] in ["buy", "round", "end"]
    assert isinstance(state["time_remaining"], (int, float))
    assert isinstance(state["spike_planted"], bool)
    assert isinstance(state["alive_attackers"], int)
    assert isinstance(state["alive_defenders"], int)

def test_round_events(client, created_match):
    """Test that round events are recorded."""
    # Simulate a round
    client.post(f"/matches/{created_match}/rounds/next")
    
    # Get round state with events
    response = client.get(f"/matches/{created_match}/rounds/1")
    assert response.status_code == 200
    data = response.json()
    
    # Check events
    events = data["events"]
    assert isinstance(events, list)
    # Events might include kills, plants, defuses, etc.

def test_round_score_updates(client, created_match):
    """Test that round results update match scores."""
    # Simulate a round
    response = client.post(f"/matches/{created_match}/rounds/next")
    round_data = response.json()
    
    # Get match state
    response = client.get(f"/matches/{created_match}")
    match_data = response.json()
    
    # Check that scores were updated based on round winner
    if round_data["winner"] == "attackers":
        assert match_data["team_a_score"] == 1
        assert match_data["team_b_score"] == 0
    else:
        assert match_data["team_a_score"] == 0
        assert match_data["team_b_score"] == 1

def test_round_player_stats(client, created_match):
    """Test that player statistics are updated after rounds."""
    # Simulate a round
    client.post(f"/matches/{created_match}/rounds/next")
    
    # Get match stats
    response = client.get(f"/matches/{created_match}/stats")
    assert response.status_code == 200
    data = response.json()
    
    # Check player statistics
    player_stats = data["player_stats"]
    for player_id, stats in player_stats.items():
        assert "kills" in stats
        assert "deaths" in stats
        assert "assists" in stats
        assert isinstance(stats["kills"], int)
        assert isinstance(stats["deaths"], int)
        assert isinstance(stats["assists"], int)

def test_invalid_round_access(client, created_match):
    """Test accessing invalid round numbers."""
    # Try to get round 0 (invalid)
    response = client.get(f"/matches/{created_match}/rounds/0")
    assert response.status_code == 404
    
    # Try to get future round
    response = client.get(f"/matches/{created_match}/rounds/999")
    assert response.status_code == 404

def test_round_buy_phase(client, created_match):
    """Test that buy phase works correctly."""
    # Access match directly to set up buy phase
    response = client.get(f"/matches/{created_match}")
    assert response.status_code == 200
    match_data = response.json()
    
    # Use the game manager to directly set up a round in buy phase
    from app.api.main import game_manager
    from app.simulation.models.round import RoundPhase
    
    # Get the match
    match = game_manager.matches[created_match]
    
    # Artificially set the round to buy phase
    match.round.phase = RoundPhase.BUY
    match.round.buy_phase_time = 10  # 10 seconds left in buy phase
    
    # Store the round state
    match.round_results[match.current_round] = match.round.get_round_summary()
    
    # Get round state
    response = client.get(f"/matches/{created_match}/rounds/{match.current_round}")
    assert response.status_code == 200
    data = response.json()
    
    # First phase should be buy
    state = data["state"]
    assert state["phase"] == "buy"
    
    # Players should have starting credits
    match_response = client.get(f"/matches/{created_match}")
    match_data = match_response.json()
    for player in match_data["players"].values():
        assert player["credits"] >= 0

def test_overtime_detection(client, created_match):
    """Test that overtime is detected correctly."""
    # Get initial match state
    response = client.get(f"/matches/{created_match}")
    assert response.status_code == 200
    data = response.json()
    assert not data["is_overtime"]
    
    # Would need to simulate many rounds to reach overtime
    # This is just checking the initial state 
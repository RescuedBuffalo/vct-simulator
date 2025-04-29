import pytest
import numpy as np
from ..simulation.ai.agents.rl_agent import RLAgent
from ..simulation.ai.training.spaces import ObservationSpace, ActionSpace
from ..simulation.models.game_state import GameState
from ..simulation.models.player import Player
from ..simulation.models.team import Team

@pytest.fixture
def game_state():
    """Create a mock game state for testing."""
    team_a = Team(id="Team A", name="Attackers", validate_size=False)
    team_b = Team(id="Team B", name="Defenders", validate_size=False)
    
    # Add some players to each team
    roles = ["duelist", "controller", "sentinel", "initiator", "duelist"]
    agents = ["Jett", "Sage", "Phoenix", "Brimstone", "Viper"]
    for i in range(5):
        team_a.add_player(Player(
            id=f"player_a{i}",
            name=f"Player A{i}",
            team_id="Team A",
            role=roles[i],
            agent=agents[i],
            aim_rating=75.0,
            reaction_time=200.0,
            movement_accuracy=0.8,
            spray_control=0.7,
            clutch_iq=0.6
        ))
        team_b.add_player(Player(
            id=f"player_b{i}",
            name=f"Player B{i}",
            team_id="Team B",
            role=roles[i],
            agent=agents[i],
            aim_rating=75.0,
            reaction_time=200.0,
            movement_accuracy=0.8,
            spray_control=0.7,
            clutch_iq=0.6
        ))
    
    state = GameState(teams=[team_a, team_b])
    return state

@pytest.fixture
def observation_space():
    """Create an observation space instance for testing."""
    return ObservationSpace()

@pytest.fixture
def action_space():
    """Create an action space instance for testing."""
    return ActionSpace()

def test_observation_space_shape():
    """Test that observation space has correct shape and bounds."""
    obs_space = ObservationSpace()
    
    # Check observation space dimensions
    assert obs_space.shape == (29,)  # Actual size based on components
    assert obs_space.low.shape == obs_space.shape
    assert obs_space.high.shape == obs_space.shape
    
    # Check that bounds are reasonable
    assert np.all(obs_space.low <= obs_space.high)
    assert np.all(obs_space.low >= -np.inf)
    assert np.all(obs_space.high <= np.inf)

def test_action_space_shape():
    """Test that action space has correct shape and bounds."""
    action_space = ActionSpace()
    
    # Check action space dimensions
    assert action_space.shape == (8,)  # Example size, adjust based on actual implementation
    assert action_space.low.shape == action_space.shape
    assert action_space.high.shape == action_space.shape
    
    # Check that bounds are reasonable
    assert np.all(action_space.low <= action_space.high)
    assert np.all(action_space.low >= -1)
    assert np.all(action_space.high <= 1)

def test_observation_encoding(game_state, observation_space):
    """Test that game state can be encoded into observation space."""
    obs = observation_space.encode(game_state)
    
    # Check observation shape and bounds
    assert obs.shape == observation_space.shape
    assert np.all(obs >= observation_space.low)
    assert np.all(obs <= observation_space.high)
    
    # Test specific observation features
    assert not np.any(np.isnan(obs))
    assert not np.any(np.isinf(obs))

def test_action_decoding(action_space):
    """Test that actions can be decoded into game commands."""
    # Test various action values
    test_actions = [
        np.zeros(action_space.shape),
        np.ones(action_space.shape),
        -np.ones(action_space.shape),
        np.random.uniform(low=-1, high=1, size=action_space.shape)
    ]
    
    for action in test_actions:
        # Decode action into game command
        command = action_space.decode(action)
        
        # Check command structure
        assert isinstance(command, dict)
        assert 'action_type' in command
        assert command['action_type'] in ['move', 'shoot', 'plant', 'defuse', 'buy', 'idle']
        
        # Check command parameters based on action type
        if command['action_type'] == 'move':
            assert 'move' in command
            assert isinstance(command['move'], dict)
            assert 'direction' in command['move']
            assert 'is_walking' in command['move']
            assert 'is_crouching' in command['move']
        elif command['action_type'] == 'shoot':
            assert 'shoot' in command
            assert isinstance(command['shoot'], dict)
            assert 'target_id' in command['shoot']

def test_invalid_actions(action_space):
    """Test that invalid actions are handled appropriately."""
    # Test actions outside bounds
    with pytest.raises(ValueError):
        action_space.decode(np.ones(action_space.shape) * 2)
    
    with pytest.raises(ValueError):
        action_space.decode(np.ones(action_space.shape) * -2)
    
    # Test wrong shape
    with pytest.raises(ValueError):
        action_space.decode(np.zeros((10,)))

def test_observation_normalization(observation_space, game_state):
    """Test that observations are properly normalized."""
    obs = observation_space.encode(game_state)
    
    # Check that all values are normalized between -1 and 1
    assert np.all(obs >= -1)
    assert np.all(obs <= 1)
    
    # Test specific features are properly normalized
    # Add specific tests based on your observation space implementation 
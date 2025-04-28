import pytest
from app.simulation.ai.agents.base import BaseAgent, AgentConfig
from app.simulation.ai.agents.greedy import GreedyAgent
from app.simulation.ai.inference.agent_pool import AgentPool

def create_minimal_observation(phase='round', **kwargs) -> dict:
    """Create a minimal valid observation dictionary."""
    obs = {
        'alive': True,
        'phase': phase,
        'location': (0, 0, 0),
        'direction': 0.0,
        'health': 100,
        'armor': 0,
        'is_walking': False,
        'is_crouching': False,
        'is_jumping': False,
        'ground_contact': True,
        'creds': 0,
        'weapon': None,
        'shield': None,
        'spike': False,
        'visible_enemies': [],
        'heard_sounds': [],
        'status_effects': [],
        'utility_charges': {},
        'utility_cooldowns': {},
        'at_plant_site': False,
        'spike_planted': False,
        'at_spike': False
    }
    obs.update(kwargs)
    return obs

def test_agent_config_validation():
    """Test that AgentConfig validation works."""
    # Valid config should work
    config = AgentConfig(
        role="duelist",
        skill_level=0.7,
        personality={"aggression": 0.8, "patience": 0.3}
    )
    agent = GreedyAgent(config)
    assert agent.role == "duelist"
    assert agent.skill_level == 0.7
    
    # Invalid role should raise ValueError
    with pytest.raises(ValueError):
        config = AgentConfig(role="invalid", skill_level=0.5)
        GreedyAgent(config)
    
    # Invalid skill level should raise ValueError
    with pytest.raises(ValueError):
        config = AgentConfig(role="duelist", skill_level=1.5)
        GreedyAgent(config)

def test_greedy_agent_decide_action():
    """Test that GreedyAgent produces valid actions."""
    config = AgentConfig(
        role="duelist",
        skill_level=0.7,
        personality={"aggression": 0.8, "patience": 0.3, "teamplay": 0.5}
    )
    agent = GreedyAgent(config)
    
    # Test buy phase
    obs = create_minimal_observation(
        phase='buy',
        creds=4000,
        weapon=None,
        shield=None
    )
    action = agent.decide_action(obs, None)
    assert action['action_type'] == 'buy'
    assert action['buy']['weapon'] in {'Vandal', 'Phantom'}
    assert action['buy']['shield'] == 'heavy'
    
    # Test combat
    obs = create_minimal_observation(
        phase='round',
        visible_enemies=['enemy1']
    )
    action = agent.decide_action(obs, None)
    assert action['action_type'] == 'shoot'
    assert action['shoot']['target_id'] == 'enemy1'
    
    # Test planting
    obs = create_minimal_observation(
        phase='round',
        spike=True,
        at_plant_site=True
    )
    action = agent.decide_action(obs, None)
    assert action['action_type'] == 'plant'
    assert action['plant'] is True
    
    # Test defusing
    obs = create_minimal_observation(
        phase='round',
        spike_planted=True,
        at_spike=True
    )
    action = agent.decide_action(obs, None)
    assert action['action_type'] == 'defuse'
    assert action['defuse'] is True
    
    # Test idle when dead
    obs = create_minimal_observation(alive=False)
    action = agent.decide_action(obs, None)
    assert action['action_type'] == 'idle'

def test_agent_pool_management():
    """Test that AgentPool properly manages agents."""
    pool = AgentPool()
    
    # Register agent class
    pool.register_agent_class('greedy', GreedyAgent)
    
    # Get agent with specific criteria
    agent1 = pool.get_agent('duelist', 0.8, 'greedy')
    assert isinstance(agent1, GreedyAgent)
    assert agent1.role == 'duelist'
    assert abs(agent1.skill_level - 0.8) < 0.1
    
    # Get another agent with same criteria - should reuse existing
    agent2 = pool.get_agent('duelist', 0.79, 'greedy')
    assert agent1 is agent2  # Should be the same instance
    
    # Get agent with different criteria - should create new
    agent3 = pool.get_agent('sentinel', 0.6, 'greedy')
    assert agent3 is not agent1
    assert agent3.role == 'sentinel'
    
    # Test automatic agent type selection
    agent4 = pool.get_agent('controller', 0.9, 'greedy')  # High skill but force greedy
    assert agent4.skill_level == 0.9
    
    # Test invalid agent type
    with pytest.raises(ValueError):
        pool.get_agent('duelist', 0.8, 'invalid_type')
    
    # Reset all agents
    pool.reset_all()

def test_agent_personality_influence():
    """Test that agent personality affects decision making."""
    # Create aggressive agent
    aggressive_config = AgentConfig(
        role="duelist",
        skill_level=0.7,
        personality={"aggression": 1.0, "patience": 0.0, "teamplay": 0.5}
    )
    aggressive_agent = GreedyAgent(aggressive_config)
    
    # Create patient agent
    patient_config = AgentConfig(
        role="duelist",
        skill_level=0.7,
        personality={"aggression": 0.0, "patience": 1.0, "teamplay": 0.5}
    )
    patient_agent = GreedyAgent(patient_config)
    
    # Give both agents same observation
    obs = create_minimal_observation(
        phase='round',
        visible_enemies=[],
        location=(5.0, 5.0, 0.0)  # Some position that might trigger movement
    )
    
    # Run multiple trials to account for randomness
    patient_walking_count = 0
    aggressive_walking_count = 0
    trials = 100
    
    for _ in range(trials):
        aggressive_action = aggressive_agent.decide_action(obs, None)
        patient_action = patient_agent.decide_action(obs, None)
        
        if aggressive_action.get('move') and aggressive_action['move'].get('is_walking', False):
            aggressive_walking_count += 1
        if patient_action.get('move') and patient_action['move'].get('is_walking', False):
            patient_walking_count += 1
    
    # Patient agent should walk more often
    assert patient_walking_count > aggressive_walking_count

def test_agent_reset():
    """Test that agent reset works correctly."""
    config = AgentConfig(
        role="duelist",
        skill_level=0.7,
        personality={"aggression": 0.5, "patience": 0.5, "teamplay": 0.5}
    )
    agent = GreedyAgent(config)
    
    # Simulate some state
    agent.last_action = "some_action"
    agent.action_cooldown = 10
    
    # Reset
    agent.reset()
    
    # Check state was cleared
    assert agent.last_action is None
    assert agent.action_cooldown == 0

def test_agent_pool_config_loading():
    """Test that AgentPool can load configurations."""
    import tempfile
    import json
    
    # Create a temporary config file
    config = {
        "default_personalities": {
            "duelist": {"aggression": 0.8, "patience": 0.3, "teamplay": 0.5},
            "sentinel": {"aggression": 0.3, "patience": 0.8, "teamplay": 0.7}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump(config, f)
        config_path = f.name
    
    # Create pool with config
    pool = AgentPool(config_path=config_path)
    pool.register_agent_class('greedy', GreedyAgent)
    
    # Get agents and verify personality matches config
    duelist = pool.get_agent('duelist', 0.7, 'greedy')
    assert abs(duelist.weights['aggression'] - 0.8) < 0.1
    
    # Clean up
    import os
    os.unlink(config_path) 
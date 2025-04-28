# Agent System Documentation

## Overview

The agent system provides a flexible framework for implementing and managing AI agents in the VCT simulator. It supports multiple agent types (rule-based, RL, pro-based) with different skill levels and personalities.

## Architecture

```
ai/
├── agents/             # Agent implementations
│   ├── base.py        # Base agent interface
│   └── greedy.py      # Rule-based greedy agent
├── inference/          # Production inference code
│   └── agent_pool.py  # Agent management and caching
└── models/            # Trained model weights (for RL/pro agents)
```

## Components

### BaseAgent

The foundation of the agent system. Defines the interface that all agents must implement:

```python
class BaseAgent(ABC):
    @abstractmethod
    def decide_action(self, observation: Dict, game_state: Any) -> Dict:
        """Decide next action based on observation."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset agent's internal state."""
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type identifier."""
        pass
```

### AgentConfig

Configuration class for agents:

```python
@dataclass
class AgentConfig:
    role: str                      # duelist, controller, sentinel, initiator
    skill_level: float            # 0.0 to 1.0
    personality: Optional[Dict]    # Personality traits
    model_path: Optional[str]     # Path to model weights
```

### AgentPool

Manages agent instances for production use:

```python
pool = AgentPool()
pool.register_agent_class('greedy', GreedyAgent)

# Get agent based on role and skill
agent = pool.get_agent(
    role='duelist',
    skill_level=0.8,
    agent_type='greedy'  # optional
)
```

## Observation Space

The standard observation dictionary includes:

- **Identity**: id, team_id, role, agent
- **State**: location, direction, health, armor, alive
- **Movement**: velocity, is_walking, is_crouching, is_jumping
- **Equipment**: creds, weapon, shield, spike
- **Perception**: visible_enemies, heard_sounds, known_enemy_positions
- **Team**: team_alive, team_confidence, current_strategy
- **Game**: round_number, phase, spike_planted, spike_time_remaining

## Action Space

The standard action dictionary includes:

- **action_type**: Primary action type
- **move**: Movement parameters (direction, walking, crouching)
- **shoot**: Shooting parameters (target_id)
- **plant/defuse**: Boolean flags
- **buy**: Buy decisions (weapon, shield, abilities)
- **use_ability**: Ability usage parameters
- **communicate**: Communication content

## Usage Examples

### Creating a New Agent

```python
from app.simulation.ai.agents.base import BaseAgent, AgentConfig

class MyAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        # Initialize agent-specific state

    def decide_action(self, observation, game_state):
        # Implement decision logic
        return {
            'action_type': 'move',
            'move': {'direction': (1.0, 0.0)}
        }

    def reset(self):
        # Reset agent state
        pass

    @property
    def agent_type(self):
        return 'my_agent'
```

### Using Agents in Simulation

```python
# Initialize agent pool
pool = AgentPool()
pool.register_agent_class('my_agent', MyAgent)

# Create agents for players
agents_dict = {}
for player in players:
    agent = pool.get_agent(
        role=player.role,
        skill_level=calculate_skill(player),
        agent_type='my_agent'
    )
    agents_dict[player.id] = agent

# Use in simulation loop
for player_id, agent in agents_dict.items():
    obs = players[player_id].get_observation(round_obj, team_blackboard)
    action = agent.decide_action(obs, round_obj)
    # Apply action to simulation
```

## Personality System

Agents can be configured with personality traits that influence their decision-making:

- **aggression**: Affects combat engagement and positioning (0.0-1.0)
- **patience**: Affects movement speed and timing (0.0-1.0)
- **teamplay**: Affects communication and utility usage (0.0-1.0)

Example personality profiles:

```python
# Aggressive duelist
duelist_personality = {
    "aggression": 0.8,
    "patience": 0.3,
    "teamplay": 0.5
}

# Patient sentinel
sentinel_personality = {
    "aggression": 0.3,
    "patience": 0.8,
    "teamplay": 0.7
}
```

## Configuration

Agents can be configured via JSON files:

```json
{
    "default_personalities": {
        "duelist": {"aggression": 0.8, "patience": 0.3, "teamplay": 0.5},
        "sentinel": {"aggression": 0.3, "patience": 0.8, "teamplay": 0.7}
    },
    "skill_thresholds": {
        "pro": 0.8,
        "rl": 0.5
    }
}
```

## Testing

The agent system includes comprehensive tests:

- Unit tests for agent configuration and validation
- Behavioral tests for decision-making
- Integration tests with the simulation
- Personality influence tests
- Agent pool management tests

Run tests with:
```bash
pytest tests/test_agent_system.py -v
``` 
from typing import Dict, List, Optional, Type
import random
from pathlib import Path
import json

from ..agents.base import BaseAgent, AgentConfig
from ..agents.greedy import GreedyAgent
from ..agents.rl_agent import RLAgent
from ..agents.pro_agent import ProAgent

class AgentPool:
    """
    Manages a pool of agents for production use.
    Handles agent creation, caching, and selection based on role and skill level.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the agent pool.
        
        Args:
            config_path: Optional path to a JSON config file specifying agent configurations
        """
        self.agents: Dict[str, List[BaseAgent]] = {
            'duelist': [],
            'controller': [],
            'sentinel': [],
            'initiator': []
        }
        
        # Register default agent types
        self.agent_classes: Dict[str, Type[BaseAgent]] = {
            'greedy': GreedyAgent,
            'rl': RLAgent,
            'pro': ProAgent
        }
        
        # Load default personalities and configurations
        self.default_personalities: Dict[str, Dict[str, float]] = {
            'duelist': {
                'aggression': 0.8,
                'patience': 0.3,
                'teamplay': 0.5
            },
            'controller': {
                'aggression': 0.4,
                'patience': 0.7,
                'teamplay': 0.8
            },
            'sentinel': {
                'aggression': 0.3,
                'patience': 0.8,
                'teamplay': 0.7
            },
            'initiator': {
                'aggression': 0.5,
                'patience': 0.6,
                'teamplay': 0.7
            }
        }
        
        # Skill thresholds for agent type selection
        self.skill_thresholds: Dict[str, float] = {
            'pro': 0.8,  # High skill -> pro agent
            'rl': 0.5    # Medium skill -> RL agent
        }
        
        if config_path:
            self._load_config(config_path)
    
    def register_agent_class(self, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register a new agent class with the pool.
        
        Args:
            agent_type: The type identifier for this agent class (e.g., 'rl', 'greedy')
            agent_class: The agent class to register
        """
        self.agent_classes[agent_type] = agent_class
    
    def get_agent(self, role: str, skill_level: float, agent_type: Optional[str] = None,
                  personality: Optional[Dict[str, float]] = None) -> BaseAgent:
        """
        Get an appropriate agent based on role and skill level.
        
        Args:
            role: The desired agent role
            skill_level: The desired skill level (0.0 to 1.0)
            agent_type: Optional specific agent type to use
            personality: Optional personality traits to override defaults
            
        Returns:
            An agent instance matching the criteria
        """
        if role not in self.agents:
            raise ValueError(f"Invalid role: {role}")
            
        # First try to find an existing agent with matching criteria
        matching_agents = [
            agent for agent in self.agents[role]
            if abs(agent.skill_level - skill_level) < 0.1 and
            (agent_type is None or agent.agent_type == agent_type)
        ]
        
        if matching_agents:
            return random.choice(matching_agents)
            
        # If no matching agent exists, create a new one
        return self._create_agent(role, skill_level, agent_type, personality)
    
    def _create_agent(self, role: str, skill_level: float, 
                     agent_type: Optional[str] = None,
                     personality: Optional[Dict[str, float]] = None) -> BaseAgent:
        """Create a new agent with the specified parameters."""
        # If no specific agent type requested, choose based on skill level
        if agent_type is None:
            if skill_level > self.skill_thresholds['pro']:
                agent_type = 'pro'  # Use pro-based agent for high skill
            elif skill_level > self.skill_thresholds['rl']:
                agent_type = 'rl'   # Use RL agent for medium skill
            else:
                agent_type = 'greedy'  # Use rule-based for low skill
        
        if agent_type not in self.agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        # Get personality from config or generate
        if personality is None:
            personality = self.default_personalities.get(role)
            if not personality:
                personality = self._generate_personality(role, skill_level)
        
        # Create configuration
        config = AgentConfig(
            role=role,
            skill_level=skill_level,
            personality=personality,
            model_path=self._get_model_path(agent_type, role, skill_level)
        )
        
        # Create agent
        agent = self.agent_classes[agent_type](config)
        
        # Add to pool
        self.agents[role].append(agent)
        
        return agent
    
    def _generate_personality(self, role: str, skill_level: float) -> Dict[str, float]:
        """Generate a personality profile based on role and skill."""
        # Get base personality for role
        base = self.default_personalities.get(role, {
            'aggression': 0.5,
            'patience': 0.5,
            'teamplay': 0.5
        })
        
        # Add skill-based variations
        variations = {
            'aggression': random.uniform(-0.1, 0.1) + (skill_level - 0.5) * 0.2,
            'patience': random.uniform(-0.1, 0.1) + (skill_level - 0.5) * 0.2,
            'teamplay': random.uniform(-0.1, 0.1) + (skill_level - 0.5) * 0.3
        }
        
        # Combine base with variations and clamp values
        return {
            trait: max(0.0, min(1.0, base.get(trait, 0.5) + variations[trait]))
            for trait in ['aggression', 'patience', 'teamplay']
        }
    
    def _get_model_path(self, agent_type: str, role: str, skill_level: float) -> Optional[str]:
        """Get the path to the model weights for this agent configuration."""
        if agent_type not in {'rl', 'pro'}:
            return None
            
        # Convert skill level to tier
        tier = self._skill_to_tier(skill_level)
        
        # Construct path
        model_dir = Path(__file__).parent.parent / 'models'
        model_path = model_dir / f"{agent_type}_{role}_{tier}.pt"
        
        return str(model_path) if model_path.exists() else None
    
    def _skill_to_tier(self, skill_level: float) -> str:
        """Convert a skill level to a Valorant rank tier."""
        if skill_level >= 0.9:
            return 'radiant'
        elif skill_level >= 0.8:
            return 'immortal'
        elif skill_level >= 0.7:
            return 'diamond'
        elif skill_level >= 0.6:
            return 'platinum'
        elif skill_level >= 0.5:
            return 'gold'
        elif skill_level >= 0.4:
            return 'silver'
        else:
            return 'bronze'
    
    def _load_config(self, config_path: str) -> None:
        """Load agent configurations from a JSON file."""
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Load default personalities
            if "default_personalities" in config:
                self.default_personalities.update(config["default_personalities"])
            
            # Load skill thresholds
            if "skill_thresholds" in config:
                self.skill_thresholds.update(config["skill_thresholds"])
                
            # Load agent-specific configs
            if "agent_configs" in config:
                for agent_type, cfg in config["agent_configs"].items():
                    if agent_type in self.agent_classes:
                        # Could update agent-specific parameters here
                        pass
                
        except Exception as e:
            print(f"Warning: Failed to load agent config: {e}")
    
    def reset_all(self) -> None:
        """Reset all agents in the pool."""
        for agents in self.agents.values():
            for agent in agents:
                agent.reset()
    
    def get_agent_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics about agents in the pool."""
        stats = {role: {'total': 0} for role in self.agents}
        for role, agents in self.agents.items():
            stats[role]['total'] = len(agents)
            for agent in agents:
                agent_type = agent.agent_type
                stats[role][agent_type] = stats[role].get(agent_type, 0) + 1
        return stats 
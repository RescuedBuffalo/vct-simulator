from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentConfig:
    """Configuration for an agent."""
    role: str  # duelist, controller, sentinel, initiator
    skill_level: float  # 0.0 to 1.0
    personality: Optional[Dict[str, float]] = None  # Optional personality traits
    model_path: Optional[str] = None  # Path to saved model weights if applicable

class BaseAgent(ABC):
    """
    Base interface for all agents (RL, rule-based, pro-based, etc.)
    All agents must implement these methods to be used in the simulation.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def decide_action(self, observation: Dict[str, Any], game_state: Any) -> Dict[str, Any]:
        """
        Decide the next action based on current observation and game state.
        
        Args:
            observation: Dict containing the agent's observation of the game state
            game_state: The full game state object (for non-RL agents that need it)
            
        Returns:
            action_dict: Dict containing the chosen action with format:
                {
                    'action_type': str,  # move, shoot, plant, defuse, buy, use_ability, communicate
                    'move': Optional[Dict],  # movement parameters if moving
                    'shoot': Optional[Dict],  # shooting parameters if shooting
                    'plant': bool,  # True if planting
                    'defuse': bool,  # True if defusing
                    'buy': Optional[Dict],  # buy decisions if in buy phase
                    'use_ability': Optional[Dict],  # ability usage parameters
                    'communicate': Optional[Dict]  # communication content
                }
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset the agent's internal state between rounds."""
        pass
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the type of agent (e.g., 'rl', 'greedy', 'pro')"""
        pass
    
    @property
    def role(self) -> str:
        """Get the agent's role."""
        return self.config.role
    
    @property
    def skill_level(self) -> float:
        """Get the agent's skill level."""
        return self.config.skill_level
    
    def _validate_config(self) -> None:
        """Validate the agent configuration."""
        if not 0.0 <= self.config.skill_level <= 1.0:
            raise ValueError(f"Skill level must be between 0.0 and 1.0, got {self.config.skill_level}")
        if self.config.role not in {"duelist", "controller", "sentinel", "initiator"}:
            raise ValueError(f"Invalid role: {self.config.role}") 
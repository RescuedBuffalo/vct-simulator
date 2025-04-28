import random
import math
from typing import Dict, Any, Optional, Tuple

from .base import BaseAgent, AgentConfig

class GreedyAgent(BaseAgent):
    """
    A rule-based agent that makes decisions based on simple heuristics and personality traits.
    Implements the BaseAgent interface with deterministic decision-making rules.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.last_action = None
        self.action_cooldown = 0
        self.weights = config.personality or {
            "aggression": 0.5,
            "patience": 0.5,
            "teamplay": 0.5
        }
    
    def decide_action(self, observation: Dict, game_state: Any) -> Dict:
        """
        Decide the next action based on current observation and personality traits.
        """
        if not observation['alive']:
            return {'action_type': 'idle'}
            
        # Buy phase logic
        if observation['phase'] == 'buy':
            return self._decide_buy(observation)
            
        # Combat phase logic
        if observation['visible_enemies']:
            return self._decide_combat(observation)
            
        # Objective phase logic
        if self._should_plant(observation):
            return {'action_type': 'plant', 'plant': True}
            
        if self._should_defuse(observation):
            return {'action_type': 'defuse', 'defuse': True}
            
        # Movement phase
        return self._decide_movement(observation)
    
    def _decide_buy(self, observation: Dict) -> Dict:
        """Decide what equipment to buy."""
        if observation['creds'] < 1000:
            return {'action_type': 'idle'}
            
        buy_action = {'action_type': 'buy', 'buy': {'shield': None}}
        
        # More aggressive agents prefer rifles
        if observation['creds'] >= 2900 and self.weights['aggression'] > 0.3:
            buy_action['buy']['weapon'] = 'Vandal' if self.weights['aggression'] > 0.6 else 'Phantom'
        elif observation['creds'] >= 1600:
            buy_action['buy']['weapon'] = 'Spectre'
            
        # Shield buying logic - buy heavy if we can afford it and have a good weapon
        if observation['creds'] >= 2900:  # If we can afford rifle + heavy shield
            buy_action['buy']['shield'] = 'heavy'
        elif observation['creds'] >= 1000:  # Otherwise buy based on patience
            if self.weights['patience'] > 0.4:
                buy_action['buy']['shield'] = 'heavy' if observation['creds'] >= 1000 else 'light'
            else:
                buy_action['buy']['shield'] = 'light'
            
        return buy_action
    
    def _decide_combat(self, observation: Dict) -> Dict:
        """Decide combat actions based on personality."""
        # Aggressive agents shoot more readily
        if self.weights['aggression'] > random.random():
            return {
                'action_type': 'shoot',
                'shoot': {'target_id': observation['visible_enemies'][0]}
            }
            
        # Patient agents may hold fire or retreat
        if self.weights['patience'] > random.random():
            return self._decide_movement(observation, retreat=True)
            
        return {'action_type': 'idle'}
    
    def _decide_movement(self, observation: Dict, retreat: bool = False) -> Dict:
        """
        Decide movement based on personality traits.
        Patient agents walk more, aggressive agents run more.
        """
        # Base walking probability on patience
        should_walk = random.random() < self.weights['patience']
        
        # Direction influenced by aggression (more aggressive = more forward)
        direction = random.uniform(-math.pi, math.pi)
        if not retreat:
            # Bias towards forward movement based on aggression
            direction *= (1.0 - self.weights['aggression'])
        else:
            # When retreating, bias towards backward movement
            direction = math.pi + random.uniform(-math.pi/4, math.pi/4)
        
        return {
            'action_type': 'move',
            'move': {
                'direction': direction,
                'is_walking': should_walk,
                'is_crouching': should_walk and random.random() < self.weights['patience']
            }
        }
    
    def _should_plant(self, observation: Dict) -> bool:
        """Decide whether to plant the spike."""
        return (
            observation['spike'] and
            observation['at_plant_site'] and
            not observation['spike_planted']
        )
    
    def _should_defuse(self, observation: Dict) -> bool:
        """Decide whether to defuse the spike."""
        return (
            observation['spike_planted'] and
            observation['at_spike']
        )
    
    def reset(self) -> None:
        """Reset agent state."""
        self.last_action = None
        self.action_cooldown = 0
    
    @property
    def agent_type(self) -> str:
        """Return the type of this agent."""
        return 'greedy'
    
    def _decide_ability_use(self, obs: Dict[str, Any]) -> Optional[Dict]:
        """Decide whether to use an ability."""
        # This would check available abilities and use them based on situation
        return None
    
    def _closest_visible_enemy(self, obs: Dict[str, Any]) -> Optional[str]:
        """Find the closest visible enemy."""
        if not obs['visible_enemies']:
            return None
        return obs['visible_enemies'][0]  # For simplicity
    
    def _choose_movement_target(self, obs: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
        """Choose where to move based on role and situation."""
        # This would implement role-specific movement logic
        return None
    
    def _direction_to_target(self, source: Tuple[float, float, float], 
                           target: Tuple[float, float, float]) -> Tuple[float, float]:
        """Calculate normalized direction vector from source to target."""
        dx = target[0] - source[0]
        dy = target[1] - source[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            return (dx / length, dy / length)
        return (0.0, 0.0)
    
    def _get_movement_callout(self, obs: Dict[str, Any]) -> str:
        """Get an appropriate movement callout."""
        messages = [
            "Rotating!",
            "Moving up!",
            "Falling back!",
            "Watching flank!"
        ]
        return random.choice(messages) 
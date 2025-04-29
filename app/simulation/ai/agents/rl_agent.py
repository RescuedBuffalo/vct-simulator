import torch
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base import BaseAgent, AgentConfig

class RLAgent(BaseAgent):
    """
    A reinforcement learning agent that uses trained models for decision making.
    Supports loading different models based on role and skill level.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        if not config.model_path:
            raise ValueError("RL agent requires a model path")
            
        # Load the model
        self.model = self._load_model(config.model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Initialize state tracking
        self.last_observation = None
        self.last_action = None
        self.episode_memory: List[Dict] = []
        
        # Action mapping for converting network output to game actions
        self.action_mapping = {
            0: self._create_move_action,
            1: self._create_shoot_action,
            2: self._create_ability_action,
            3: self._create_plant_action,
            4: self._create_defuse_action,
            5: self._create_buy_action,
            6: self._create_communicate_action
        }
    
    def decide_action(self, observation: Dict[str, Any], game_state: Any) -> Dict[str, Any]:
        """Use the trained model to decide the next action."""
        if not observation['alive']:
            return {'action_type': 'idle'}
        
        # Convert observation to model input
        obs_tensor = self._preprocess_observation(observation)
        
        # Get model prediction
        with torch.no_grad():
            action_probs, value = self.model(obs_tensor)
            action_idx = torch.multinomial(action_probs, 1).item()
        
        # Convert model output to game action
        action = self.action_mapping[action_idx](observation, game_state)
        
        # Store for learning
        self.last_observation = observation
        self.last_action = action
        self.episode_memory.append({
            'observation': observation,
            'action': action,
            'value': value.item()
        })
        
        return action
    
    def _preprocess_observation(self, observation: Dict) -> torch.Tensor:
        """Convert observation dictionary to model input tensor."""
        # Extract relevant features
        features = []
        
        # Identity features
        features.extend([
            float(observation.get('team_id', 0)),
            float(observation.get('role_id', 0)),
        ])
        
        # State features
        features.extend([
            observation.get('health', 0) / 100.0,
            observation.get('armor', 0) / 100.0,
            float(observation.get('alive', False)),
        ])
        
        # Position and movement
        pos = observation.get('position', [0, 0, 0])
        vel = observation.get('velocity', [0, 0, 0])
        features.extend([
            pos[0] / 100.0, pos[1] / 100.0, pos[2] / 10.0,
            vel[0] / 10.0, vel[1] / 10.0, vel[2] / 10.0,
        ])
        
        # Equipment
        features.extend([
            observation.get('creds', 0) / 9000.0,
            float(observation.get('spike', False)),
        ])
        
        # Combat information
        features.extend([
            len(observation.get('visible_enemies', [])) / 5.0,
            len(observation.get('heard_sounds', [])) / 10.0,
        ])
        
        # Game state
        features.extend([
            observation.get('round_number', 0) / 25.0,
            float(observation.get('spike_planted', False)),
            observation.get('spike_time_remaining', 0) / 45.0,
        ])
        
        # Convert to tensor
        return torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
    
    def _create_move_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create a movement action based on model output."""
        return {
            'action_type': 'move',
            'move': {
                'direction': self._get_strategic_direction(obs),
                'is_walking': self._should_walk(obs),
                'is_crouching': self._should_crouch(obs)
            }
        }
    
    def _create_shoot_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create a shooting action based on model output."""
        if not obs.get('visible_enemies'):
            return self._create_move_action(obs, game_state)
            
        return {
            'action_type': 'shoot',
            'shoot': {
                'target_id': obs['visible_enemies'][0],
                'is_scoped': self._should_scope(obs),
                'burst_length': self._get_burst_length(obs)
            }
        }
    
    def _create_ability_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create an ability usage action based on model output."""
        ability = self._choose_ability(obs)
        if not ability:
            return self._create_move_action(obs, game_state)
            
        return {
            'action_type': 'use_ability',
            'use_ability': {
                'ability_name': ability,
                'target_position': self._get_ability_target(obs, ability)
            }
        }
    
    def _create_plant_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create a spike plant action."""
        if not (obs.get('spike') and obs.get('at_plant_site')):
            return self._create_move_action(obs, game_state)
            
        return {
            'action_type': 'plant',
            'plant': True
        }
    
    def _create_defuse_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create a spike defuse action."""
        if not (obs.get('spike_planted') and obs.get('at_spike')):
            return self._create_move_action(obs, game_state)
            
        return {
            'action_type': 'defuse',
            'defuse': True
        }
    
    def _create_buy_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create a buy action based on economy and strategy."""
        if obs.get('phase') != 'buy' or obs.get('creds', 0) < 800:
            return {'action_type': 'idle'}
            
        return {
            'action_type': 'buy',
            'buy': self._get_buy_loadout(obs)
        }
    
    def _create_communicate_action(self, obs: Dict, game_state: Any) -> Dict:
        """Create a team communication action."""
        return {
            'action_type': 'communicate',
            'communicate': {
                'message': self._get_strategic_callout(obs),
                'type': 'voice'
            }
        }
    
    def _get_strategic_direction(self, obs: Dict) -> float:
        """Calculate strategic movement direction."""
        # Consider objectives, team positions, and known enemy positions
        if obs.get('spike_planted'):
            # Move towards spike if defending
            if obs.get('team_id') == 'defenders':
                return self._direction_to_position(obs['position'], obs.get('spike_position', [0, 0, 0]))
        elif obs.get('spike'):
            # Move towards nearest site if attacking with spike
            if obs.get('team_id') == 'attackers':
                nearest_site = self._find_nearest_site(obs['position'])
                if nearest_site:
                    return self._direction_to_position(obs['position'], nearest_site)
        
        # Default to role-based positioning
        return self._get_role_based_direction(obs)
    
    def _should_walk(self, obs: Dict) -> bool:
        """Decide if should walk based on situation."""
        return (
            obs.get('heard_sounds') or  # Enemies nearby
            obs.get('spike_planted') or  # Critical phase
            obs.get('spike')  # Carrying spike
        )
    
    def _should_crouch(self, obs: Dict) -> bool:
        """Decide if should crouch based on situation."""
        return bool(obs.get('visible_enemies')) and self._is_in_combat_range(obs)
    
    def _should_scope(self, obs: Dict) -> bool:
        """Decide if should scope based on weapon and distance."""
        if not obs.get('visible_enemies'):
            return False
        return self._get_enemy_distance(obs) > 20.0  # Long range
    
    def _get_burst_length(self, obs: Dict) -> int:
        """Decide burst length based on weapon and distance."""
        distance = self._get_enemy_distance(obs)
        if distance < 10.0:
            return 5  # Close range spray
        elif distance < 20.0:
            return 3  # Medium range burst
        return 1  # Long range tap
    
    def _choose_ability(self, obs: Dict) -> Optional[str]:
        """Choose which ability to use based on situation."""
        if not obs.get('abilities'):
            return None
            
        # Role-specific ability usage
        if self.config.role == 'duelist':
            if obs.get('visible_enemies') and 'flash' in obs['abilities']:
                return 'flash'
        elif self.config.role == 'controller':
            if not obs.get('visible_enemies') and 'smoke' in obs['abilities']:
                return 'smoke'
        elif self.config.role == 'sentinel':
            if obs.get('spike_planted') and 'trap' in obs['abilities']:
                return 'trap'
        elif self.config.role == 'initiator':
            if not obs.get('visible_enemies') and 'recon' in obs['abilities']:
                return 'recon'
        
        return None
    
    def _get_buy_loadout(self, obs: Dict) -> Dict:
        """Decide what equipment to buy."""
        creds = obs.get('creds', 0)
        loadout = {'shield': None}
        
        # Full buy threshold
        if creds >= 3900:
            loadout['weapon'] = 'Vandal' if self.config.role == 'duelist' else 'Phantom'
            loadout['shield'] = 'heavy'
            loadout['abilities'] = True
        # Force buy threshold
        elif creds >= 2000:
            loadout['weapon'] = 'Spectre'
            loadout['shield'] = 'light'
            loadout['abilities'] = True
        # Eco threshold
        elif creds >= 800:
            loadout['weapon'] = 'Classic'
            loadout['shield'] = 'light'
        
        return loadout
    
    def _get_strategic_callout(self, obs: Dict) -> str:
        """Generate appropriate strategic callout."""
        if obs.get('visible_enemies'):
            return f"Enemy spotted at {self._position_to_callout(obs['visible_enemies'][0])}"
        elif obs.get('heard_sounds'):
            return f"Steps at {self._position_to_callout(obs['heard_sounds'][0])}"
        elif obs.get('spike_planted'):
            return "Spike planted, rotating"
        return ""
    
    def reset(self) -> None:
        """Reset agent state between rounds."""
        self.last_observation = None
        self.last_action = None
        self.episode_memory.clear()
    
    @property
    def agent_type(self) -> str:
        return 'rl'
    
    @staticmethod
    def _load_model(model_path: str) -> torch.nn.Module:
        """Load the trained model from disk."""
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        return torch.load(model_path, map_location='cpu') 
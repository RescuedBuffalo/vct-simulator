import torch
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import random

from .base import BaseAgent, AgentConfig

class ProAgent(BaseAgent):
    """
    A pro-player based agent that mimics real player behaviors.
    Uses a combination of trained models and expert-designed heuristics.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        if not config.model_path:
            raise ValueError("Pro agent requires a model path")
            
        # Load behavior model
        self.model = self._load_model(config.model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Initialize state tracking
        self.current_strategy = None
        self.team_economy = {}
        self.known_enemy_positions = {}
        self.map_control = {}
        
        # Role-specific strategies
        self.strategies = {
            'duelist': ['entry', 'lurk', 'flank'],
            'controller': ['setup', 'anchor', 'retake'],
            'sentinel': ['lockdown', 'hold', 'retake'],
            'initiator': ['info', 'support', 'breach']
        }
        
        # Pro-style decision weights
        self.decision_weights = {
            'aggression': config.personality.get('aggression', 0.5),
            'patience': config.personality.get('patience', 0.5),
            'teamplay': config.personality.get('teamplay', 0.5),
            'utility_usage': 0.8,  # Pro players use utility effectively
            'positioning': 0.9,    # Pro players have excellent positioning
            'timing': 0.85,        # Pro players have good timing
            'economy': 0.95        # Pro players manage economy well
        }
    
    def decide_action(self, observation: Dict[str, Any], game_state: Any) -> Dict[str, Any]:
        """Use pro-player behavior model to decide the next action."""
        if not observation['alive']:
            return {'action_type': 'idle'}
        
        # Update state tracking
        self._update_state_tracking(observation, game_state)
        
        # Choose strategy if needed
        if not self.current_strategy:
            self.current_strategy = self._choose_strategy(observation)
        
        # Get model prediction
        obs_tensor = self._preprocess_observation(observation)
        with torch.no_grad():
            action_probs = self.model(obs_tensor)
        
        # Combine model output with pro heuristics
        action = self._combine_model_and_heuristics(action_probs, observation)
        
        return action
    
    def _update_state_tracking(self, obs: Dict, game_state: Any):
        """Update internal state tracking."""
        # Update team economy
        for player_id, creds in obs.get('team_creds', {}).items():
            self.team_economy[player_id] = creds
        
        # Update known enemy positions
        for enemy_id, pos in obs.get('known_enemy_positions', {}).items():
            self.known_enemy_positions[enemy_id] = {
                'position': pos,
                'last_seen': obs.get('game_time', 0)
            }
        
        # Update map control based on team positions
        self._update_map_control(obs)
    
    def _choose_strategy(self, obs: Dict) -> str:
        """Choose a role-appropriate strategy based on game state."""
        available_strategies = self.strategies[self.config.role]
        
        # Factors influencing strategy choice
        factors = {
            'round_type': 'eco' if obs.get('team_creds_avg', 0) < 2000 else 'full_buy',
            'player_count_diff': obs.get('team_players_alive', 0) - obs.get('enemy_players_alive', 0),
            'spike_state': 'planted' if obs.get('spike_planted') else 'default',
            'map_control': self._evaluate_map_control()
        }
        
        # Choose strategy based on situation
        if self.config.role == 'duelist':
            if factors['round_type'] == 'eco':
                return 'lurk'  # Save weapon
            elif factors['map_control'].get('mid', 0) > 0.7:
                return 'flank'  # Good mid control
            else:
                return 'entry'  # Default duelist role
                
        elif self.config.role == 'controller':
            if factors['spike_state'] == 'planted':
                return 'anchor'
            elif factors['player_count_diff'] < 0:
                return 'retake'  # Playing retake with numbers disadvantage
            else:
                return 'setup'  # Default controller role
                
        elif self.config.role == 'sentinel':
            if factors['spike_state'] == 'planted':
                return 'lockdown'  # Hold site
            elif factors['player_count_diff'] < 0:
                return 'retake'
            else:
                return 'hold'  # Default sentinel role
                
        else:  # initiator
            if factors['round_type'] == 'eco':
                return 'info'  # Gather info safely
            elif factors['player_count_diff'] < 0:
                return 'breach'  # Create opportunities
            else:
                return 'support'  # Default initiator role
    
    def _combine_model_and_heuristics(self, model_probs: torch.Tensor, obs: Dict) -> Dict:
        """Combine model predictions with pro-player heuristics."""
        action_type = self._get_action_type(model_probs, obs)
        
        if action_type == 'buy':
            return self._create_pro_buy_action(obs)
        elif action_type == 'move':
            return self._create_pro_movement_action(obs)
        elif action_type == 'shoot':
            return self._create_pro_combat_action(obs)
        elif action_type == 'use_ability':
            return self._create_pro_utility_action(obs)
        elif action_type == 'plant':
            return {'action_type': 'plant', 'plant': True}
        elif action_type == 'defuse':
            return {'action_type': 'defuse', 'defuse': True}
        else:
            return {'action_type': 'idle'}
    
    def _create_pro_buy_action(self, obs: Dict) -> Dict:
        """Create a pro-style buy decision."""
        team_creds_avg = sum(self.team_economy.values()) / len(self.team_economy)
        
        # Pro buy strategies
        if obs.get('creds', 0) >= 3900 and team_creds_avg >= 3500:
            # Full buy with team
            loadout = {
                'weapon': self._get_preferred_weapon(),
                'shield': 'heavy',
                'abilities': True
            }
        elif obs.get('creds', 0) >= 2000 and team_creds_avg < 2000:
            # Save for team buy next round
            loadout = {
                'weapon': 'Classic',
                'shield': 'light',
                'abilities': False
            }
        else:
            # Force buy or eco based on team economy
            can_force = all(creds >= 2000 for creds in self.team_economy.values())
            loadout = {
                'weapon': 'Spectre' if can_force else 'Classic',
                'shield': 'light',
                'abilities': can_force
            }
        
        return {
            'action_type': 'buy',
            'buy': loadout
        }
    
    def _create_pro_movement_action(self, obs: Dict) -> Dict:
        """Create a pro-style movement action."""
        # Get strategic position based on role and strategy
        target_pos = self._get_strategic_position(obs)
        
        # Calculate movement parameters
        direction = self._calculate_safe_path(obs['position'], target_pos)
        should_walk = self._should_walk_pro(obs)
        should_crouch = self._should_crouch_pro(obs)
        
        return {
            'action_type': 'move',
            'move': {
                'direction': direction,
                'is_walking': should_walk,
                'is_crouching': should_crouch
            }
        }
    
    def _create_pro_combat_action(self, obs: Dict) -> Dict:
        """Create a pro-style combat action."""
        if not obs.get('visible_enemies'):
            return self._create_pro_movement_action(obs)
        
        # Get best target based on threat level and position
        target = self._prioritize_target(obs)
        
        # Determine combat style based on weapon and range
        combat_style = self._get_combat_style(obs, target)
        
        return {
            'action_type': 'shoot',
            'shoot': {
                'target_id': target['id'],
                'is_scoped': combat_style['scope'],
                'burst_length': combat_style['burst'],
                'aim_location': combat_style['aim_point']  # head, body, legs
            }
        }
    
    def _create_pro_utility_action(self, obs: Dict) -> Dict:
        """Create a pro-style utility usage action."""
        if not obs.get('abilities'):
            return self._create_pro_movement_action(obs)
        
        # Choose ability and target based on strategy
        ability, target = self._choose_utility_action(obs)
        if not ability:
            return self._create_pro_movement_action(obs)
        
        return {
            'action_type': 'use_ability',
            'use_ability': {
                'ability_name': ability,
                'target_position': target,
                'timing': self._get_utility_timing(obs)
            }
        }
    
    def _get_preferred_weapon(self) -> str:
        """Get preferred weapon based on role and playstyle."""
        if self.config.role == 'duelist':
            return 'Vandal' if self.decision_weights['aggression'] > 0.6 else 'Phantom'
        elif self.config.role == 'controller':
            return 'Phantom'  # Better for smoke spraying
        elif self.config.role == 'sentinel':
            return 'Vandal' if self.decision_weights['positioning'] > 0.8 else 'Phantom'
        else:  # initiator
            return 'Phantom' if self.decision_weights['teamplay'] > 0.7 else 'Vandal'
    
    def _get_strategic_position(self, obs: Dict) -> Tuple[float, float, float]:
        """Get strategic position based on role and strategy."""
        if self.current_strategy == 'entry':
            return self._get_entry_position(obs)
        elif self.current_strategy == 'lurk':
            return self._get_lurk_position(obs)
        elif self.current_strategy == 'hold':
            return self._get_hold_position(obs)
        elif self.current_strategy == 'retake':
            return self._get_retake_position(obs)
        else:
            return self._get_default_position(obs)
    
    def _prioritize_target(self, obs: Dict) -> Dict:
        """Prioritize targets based on threat level and position."""
        targets = []
        for enemy_id in obs.get('visible_enemies', []):
            threat_level = self._calculate_threat_level(enemy_id, obs)
            targets.append({
                'id': enemy_id,
                'threat': threat_level,
                'position': obs['enemy_positions'][enemy_id]
            })
        
        return max(targets, key=lambda x: x['threat'])
    
    def _get_combat_style(self, obs: Dict, target: Dict) -> Dict:
        """Determine optimal combat style based on situation."""
        distance = self._calculate_distance(obs['position'], target['position'])
        weapon = obs.get('weapon', 'Classic')
        
        if distance > 20.0:  # Long range
            return {
                'scope': True,
                'burst': 1,
                'aim_point': 'head'
            }
        elif distance > 10.0:  # Medium range
            return {
                'scope': weapon in ['Vandal', 'Phantom', 'Guardian'],
                'burst': 2,
                'aim_point': 'head'
            }
        else:  # Close range
            return {
                'scope': False,
                'burst': 4,
                'aim_point': 'body'
            }
    
    def _choose_utility_action(self, obs: Dict) -> Tuple[Optional[str], Optional[Tuple[float, float, float]]]:
        """Choose utility action based on strategy and situation."""
        if self.current_strategy == 'setup':
            return self._get_setup_utility(obs)
        elif self.current_strategy == 'retake':
            return self._get_retake_utility(obs)
        elif self.current_strategy == 'entry':
            return self._get_entry_utility(obs)
        else:
            return None, None
    
    def reset(self) -> None:
        """Reset agent state between rounds."""
        self.current_strategy = None
        self.team_economy.clear()
        self.known_enemy_positions.clear()
        self.map_control.clear()
    
    @property
    def agent_type(self) -> str:
        return 'pro'
    
    @staticmethod
    def _load_model(model_path: str) -> torch.nn.Module:
        """Load the trained behavior model."""
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        return torch.load(model_path, map_location='cpu') 
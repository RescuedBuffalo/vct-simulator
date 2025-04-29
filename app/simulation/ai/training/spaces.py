import numpy as np
from typing import Dict, Tuple, Any
from gymnasium import spaces

class ObservationSpace:
    """
    Defines the observation space for the RL agent.
    Handles encoding game state into normalized observations.
    """
    def __init__(self):
        # Define observation space components and their ranges
        self.components = {
            # Identity features
            'team_id': (-1, 1),  # -1: Attackers, 1: Defenders
            'role_id': (-1, 1),  # -1: Duelist, -0.5: Controller, 0: Sentinel, 0.5: Initiator
            
            # State features
            'health': (-1, 1),  # Normalized from 0-100
            'armor': (-1, 1),  # Normalized from 0-50
            'alive': (-1, 1),  # -1: Dead, 1: Alive
            'position_x': (-1, 1),  # Normalized map coordinates
            'position_y': (-1, 1),  # Normalized map coordinates
            'position_z': (-1, 1),  # Normalized height
            'velocity_x': (-1, 1),  # Normalized velocity
            'velocity_y': (-1, 1),  # Normalized velocity
            'velocity_z': (-1, 1),  # Normalized velocity
            'direction_x': (-1, 1),  # Normalized direction
            'direction_y': (-1, 1),  # Normalized direction
            
            # Equipment features
            'creds': (-1, 1),  # Normalized from 0-9000
            'has_spike': (-1, 1),  # -1: No, 1: Yes
            'has_primary': (-1, 1),  # -1: No, 1: Yes
            'has_shield': (-1, 1),  # -1: No, 1: Yes
            'ability_charges': (-1, 1),  # Normalized from 0-4
            
            # Combat features
            'enemies_visible': (-1, 1),  # Normalized from 0-5
            'enemies_heard': (-1, 1),  # Normalized from 0-5
            'distance_to_nearest': (-1, 1),  # Normalized from 0-100
            'damage_dealt': (-1, 1),  # Normalized from 0-150
            'damage_taken': (-1, 1),  # Normalized from 0-150
            
            # Game state features
            'round_number': (-1, 1),  # Normalized from 0-25
            'round_time': (-1, 1),  # Normalized from 0-100
            'spike_planted': (-1, 1),  # -1: No, 1: Yes
            'spike_time': (-1, 1),  # Normalized from 0-45
            'team_alive': (-1, 1),  # Normalized from 0-5
            'enemy_alive': (-1, 1)  # Normalized from 0-5
        }
        
        # Calculate total observation size
        self.size = len(self.components)
        self.shape = (self.size,)
        
        # Create bounds arrays
        self.low = np.array([v[0] for v in self.components.values()], dtype=np.float32)
        self.high = np.array([v[1] for v in self.components.values()], dtype=np.float32)
        
        # Create gym space
        self.space = spaces.Box(low=self.low, high=self.high, dtype=np.float32)
    
    def encode(self, game_state: Any) -> np.ndarray:
        """Convert game state to normalized observation vector."""
        obs = np.zeros(self.size, dtype=np.float32)
        
        # Extract features from game state
        for i, (key, (low, high)) in enumerate(self.components.items()):
            # Get raw value from game state
            raw_value = self._get_feature(game_state, key)
            # Normalize to [-1, 1] range based on feature type
            if key in ['team_id', 'role_id', 'alive', 'has_spike', 'has_primary', 'has_shield', 'spike_planted']:
                # Binary or categorical features
                obs[i] = raw_value
            else:
                # Continuous features
                value_range = self._get_feature_range(key)
                if value_range[1] > value_range[0]:
                    # Normalize to [-1, 1]
                    obs[i] = 2.0 * (raw_value - value_range[0]) / (value_range[1] - value_range[0]) - 1.0
                else:
                    obs[i] = raw_value
        
        return obs
    
    def _get_feature_range(self, feature: str) -> Tuple[float, float]:
        """Get the raw value range for a feature."""
        ranges = {
            'health': (0, 100),
            'armor': (0, 50),
            'position_x': (-100, 100),
            'position_y': (-100, 100),
            'position_z': (-10, 10),
            'velocity_x': (-10, 10),
            'velocity_y': (-10, 10),
            'velocity_z': (-10, 10),
            'direction_x': (-1, 1),
            'direction_y': (-1, 1),
            'creds': (0, 9000),
            'ability_charges': (0, 4),
            'enemies_visible': (0, 5),
            'enemies_heard': (0, 5),
            'distance_to_nearest': (0, 100),
            'damage_dealt': (0, 150),
            'damage_taken': (0, 150),
            'round_number': (0, 25),
            'round_time': (0, 100),
            'spike_time': (0, 45),
            'team_alive': (0, 5),
            'enemy_alive': (0, 5)
        }
        return ranges.get(feature, (-1, 1))
    
    def _get_feature(self, game_state: Any, feature: str) -> float:
        """Extract a specific feature from the game state."""
        # This would need to be implemented based on your game state structure
        # For now, return default values
        defaults = {
            'team_id': -1,  # Attackers
            'role_id': -1,  # Duelist
            'health': 100,
            'armor': 0,
            'alive': 1,
            'position_x': 0,
            'position_y': 0,
            'position_z': 0,
            'velocity_x': 0,
            'velocity_y': 0,
            'velocity_z': 0,
            'direction_x': 1,
            'direction_y': 0,
            'creds': 800,
            'has_spike': -1,
            'has_primary': -1,
            'has_shield': -1,
            'ability_charges': 2,
            'enemies_visible': 0,
            'enemies_heard': 0,
            'distance_to_nearest': 50,
            'damage_dealt': 0,
            'damage_taken': 0,
            'round_number': 1,
            'round_time': 90,
            'spike_planted': -1,
            'spike_time': 45,
            'team_alive': 5,
            'enemy_alive': 5
        }
        return defaults.get(feature, 0.0)

class ActionSpace:
    """
    Defines the action space for the RL agent.
    Handles encoding and decoding of actions.
    """
    def __init__(self):
        # Define action components
        self.components = {
            'action_type': 6,  # move, shoot, plant, defuse, buy, idle
            'move_x': (-1, 1),  # Movement direction X
            'move_y': (-1, 1),  # Movement direction Y
            'is_walking': (0, 1),
            'is_crouching': (0, 1),
            'aim_x': (-1, 1),  # Aim direction X
            'aim_y': (-1, 1),  # Aim direction Y
            'trigger': (0, 1)  # Shoot trigger
        }
        
        # Calculate total action size
        self.size = len(self.components)
        self.shape = (self.size,)
        
        # Create bounds arrays
        self.low = np.array([-1] * self.size, dtype=np.float32)
        self.high = np.array([1] * self.size, dtype=np.float32)
        
        # Create gym space
        self.space = spaces.Box(low=self.low, high=self.high, dtype=np.float32)
    
    def decode(self, action: np.ndarray) -> Dict:
        """Convert normalized action vector to game command."""
        if action.shape != self.shape:
            raise ValueError(f"Action shape {action.shape} does not match expected shape {self.shape}")
        
        if np.any(action < -1) or np.any(action > 1):
            raise ValueError("Action values must be between -1 and 1")
        
        # Determine action type (using first component)
        action_types = ['move', 'shoot', 'plant', 'defuse', 'buy', 'idle']
        action_idx = int((action[0] + 1) * len(action_types) / 2) % len(action_types)
        action_type = action_types[action_idx]
        
        # Create command based on action type
        command = {'action_type': action_type}
        
        if action_type == 'move':
            command['move'] = {
                'direction': (float(action[1]), float(action[2])),
                'is_walking': bool(action[3] > 0),
                'is_crouching': bool(action[4] > 0)
            }
        elif action_type == 'shoot':
            command['shoot'] = {
                'direction': (float(action[5]), float(action[6])),
                'trigger': bool(action[7] > 0)
            }
        elif action_type in ['plant', 'defuse']:
            command[action_type] = True
        elif action_type == 'buy':
            # Buy decisions would be handled by a separate system
            pass
        
        return command 
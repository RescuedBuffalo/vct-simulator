from typing import Dict, Any
import numpy as np

class RewardFunctions:
    """
    Collection of reward functions for different agent roles.
    Each function calculates rewards based on role-specific objectives and actions.
    """
    
    @staticmethod
    def common_reward(state: Dict[str, Any], stats: Dict[str, Any]) -> float:
        """
        Calculate common rewards applicable to all roles.
        
        Args:
            state: Current game state
            stats: Current episode statistics
            
        Returns:
            float: Common reward value
        """
        reward = 0.0
        
        # Round outcome rewards
        if state.get('round_won'):
            reward += 5.0
        elif state.get('round_lost'):
            reward -= 2.0
            
        # Survival reward
        if state.get('survived_round'):
            reward += 1.0
            
        # Economy management
        if state.get('good_economy'):  # Maintained good economy for the team
            reward += 0.5
            
        # Team play
        if stats.get('assists', 0) > 0:
            reward += 0.5 * stats['assists']
            
        # Objective play
        if state.get('spike_planted') or state.get('spike_defused'):
            reward += 2.0
            
        return reward
    
    @staticmethod
    def duelist_reward(state: Dict[str, Any], stats: Dict[str, Any]) -> float:
        """
        Calculate rewards for duelist role.
        Focuses on entry fragging, aggressive plays, and creating space.
        """
        reward = 0.0
        
        # Entry frags
        if state.get('entry_kill'):
            reward += 3.0
        elif state.get('entry_death'):
            reward -= 1.5
            
        # Trading
        if state.get('traded_kill'):
            reward += 1.0
            
        # Multi-kills
        kills_this_round = state.get('kills_this_round', 0)
        if kills_this_round >= 2:
            reward += 1.0 * kills_this_round
            
        # Space creation
        if state.get('space_created'):  # Measured by territory gained/map control
            reward += 1.0
            
        # Aggressive plays
        if state.get('successful_push'):
            reward += 1.5
            
        return reward
    
    @staticmethod
    def controller_reward(state: Dict[str, Any], stats: Dict[str, Any]) -> float:
        """
        Calculate rewards for controller role.
        Focuses on map control, utility usage, and team coordination.
        """
        reward = 0.0
        
        # Effective utility usage
        if state.get('utility_damage'):
            reward += 0.5
            
        # Area denial
        if state.get('area_denied'):
            reward += 1.0
            
        # Site control
        if state.get('site_control'):
            reward += 2.0
            
        # Team coordination
        if state.get('coordinated_push'):
            reward += 1.5
            
        # Post-plant positioning
        if state.get('good_post_plant'):
            reward += 1.0
            
        return reward
    
    @staticmethod
    def sentinel_reward(state: Dict[str, Any], stats: Dict[str, Any]) -> float:
        """
        Calculate rewards for sentinel role.
        Focuses on site defense, information gathering, and team protection.
        """
        reward = 0.0
        
        # Site defense
        if state.get('site_held'):
            reward += 2.0
            
        # Information gathering
        if state.get('enemy_detected'):
            reward += 0.5
            
        # Team protection
        if state.get('teammate_protected'):
            reward += 1.0
            
        # Utility value
        if state.get('utility_destroyed'):
            reward += 0.5
            
        # Flank prevention
        if state.get('flank_prevented'):
            reward += 1.5
            
        return reward
    
    @staticmethod
    def initiator_reward(state: Dict[str, Any], stats: Dict[str, Any]) -> float:
        """
        Calculate rewards for initiator role.
        Focuses on information gathering, team setup, and coordinated pushes.
        """
        reward = 0.0
        
        # Information gathering
        if state.get('enemy_revealed'):
            reward += 1.0
            
        # Team setup
        if state.get('successful_setup'):
            reward += 1.5
            
        # Flash assists
        if state.get('flash_assist'):
            reward += 1.0
            
        # Coordinated pushes
        if state.get('coordinated_push'):
            reward += 1.5
            
        # Utility value
        utility_value = state.get('utility_value', 0.0)
        reward += 0.5 * utility_value
        
        return reward 
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
import time
import random
import math

@dataclass
class EnemyInfo:
    """Information about an enemy player."""
    player_id: str
    position: Tuple[float, float]
    last_seen_time: float  # Simulation time when last spotted
    spotted_by: str  # ID of player who spotted them
    status: Optional[Dict] = None  # Any known status (health, weapon, etc.)
    confidence: float = 1.0  # 1.0 = certain, decreases over time

@dataclass
class SpikeInfo:
    """Information about the spike."""
    location: Optional[Tuple[float, float]] = None
    status: str = "unknown"  # "unknown", "carried", "dropped", "planted", "defused"
    carrier_id: Optional[str] = None
    plant_time: Optional[float] = None
    plant_site: Optional[str] = None
    seen_by: Optional[str] = None
    last_updated: float = 0.0

@dataclass
class StrategyCall:
    """A strategy call made by the IGL."""
    name: str  # e.g., "execute A", "rotate B", "default"
    issued_at: float  # Time when call was made
    issued_by: str  # IGL ID
    target_site: Optional[str] = None  # A, B, C, mid, etc.
    details: Optional[Dict] = None  # Additional strategy details

@dataclass
class AreaControl:
    """Information about map control."""
    area_id: str
    controlled_by: Optional[str] = None  # Team ID or None if contested/unknown
    confidence: float = 0.0  # How sure we are about control
    last_updated: float = 0.0

@dataclass
class EconomyInfo:
    """Team economy information."""
    team_credits: int = 0
    avg_credits: float = 0.0
    can_full_buy: bool = False
    can_half_buy: bool = False
    saving: bool = False
    last_updated: float = 0.0

@dataclass
class RoundPattern:
    """Observed pattern from previous rounds."""
    pattern_type: str  # e.g., "site_preference", "rotation_speed", "utility_usage"
    description: str
    confidence: float  # How certain we are in this pattern
    observed_rounds: List[int]  # Which rounds this was observed in
    
    
class Blackboard:
    """
    Stores and shares information between team members across rounds.
    Acts as the team's collective knowledge and memory.
    """
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.data = {}
        
        # Initialize standard knowledge categories
        self.data["enemy_info"] = {}  # player_id -> EnemyInfo
        self.data["spike_info"] = SpikeInfo()
        self.data["current_strategy"] = None  # Current strategy call
        self.data["previous_strategies"] = []  # List of previous strategies
        self.data["map_control"] = {}  # area_id -> AreaControl 
        self.data["economy"] = EconomyInfo()
        self.data["observed_patterns"] = []  # List of RoundPattern objects
        self.data["team_confidence"] = 1.0  # 0.0 to 2.0, 1.0 is neutral
        self.data["danger_areas"] = set()  # Set of areas that may be dangerous
        self.data["cleared_areas"] = set()  # Set of areas that have been cleared
        self.data["round_memory"] = {}  # round_num -> key data points about the round
        self.data["noise_events"] = []  # List of recent noise events
        self.data["warnings"] = []  # Current active warnings
        
        # Performance metrics
        self.data["win_streaks"] = 0  # Current win streak (negative for loss streak)
        self.data["rounds_won"] = 0
        self.data["rounds_lost"] = 0
        self.data["site_success_rate"] = {"A": 0.5, "B": 0.5, "C": 0.5}  # Default 50% success rate
        
        # Current round state
        self.data["alive_players"] = set()  # IDs of alive teammates
        self.data["current_round"] = 0
        self.data["current_half"] = 1
        self.data["is_attacking"] = False  # Whether team is currently attacking

    def get(self, key: str) -> Any:
        """Get a value from the blackboard."""
        return self.data.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the blackboard."""
        self.data[key] = value
    
    def update_enemy_info(self, player_id: str, position: Tuple[float, float], 
                         spotted_by: str, status: Dict = None) -> None:
        """Update information about an enemy player."""
        current_time = time.time()  # In a real sim, this would be simulation time
        
        self.data["enemy_info"][player_id] = EnemyInfo(
            player_id=player_id,
            position=position,
            last_seen_time=current_time,
            spotted_by=spotted_by,
            status=status,
            confidence=1.0  # Fresh sighting is 100% confident
        )
        
        # Add the enemy position to cleared areas since we can see it
        if position is not None:
            self.data["cleared_areas"].add(self._position_to_area_id(position))
            
    def update_spike_info(self, **kwargs) -> None:
        """Update information about the spike."""
        spike_info = self.data["spike_info"]
        
        # Update only the fields that are provided
        for key, value in kwargs.items():
            if hasattr(spike_info, key):
                setattr(spike_info, key, value)
        
        spike_info.last_updated = time.time()  # Update timestamp
    
    def set_strategy(self, name: str, issued_by: str, target_site: str = None, 
                    details: Dict = None) -> None:
        """Set the current team strategy."""
        # Save the previous strategy if it exists
        if self.data["current_strategy"]:
            self.data["previous_strategies"].append(self.data["current_strategy"])
            
        # Create a new strategy call
        self.data["current_strategy"] = StrategyCall(
            name=name,
            issued_at=time.time(),
            issued_by=issued_by,
            target_site=target_site,
            details=details
        )
    
    def record_pattern(self, pattern_type: str, description: str, 
                      round_num: int, confidence: float = 0.5) -> None:
        """Record an observed pattern about the enemy team."""
        # Check if a similar pattern already exists
        for pattern in self.data["observed_patterns"]:
            if pattern.pattern_type == pattern_type and pattern.description == description:
                # Update existing pattern
                pattern.observed_rounds.append(round_num)
                pattern.confidence = min(1.0, pattern.confidence + 0.1)  # Increase confidence slightly
                return
                
        # Create a new pattern
        new_pattern = RoundPattern(
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            observed_rounds=[round_num]
        )
        self.data["observed_patterns"].append(new_pattern)
    
    def update_team_confidence(self, delta: float) -> None:
        """Update team confidence based on events."""
        self.data["team_confidence"] = max(0.1, min(2.0, self.data["team_confidence"] + delta))
    
    def mark_area_dangerous(self, area_id: str) -> None:
        """Mark an area as potentially dangerous."""
        self.data["danger_areas"].add(area_id)
        
        # Remove from cleared areas if present
        if area_id in self.data["cleared_areas"]:
            self.data["cleared_areas"].remove(area_id)
    
    def mark_area_cleared(self, area_id: str) -> None:
        """Mark an area as cleared of enemies."""
        self.data["cleared_areas"].add(area_id)
        
        # Remove from danger areas if present
        if area_id in self.data["danger_areas"]:
            self.data["danger_areas"].remove(area_id)
    
    def add_warning(self, message: str, location: Optional[Tuple[float, float]] = None, 
                  expires_in: float = 10.0) -> None:
        """Add a temporary warning for the team."""
        warning = {
            "message": message,
            "location": location,
            "created_at": time.time(),
            "expires_at": time.time() + expires_in
        }
        self.data["warnings"].append(warning)
        
        # Clean up expired warnings
        self._clean_expired_warnings()
    
    def record_round_result(self, round_num: int, won: bool, end_condition: str, 
                          site: Optional[str] = None) -> None:
        """Record the result of a round for future strategy planning."""
        # Update win/loss counts
        if won:
            self.data["rounds_won"] += 1
            self.data["win_streaks"] = max(1, self.data["win_streaks"] + 1)
            # Increase confidence on win
            self.update_team_confidence(0.1)
        else:
            self.data["rounds_lost"] += 1
            self.data["win_streaks"] = min(-1, self.data["win_streaks"] - 1)
            # Decrease confidence on loss
            self.update_team_confidence(-0.1)
        
        # Update site success rates if applicable
        if site and self.data["is_attacking"]:
            sites = self.data["site_success_rate"]
            current = sites.get(site, 0.5)
            if won:
                # Increase success rate for this site
                sites[site] = current * 0.8 + 0.2  # Weighted update
            else:
                # Decrease success rate for this site
                sites[site] = current * 0.8  # Weighted update
        
        # Save key info about the round
        self.data["round_memory"][round_num] = {
            "won": won,
            "end_condition": end_condition,
            "site": site,
            "strategy": self.data["current_strategy"].name if self.data["current_strategy"] else "unknown",
            "alive_players": len(self.data["alive_players"]),
            "team_confidence": self.data["team_confidence"]
        }
        
        # Clear current round data to prepare for next round
        self.clear_round_data()
    
    def clear_round_data(self) -> None:
        """Clear data that should reset between rounds."""
        self.data["enemy_info"] = {}
        self.data["spike_info"] = SpikeInfo()
        self.data["current_strategy"] = None
        self.data["danger_areas"] = set()
        self.data["cleared_areas"] = set()
        self.data["noise_events"] = []
        self.data["warnings"] = []
        self.data["alive_players"] = set()
    
    def prepare_for_new_half(self) -> None:
        """Reset data for a new half (switch sides)."""
        # Switch attacking/defending side
        self.data["is_attacking"] = not self.data["is_attacking"]
        self.data["current_half"] += 1
        
        # Confidence slight reset toward neutral
        self.data["team_confidence"] = (self.data["team_confidence"] + 1.0) / 2.0
        
        # Reset site success rates for new side
        self.data["site_success_rate"] = {"A": 0.5, "B": 0.5, "C": 0.5}
        
        # Clear current round data
        self.clear_round_data()
    
    def suggest_strategy(self) -> Tuple[str, str, float]:
        """
        Suggest a strategy based on previous round data and patterns.
        Returns (strategy_name, target_site, confidence)
        """
        # This would be a more complex algorithm in a real implementation
        # Using site success rates, enemy patterns, and team confidence
        
        if self.data["is_attacking"]:
            # Attacking strategy suggestion
            if self.data["team_confidence"] > 1.5:
                # High confidence - aggressive plays
                return ("rush", self._get_best_site(), 0.8)
            elif self.data["team_confidence"] < 0.5:
                # Low confidence - play it safe
                return ("default", None, 0.7)
            else:
                # Normal confidence - balanced approach
                if random.random() < 0.7:
                    return ("execute", self._get_best_site(), 0.6)
                else:
                    return ("fake_and_rotate", self._get_worst_site(), 0.5)
        else:
            # Defending strategy suggestion
            if self.data["team_confidence"] > 1.5:
                # High confidence - aggressive defense
                return ("aggressive_defense", self._get_best_site(), 0.7)
            elif self.data["team_confidence"] < 0.5:
                # Low confidence - stack a site
                return ("stack_site", self._get_best_site(), 0.6)
            else:
                # Normal confidence - standard defense
                return ("standard_defense", None, 0.8)
    
    def _get_best_site(self) -> str:
        """Get the site with highest success rate."""
        rates = self.data["site_success_rate"]
        return max(rates.keys(), key=lambda k: rates[k])
    
    def _get_worst_site(self) -> str:
        """Get the site with lowest success rate."""
        rates = self.data["site_success_rate"]
        return min(rates.keys(), key=lambda k: rates[k])
    
    def _position_to_area_id(self, position: Tuple[float, float]) -> str:
        """Convert a position to an area ID (simplified)."""
        # Accept both 2D and 3D tuples, use only x and y
        x, y = position[:2]
        # Placeholder implementation - divide map into quadrants
        x_part = "east" if x > 0 else "west"
        y_part = "north" if y > 0 else "south"
        return f"{x_part}_{y_part}"
    
    def _clean_expired_warnings(self) -> None:
        """Remove expired warnings."""
        current_time = time.time()
        self.data["warnings"] = [w for w in self.data["warnings"] 
                              if w["expires_at"] > current_time]
    
    def decay_knowledge(self, elapsed_time: float) -> None:
        """
        Decay knowledge confidence over time.
        Call this periodically to simulate information becoming less reliable.
        """
        # Decay enemy position confidence
        for enemy_id, info in list(self.data["enemy_info"].items()):
            time_since_seen = time.time() - info.last_seen_time
            # Decay formula: exponential decay based on time
            decay_rate = 0.9 ** (elapsed_time / 5.0)
            info.confidence = max(0.1, info.confidence * decay_rate)
            
            # If confidence is very low, consider the information too stale
            if info.confidence < 0.2:
                del self.data["enemy_info"][enemy_id]
                
                # Area might be dangerous again if we haven't seen enemy in a while
                if info.position is not None:
                    area = self._position_to_area_id(info.position)
                    if area in self.data["cleared_areas"]:
                        self.data["cleared_areas"].remove(area)
                    self.data["danger_areas"].add(area)

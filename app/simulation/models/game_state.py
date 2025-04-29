from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .team import Team
from .player import Player
from .map import Map

@dataclass
class GameState:
    """
    Represents the overall state of a Valorant game.
    Tracks teams, players, rounds, and game progression.
    """
    # Teams and players
    teams: List[Team] = field(default_factory=list)
    current_round: int = 1
    max_rounds: int = 25
    
    # Round state
    round_phase: str = "buy"  # buy, combat, planting, planted, defusing, end
    round_time: float = 100.0  # Seconds remaining in round
    round_number: int = 1
    round_history: List[Dict] = field(default_factory=list)
    
    # Spike state
    spike_planted: bool = False
    spike_position: Optional[tuple] = None
    spike_time: float = 45.0  # Time until spike detonates
    spike_carrier: Optional[str] = None  # Player ID
    
    # Map state
    current_map: Optional[Map] = None
    
    def __post_init__(self):
        """Initialize any derived state."""
        if not self.teams:
            self.teams = [
                Team("Attackers", "Attackers"),
                Team("Defenders", "Defenders")
            ]
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        for team in self.teams:
            if team.id == team_id:
                return team
        return None
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        for team in self.teams:
            for player in team.players:
                if player.id == player_id:
                    return player
        return None
    
    def get_round_score(self) -> Dict[str, int]:
        """Get current round score for each team."""
        return {
            team.id: sum(1 for round in self.round_history if round['winner'] == team.id)
            for team in self.teams
        }
    
    def is_match_over(self) -> bool:
        """Check if match is over based on round wins."""
        scores = self.get_round_score()
        return any(score >= 13 for score in scores.values())
    
    def get_winning_team(self) -> Optional[Team]:
        """Get winning team if match is over."""
        if not self.is_match_over():
            return None
        scores = self.get_round_score()
        winning_team_id = max(scores.items(), key=lambda x: x[1])[0]
        return self.get_team(winning_team_id)
    
    def update(self, time_delta: float):
        """Update game state based on time passing."""
        if self.round_phase != "end":
            # Update round timer
            self.round_time = max(0.0, self.round_time - time_delta)
            
            # Update spike timer if planted
            if self.spike_planted:
                self.spike_time = max(0.0, self.spike_time - time_delta)
                
                # Check spike detonation
                if self.spike_time <= 0:
                    self.end_round("Attackers")
            
            # Check round time expiration
            if self.round_time <= 0:
                self.end_round("Defenders")
    
    def start_round(self):
        """Start a new round."""
        self.round_phase = "buy"
        self.round_time = 100.0
        self.spike_planted = False
        self.spike_position = None
        self.spike_time = 45.0
        self.spike_carrier = None
        
        # Reset player states
        for team in self.teams:
            for player in team.players:
                player.reset_for_round()
    
    def end_round(self, winning_team_id: str):
        """End the current round."""
        self.round_phase = "end"
        
        # Record round result
        self.round_history.append({
            'round_number': self.round_number,
            'winner': winning_team_id,
            'spike_planted': self.spike_planted,
            'time_remaining': self.round_time,
            'players_alive': {
                team.id: sum(1 for p in team.players if p.alive)
                for team in self.teams
            }
        })
        
        # Increment round counter
        self.round_number += 1
        
        # Start next round if match not over
        if not self.is_match_over():
            self.start_round()
    
    def get_state_dict(self) -> Dict:
        """Get a dictionary representation of the game state."""
        return {
            'round_number': self.round_number,
            'round_phase': self.round_phase,
            'round_time': self.round_time,
            'spike_planted': self.spike_planted,
            'spike_time': self.spike_time if self.spike_planted else None,
            'spike_position': self.spike_position,
            'spike_carrier': self.spike_carrier,
            'teams': {
                team.id: {
                    'score': self.get_round_score()[team.id],
                    'players_alive': sum(1 for p in team.players if p.alive),
                    'total_players': len(team.players)
                }
                for team in self.teams
            }
        } 
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from .player import Player
from .blackboard import Blackboard

@dataclass
class TeamStats:
    """Statistics for a team across a match."""
    rounds_won: int = 0
    rounds_lost: int = 0
    attack_rounds_won: int = 0
    defense_rounds_won: int = 0
    plants: int = 0
    defuses: int = 0
    first_bloods: int = 0
    clutches: int = 0
    thrifty_rounds: int = 0
    flawless_rounds: int = 0
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    economy: Dict[str, int] = field(default_factory=lambda: {
        "total_spent": 0,
        "avg_per_round": 0,
        "current_credits": 0
    })

@dataclass
class Team:
    """Represents a team in a Valorant match."""
    # Identity
    id: str
    name: str
    
    # Players
    players: List[Player] = field(default_factory=list)
    igl_id: Optional[str] = None  # ID of the in-game leader
    
    # Team Knowledge and Communication
    blackboard: Blackboard = field(default_factory=lambda: Blackboard(""))
    
    # Match State
    is_attacking: bool = False
    alive_players: Set[str] = field(default_factory=set)
    stats: TeamStats = field(default_factory=TeamStats)
    
    def __post_init__(self):
        """Initialize the team after creation."""
        # Set team ID in blackboard
        self.blackboard.team_id = self.id
        
        # Validate team size
        if len(self.players) != 5:
            raise ValueError("Team must have exactly 5 players")
        
        # If no IGL is designated, choose one based on highest clutch_iq
        if not self.igl_id:
            self.igl_id = max(self.players, key=lambda p: p.clutch_iq).id
        
        # Initialize alive players set
        self.alive_players = {p.id for p in self.players}
        
        # Set team ID for all players
        for player in self.players:
            player.team_id = self.id
    
    def get_igl(self) -> Optional[Player]:
        """Get the in-game leader player object."""
        return next((p for p in self.players if p.id == self.igl_id), None)
    
    def get_alive_players(self) -> List[Player]:
        """Get list of currently alive players."""
        return [p for p in self.players if p.id in self.alive_players]
    
    def update_alive_players(self) -> None:
        """Update the set of alive players based on player states."""
        self.alive_players = {p.id for p in self.players if p.alive}
        self.blackboard.set("alive_players", self.alive_players)
    
    def reset_for_round(self) -> None:
        """Reset team state for a new round."""
        # Reset all players
        for player in self.players:
            player.alive = True
            player.health = 100
            player.armor = 0 if player.shield is None else (50 if player.shield == "light" else 100)
            player.is_planting = False
            player.is_defusing = False
            player.plant_progress = 0.0
            player.defuse_progress = 0.0
            player.visible_enemies = []
            player.heard_sounds = []
            player.known_enemy_positions = {}
            player.status_effects = []
            player.velocity = (0.0, 0.0)
            player.utility_active = []
        
        # Reset alive players set
        self.alive_players = {p.id for p in self.players}
        
        # Update blackboard
        self.blackboard.clear_round_data()
    
    def switch_side(self) -> None:
        """Switch between attacking and defending."""
        self.is_attacking = not self.is_attacking
        self.blackboard.set("is_attacking", self.is_attacking)
        self.blackboard.prepare_for_new_half()
    
    def update_stats_after_round(self, won: bool, end_condition: str, site: Optional[str] = None) -> None:
        """Update team stats after a round."""
        if won:
            self.stats.rounds_won += 1
            if self.is_attacking:
                self.stats.attack_rounds_won += 1
            else:
                self.stats.defense_rounds_won += 1
        else:
            self.stats.rounds_lost += 1
        
        # Update total kills/deaths/assists
        self.stats.total_kills = sum(p.kills for p in self.players)
        self.stats.total_deaths = sum(p.deaths for p in self.players)
        self.stats.total_assists = sum(p.assists for p in self.players)
        
        # Record round result in blackboard
        self.blackboard.record_round_result(
            round_num=self.stats.rounds_won + self.stats.rounds_lost,
            won=won,
            end_condition=end_condition,
            site=site
        )
    
    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Get a player by their ID."""
        return next((p for p in self.players if p.id == player_id), None)
    
    def get_player_by_role(self, role: str) -> Optional[Player]:
        """Get the first player with a specific role."""
        return next((p for p in self.players if p.role == role), None)
    
    def get_players_by_role(self, role: str) -> List[Player]:
        """Get all players with a specific role."""
        return [p for p in self.players if p.role == role] 
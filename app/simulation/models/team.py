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
    """Represents a team in the game."""
    id: str
    name: str
    players: List[Player] = field(default_factory=list)
    igl_id: Optional[str] = None  # In-game leader
    blackboard: Optional[Blackboard] = None
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    economy: Dict[str, int] = field(default_factory=lambda: {
        'total_spent': 0,
        'avg_per_round': 0,
        'current_credits': 0
    })
    validate_size: bool = True  # Whether to validate team size
    _alive_players: Set[str] = field(default_factory=set)  # Private field for alive players
    
    def __post_init__(self):
        """Initialize the team after creation."""
        # Initialize blackboard
        self.blackboard = Blackboard(self.id)
        
        # Initialize alive players
        self._alive_players = {p.id for p in self.players if p.alive}
        
        # Validate team size
        if self.validate_size and len(self.players) != 5:
            raise ValueError("Team must have exactly 5 players")
    
    def add_player(self, player: Player):
        """Add a player to the team."""
        if player.team_id != self.id:
            raise ValueError(f"Player {player.id} belongs to team {player.team_id}, not {self.id}")
        self.players.append(player)
        
        # Validate team size after adding
        if self.validate_size and len(self.players) > 5:
            raise ValueError("Team cannot have more than 5 players")
    
    def remove_player(self, player_id: str):
        """Remove a player from the team."""
        self.players = [p for p in self.players if p.id != player_id]
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player by ID."""
        for player in self.players:
            if player.id == player_id:
                return player
        return None
    
    def get_alive_players(self) -> List[Player]:
        """Get all alive players on the team."""
        return [p for p in self.players if p.id in self._alive_players]
    
    def get_dead_players(self) -> List[Player]:
        """Get all dead players on the team."""
        return [p for p in self.players if not p.alive]
    
    def get_players_by_role(self, role: str) -> List[Player]:
        """Get all players with a specific role."""
        return [p for p in self.players if p.role == role]
    
    def update_economy(self, round_spent: int):
        """Update team economy stats."""
        self.economy['total_spent'] += round_spent
        self.economy['avg_per_round'] = self.economy['total_spent'] / max(1, len(self.players))
    
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
        self._alive_players = {p.id for p in self.players}
        
        # Update blackboard
        if self.blackboard:
            self.blackboard.clear_round_data()
    
    def __repr__(self) -> str:
        return f"Team({self.name}, {len(self.players)} players, {len(self.get_alive_players())} alive)"
    
    def get_igl(self) -> Optional[Player]:
        """Get the in-game leader player object."""
        return next((p for p in self.players if p.id == self.igl_id), None)
    
    def update_alive_players(self) -> None:
        """Update the set of alive players based on player states."""
        self._alive_players = {p.id for p in self.players if p.alive}
        if self.blackboard:
            self.blackboard.set("alive_players", self._alive_players)
    
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
    
    def reset_abilities_and_ultimates(self, max_ult: int = 7):
        """Reset all player ability charges and ult points at round start."""
        for player in self.players:
            player.reset_ability_charges()
            player.ult_points = min(player.ult_points, max_ult)  # Optionally cap ult points

    def increment_player_ult(self, player_id: str, amount: int = 1, max_ult: int = 7):
        """Increment ult points for a player (e.g., orb pickup or round event)."""
        player = self.get_player_by_id(player_id)
        if player:
            player.increment_ult_points(amount, max_ult) 
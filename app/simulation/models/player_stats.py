from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import math


@dataclass
class PlayerMatchStats:
    """Comprehensive statistics for a player across a match."""
    # Basic Stats
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    
    # Damage Stats
    damage_dealt: int = 0
    damage_received: int = 0
    headshots: int = 0
    bodyshots: int = 0
    legshots: int = 0
    
    # Economy Stats
    credits_spent: int = 0
    credits_earned: int = 0
    weapons_purchased: Dict[str, int] = field(default_factory=dict)
    
    # Round Impact
    first_bloods: int = 0
    first_deaths: int = 0
    clutches: int = 0
    clutches_attempted: int = 0
    plants: int = 0
    defuses: int = 0
    
    # Utility Usage
    utilities_used: Dict[str, int] = field(default_factory=dict)
    blind_duration_caused: float = 0.0  # seconds enemy players were blinded by this player
    enemies_flashed: int = 0  # number of times an enemy was flashed 
    teammates_flashed: int = 0  # number of times a teammate was flashed
    damage_by_utility: int = 0
    
    # Multi-kills
    multi_kills: Dict[str, int] = field(default_factory=lambda: {"2k": 0, "3k": 0, "4k": 0, "5k": 0})
    trade_kills: int = 0  # killed an enemy who just killed a teammate
    traded_deaths: int = 0  # died and teammate killed enemy who killed you
    
    # Weapon Stats
    weapon_kills: Dict[str, int] = field(default_factory=dict)
    weapon_headshots: Dict[str, int] = field(default_factory=dict)
    weapon_damage: Dict[str, int] = field(default_factory=dict)
    wallbang_kills: int = 0
    
    # Advanced Stats
    kill_death_assist_ratio: float = 0.0
    average_combat_score: float = 0.0
    damage_per_round: float = 0.0
    kills_per_round: float = 0.0
    first_blood_success_rate: float = 0.0  # % of rounds where player got first blood
    clutch_success_rate: float = 0.0  # % of clutch situations won
    
    # Positional Stats
    kill_positions: List[Tuple[float, float]] = field(default_factory=list)
    death_positions: List[Tuple[float, float]] = field(default_factory=list)
    
    # Round-by-round Stats
    rounds_played: int = 0
    rounds_with_kills: int = 0
    rounds_with_deaths: int = 0
    rounds_with_damage: int = 0
    round_performance: List[Dict] = field(default_factory=list)  # Per-round stats
    
    # Economy Impact
    eco_kills: int = 0  # Kills against eco/save rounds
    anti_eco_kills: int = 0  # Kills during eco/save rounds
    eco_deaths: int = 0  # Deaths during eco/save rounds
    
    # Entry Stats
    entry_attempts: int = 0  # How many times player went in first
    entry_success: int = 0  # How many times player got a kill when entering first
    
    # Defensive Stats
    sites_held: Dict[str, int] = field(default_factory=dict)  # Sites defended successfully
    retakes_participated: int = 0  # Number of retakes participated in
    retakes_won: int = 0  # Number of retakes won
    
    def update_ratios(self):
        """Update calculated ratios and averages."""
        # Calculate KDA
        if self.deaths > 0:
            self.kill_death_assist_ratio = (self.kills + self.assists) / self.deaths
        else:
            self.kill_death_assist_ratio = self.kills + self.assists
        
        # Calculate clutch success rate
        if self.clutches_attempted > 0:
            self.clutch_success_rate = self.clutches / self.clutches_attempted
        
        # Calculate first blood success rate
        if self.rounds_played > 0:
            self.first_blood_success_rate = self.first_bloods / self.rounds_played
            self.kills_per_round = self.kills / self.rounds_played
            self.damage_per_round = self.damage_dealt / self.rounds_played
            
        # Calculate ACS (Average Combat Score)
        # Formula: (Total damage / rounds_played) + (50 * kills per round) + (25 * assists per round) + (33 * first bloods per round)
        if self.rounds_played > 0:
            self.average_combat_score = (
                (self.damage_dealt / self.rounds_played) +
                (50 * self.kills / self.rounds_played) +
                (25 * self.assists / self.rounds_played) +
                (33 * self.first_bloods / self.rounds_played)
            )
    
    def record_kill(self, weapon: str, is_headshot: bool, position: Tuple[float, float],
                   is_first_blood: bool = False, is_wallbang: bool = False, 
                   multi_kill_count: int = 1, is_trade: bool = False, 
                   is_entry: bool = False, is_clutch: bool = False,
                   is_eco_kill: bool = False):
        """Record detailed information about a kill."""
        self.kills += 1
        
        # Weapon stats
        if weapon not in self.weapon_kills:
            self.weapon_kills[weapon] = 0
        self.weapon_kills[weapon] += 1
        
        # Record position
        self.kill_positions.append(position)
        
        # Headshot stats
        if is_headshot:
            self.headshots += 1
            if weapon not in self.weapon_headshots:
                self.weapon_headshots[weapon] = 0
            self.weapon_headshots[weapon] += 1
        
        # Special kill types
        if is_first_blood:
            self.first_bloods += 1
        
        if is_wallbang:
            self.wallbang_kills += 1
        
        if is_trade:
            self.trade_kills += 1
            
        if is_entry:
            self.entry_success += 1
            
        if is_clutch:
            self.clutches += 1
            
        if is_eco_kill:
            self.eco_kills += 1
            
        # Multi-kills tracking
        if multi_kill_count >= 2:
            key = f"{multi_kill_count}k"
            if key in self.multi_kills:
                self.multi_kills[key] += 1
    
    def record_death(self, position: Tuple[float, float], killer_weapon: str = None,
                    is_first_death: bool = False, is_traded: bool = False,
                    is_entry_death: bool = False, during_eco: bool = False):
        """Record information about a death."""
        self.deaths += 1
        self.death_positions.append(position)
        
        if is_first_death:
            self.first_deaths += 1
            
        if is_traded:
            self.traded_deaths += 1
            
        if during_eco:
            self.eco_deaths += 1
    
    def record_damage(self, damage: int, weapon: str, is_headshot: bool = False,
                     is_bodyshot: bool = False, is_legshot: bool = False, 
                     is_utility: bool = False):
        """Record damage dealt to an enemy."""
        self.damage_dealt += damage
        
        if is_utility:
            self.damage_by_utility += damage
        else:
            # Track weapon damage
            if weapon not in self.weapon_damage:
                self.weapon_damage[weapon] = 0
            self.weapon_damage[weapon] += damage
        
        # Track hit locations
        if is_headshot:
            self.headshots += 1
        elif is_bodyshot:
            self.bodyshots += 1
        elif is_legshot:
            self.legshots += 1
    
    def record_utility_usage(self, utility_type: str, enemies_affected: int = 0, 
                           teammates_affected: int = 0, blind_duration: float = 0.0):
        """Record utility usage statistics."""
        if utility_type not in self.utilities_used:
            self.utilities_used[utility_type] = 0
        self.utilities_used[utility_type] += 1
        
        if utility_type == "flash":
            self.enemies_flashed += enemies_affected
            self.teammates_flashed += teammates_affected
            self.blind_duration_caused += blind_duration
    
    def record_purchase(self, item_type: str, cost: int):
        """Record purchase of weapons, abilities, or shields."""
        self.credits_spent += cost
        
        if item_type.startswith("weapon_"):
            weapon_name = item_type[7:]  # Remove "weapon_" prefix
            if weapon_name not in self.weapons_purchased:
                self.weapons_purchased[weapon_name] = 0
            self.weapons_purchased[weapon_name] += 1
    
    def record_round_stats(self, round_number: int, kills: int, deaths: int, 
                         damage: int, credits_earned: int, side: str,
                         won_round: bool):
        """Record player performance for a specific round."""
        self.rounds_played += 1
        self.credits_earned += credits_earned
        
        if kills > 0:
            self.rounds_with_kills += 1
        
        if deaths > 0:
            self.rounds_with_deaths += 1
            
        if damage > 0:
            self.rounds_with_damage += 1
        
        # Add detailed round performance
        self.round_performance.append({
            "round": round_number,
            "kills": kills,
            "deaths": deaths,
            "damage": damage,
            "credits_earned": credits_earned,
            "side": side,
            "won": won_round
        })
    
    def attempt_clutch(self, success: bool, enemies_remaining: int):
        """Record a clutch attempt."""
        self.clutches_attempted += 1
        if success:
            self.clutches += 1
    
    def attempt_entry(self, success: bool):
        """Record an entry attempt."""
        self.entry_attempts += 1
        if success:
            self.entry_success += 1
    
    def record_plant(self, site: str):
        """Record a successful spike plant."""
        self.plants += 1
    
    def record_defuse(self):
        """Record a successful spike defuse."""
        self.defuses += 1
    
    def record_site_defense(self, site: str, success: bool):
        """Record defense of a site."""
        if site not in self.sites_held:
            self.sites_held[site] = 0
        if success:
            self.sites_held[site] += 1
    
    def record_retake(self, success: bool):
        """Record participation in a site retake."""
        self.retakes_participated += 1
        if success:
            self.retakes_won += 1
    
    def get_headshot_percentage(self) -> float:
        """Calculate headshot percentage."""
        if self.kills == 0:
            return 0.0
        return (self.headshots / self.kills) * 100.0
    
    def get_entry_success_rate(self) -> float:
        """Calculate entry success rate."""
        if self.entry_attempts == 0:
            return 0.0
        return (self.entry_success / self.entry_attempts) * 100.0
    
    def get_retake_success_rate(self) -> float:
        """Calculate retake success rate."""
        if self.retakes_participated == 0:
            return 0.0
        return (self.retakes_won / self.retakes_participated) * 100.0
    
    def get_summary(self) -> Dict:
        """Return a summary of the player's performance."""
        self.update_ratios()
        
        return {
            "kda": f"{self.kills}/{self.deaths}/{self.assists}",
            "kd_ratio": round(self.kill_death_assist_ratio, 2),
            "acs": round(self.average_combat_score, 1),
            "adr": round(self.damage_per_round, 1),
            "hs_percentage": round(self.get_headshot_percentage(), 1),
            "first_bloods": self.first_bloods,
            "clutches": f"{self.clutches}/{self.clutches_attempted}",
            "entry_success": f"{self.entry_success}/{self.entry_attempts}",
            "utility_damage": self.damage_by_utility,
            "eco_impact": self.eco_kills - self.eco_deaths
        } 
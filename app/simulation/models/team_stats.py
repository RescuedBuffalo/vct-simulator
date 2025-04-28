from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import statistics
from .player_stats import PlayerMatchStats
import math


@dataclass
class EnhancedTeamStats:
    """Enhanced statistics for a team across a match."""
    # Basic Stats
    rounds_won: int = 0
    rounds_lost: int = 0
    attack_rounds_won: int = 0
    defense_rounds_won: int = 0
    
    # Objective Stats
    plants: int = 0
    defuses: int = 0
    
    # Site Stats
    plants_by_site: Dict[str, int] = field(default_factory=dict)
    defenses_by_site: Dict[str, int] = field(default_factory=dict)
    retakes_attempted: Dict[str, int] = field(default_factory=dict)
    retakes_successful: Dict[str, int] = field(default_factory=dict)
    
    # Round Stats
    first_bloods: int = 0
    first_deaths: int = 0
    clutches: int = 0
    clutches_attempted: int = 0
    flawless_rounds: int = 0  # No deaths on team
    thrifty_rounds: int = 0   # Won with significantly lower equipment value
    
    # Combat Stats
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    total_damage_dealt: int = 0
    total_headshots: int = 0
    
    # Economy Stats
    economy: Dict[str, int] = field(default_factory=lambda: {
        "total_spent": 0,
        "avg_per_round": 0,
        "eco_rounds_played": 0,
        "eco_rounds_won": 0,
        "bonus_rounds_played": 0,
        "bonus_rounds_won": 0,
        "full_buy_rounds": 0,
        "full_buy_rounds_won": 0
    })
    weapons_purchased: Dict[str, int] = field(default_factory=dict)
    
    # Utility Stats
    utility_used: Dict[str, int] = field(default_factory=dict)
    utility_damage: int = 0
    enemies_flashed: int = 0
    teammates_flashed: int = 0
    
    # Multi-kills
    multi_kills: Dict[str, int] = field(default_factory=lambda: {"2k": 0, "3k": 0, "4k": 0, "5k": 0})
    
    # Trade Stats
    trades_for: int = 0
    trades_against: int = 0
    trade_efficiency: float = 0.0  # trades_for / trades_against
    
    # Round-by-round Performance
    round_performance: List[Dict] = field(default_factory=list)
    equipment_value_by_round: List[int] = field(default_factory=list)
    
    # Time Stats
    avg_round_duration_attack: float = 0.0
    avg_round_duration_defense: float = 0.0
    avg_plant_time: float = 0.0  # Average time spent before planting
    
    # Comeback/Momentum Stats
    consecutive_rounds_won: int = 0
    max_consecutive_rounds_won: int = 0
    comeback_rounds: int = 0  # Rounds won when down by 4+ rounds
    
    # Advanced Stats
    avg_combat_score: float = 0.0
    avg_damage_per_round: float = 0.0
    side_win_rates: Dict[str, float] = field(default_factory=lambda: {"attack": 0.0, "defense": 0.0})
    
    # New stats from the new code block
    pistol_rounds_won: int = 0
    eco_rounds_won: int = 0
    full_buy_rounds_won: int = 0
    total_credits_spent: int = 0
    total_credits_earned: int = 0
    avg_credits_per_round: float = 0.0
    save_rounds: int = 0
    plant_retakes: int = 0
    plant_defends: int = 0
    avg_round_time: float = 0.0
    avg_defuse_time: float = 0.0
    total_round_time: float = 0.0
    total_rounds_timed: int = 0
    total_first_bloods: int = 0
    total_entry_kills: int = 0
    total_entry_deaths: int = 0
    
    def __post_init__(self):
        self.team_name = ""  # This should be set later
    
    def update_from_player_stats(self, player_stats: Dict[str, PlayerMatchStats], total_rounds: int):
        """Update team stats based on player stats."""
        # Combat stats
        self.total_kills = sum(stats.kills for stats in player_stats.values())
        self.total_deaths = sum(stats.deaths for stats in player_stats.values())
        self.total_assists = sum(stats.assists for stats in player_stats.values())
        self.total_damage_dealt = sum(stats.damage_dealt for stats in player_stats.values())
        self.total_headshots = sum(stats.headshots for stats in player_stats.values())
        
        # First blood stats
        self.first_bloods = sum(stats.first_bloods for stats in player_stats.values())
        self.first_deaths = sum(stats.first_deaths for stats in player_stats.values())
        
        # Clutch stats
        self.clutches = sum(stats.clutches for stats in player_stats.values())
        self.clutches_attempted = sum(stats.clutches_attempted for stats in player_stats.values())
        
        # Economy stats
        self.economy["total_spent"] = sum(stats.credits_spent for stats in player_stats.values())
        if total_rounds > 0:
            self.economy["avg_per_round"] = self.economy["total_spent"] / total_rounds
        
        # Utility stats
        for stats in player_stats.values():
            self.utility_damage += stats.damage_by_utility
            self.enemies_flashed += stats.enemies_flashed
            self.teammates_flashed += stats.teammates_flashed
            
            # Aggregate utilities used
            for util_type, count in stats.utilities_used.items():
                if util_type not in self.utility_used:
                    self.utility_used[util_type] = 0
                self.utility_used[util_type] += count
                
            # Aggregate weapons purchased
            for weapon, count in stats.weapons_purchased.items():
                if weapon not in self.weapons_purchased:
                    self.weapons_purchased[weapon] = 0
                self.weapons_purchased[weapon] += count
                
            # Aggregate multi-kills
            for multi_type, count in stats.multi_kills.items():
                if multi_type in self.multi_kills:
                    self.multi_kills[multi_type] += count
        
        # Advanced stats
        if player_stats:
            self.avg_combat_score = statistics.mean(
                stats.average_combat_score for stats in player_stats.values()
            )
            self.avg_damage_per_round = self.total_damage_dealt / total_rounds if total_rounds > 0 else 0
            
        # Side win rates
        attack_rounds = self.attack_rounds_won + sum(1 for perf in self.round_performance 
                                               if perf.get("side") == "attack" and not perf.get("won"))
        defense_rounds = self.defense_rounds_won + sum(1 for perf in self.round_performance 
                                                 if perf.get("side") == "defense" and not perf.get("won"))
        
        if attack_rounds > 0:
            self.side_win_rates["attack"] = self.attack_rounds_won / attack_rounds
        if defense_rounds > 0:
            self.side_win_rates["defense"] = self.defense_rounds_won / defense_rounds
        
        # New stats from the new code block
        self.pistol_rounds_won += sum(1 for perf in self.round_performance if perf.get("is_pistol", False))
        self.eco_rounds_won += sum(1 for perf in self.round_performance if perf.get("is_eco", False))
        self.full_buy_rounds_won += sum(1 for perf in self.round_performance if perf.get("is_full_buy", False))
        self.total_credits_spent += sum(stats.credits_spent for stats in player_stats.values())
        self.total_credits_earned += sum(stats.credits_earned for stats in player_stats.values())
        if total_rounds > 0:
            self.avg_credits_per_round = self.total_credits_earned / total_rounds
        self.save_rounds += sum(1 for perf in self.round_performance if perf.get("won", False) and perf.get("is_full_buy", False))
        self.plant_retakes += sum(1 for perf in self.round_performance if perf.get("won", False) and perf.get("is_full_buy", False))
        self.plant_defends += sum(1 for perf in self.round_performance if perf.get("won", False) and perf.get("is_full_buy", False))
        self.total_first_bloods += sum(1 for perf in self.round_performance if perf.get("first_bloods", 0) > 0)
        self.total_entry_kills += sum(1 for perf in self.round_performance if perf.get("entry_kills", 0) > 0)
        self.total_entry_deaths += sum(1 for perf in self.round_performance if perf.get("entry_deaths", 0) > 0)
    
    def record_round_result(self, round_number: int, won: bool, side: str, 
                           equipment_value: int, enemies_alive: int = 0, 
                           time_remaining: float = 0.0, score_difference: int = 0,
                           end_condition: str = None, site: str = None):
        """Record the result of a round."""
        if won:
            self.rounds_won += 1
            
            # Track consecutive wins
            self.consecutive_rounds_won += 1
            self.max_consecutive_rounds_won = max(self.max_consecutive_rounds_won, self.consecutive_rounds_won)
            
            # Track side wins
            if side == "attack":
                self.attack_rounds_won += 1
            else:
                self.defense_rounds_won += 1
                
            # Track flawless rounds
            if enemies_alive == 0:
                self.flawless_rounds += 1
                
            # Track thrifty rounds
            if equipment_value < 7000:  # Threshold for thrifty
                self.thrifty_rounds += 1
                
            # Track comeback rounds
            if score_difference <= -4:
                self.comeback_rounds += 1
                
            # Track site stats
            if end_condition == "spike_detonation" and site:
                if site not in self.plants_by_site:
                    self.plants_by_site[site] = 0
                self.plants_by_site[site] += 1
                
            elif end_condition == "spike_defused" and site:
                if site not in self.defenses_by_site:
                    self.defenses_by_site[site] = 0
                self.defenses_by_site[site] += 1
                
                if site not in self.retakes_successful:
                    self.retakes_successful[site] = 0
                self.retakes_successful[site] += 1
        else:
            self.rounds_lost += 1
            self.consecutive_rounds_won = 0
            
            # Track unsuccessful retakes
            if end_condition == "spike_detonation" and side == "defense" and site:
                if site not in self.retakes_attempted:
                    self.retakes_attempted[site] = 0
                self.retakes_attempted[site] += 1
        
        # Record round performance
        self.round_performance.append({
            "round": round_number,
            "won": won,
            "side": side,
            "equipment_value": equipment_value,
            "enemies_alive": enemies_alive,
            "time_remaining": time_remaining,
            "end_condition": end_condition,
            "site": site
        })
        
        self.equipment_value_by_round.append(equipment_value)
        
        # Update timing stats
        if won:
            if side == "attack":
                self._update_attack_timing_stats(time_remaining)
            else:
                self._update_defense_timing_stats(time_remaining)
                
    def record_plant(self, site: str, time_elapsed: float):
        """Record a successful spike plant."""
        self.plants += 1
        
        if site not in self.plants_by_site:
            self.plants_by_site[site] = 0
        self.plants_by_site[site] += 1
        
        # Update avg plant time
        current_total = self.avg_plant_time * (self.plants - 1)
        self.avg_plant_time = (current_total + time_elapsed) / self.plants
    
    def record_defuse(self, site: str, was_retake: bool = False):
        """Record a successful spike defuse."""
        self.defuses += 1
        
        if site not in self.defenses_by_site:
            self.defenses_by_site[site] = 0
        self.defenses_by_site[site] += 1
        
        if was_retake:
            if site not in self.retakes_successful:
                self.retakes_successful[site] = 0
            self.retakes_successful[site] += 1
            
            if site not in self.retakes_attempted:
                self.retakes_attempted[site] = 0
            self.retakes_attempted[site] += 1
    
    def record_trade(self, is_for: bool):
        """Record a trade kill."""
        if is_for:
            self.trades_for += 1
        else:
            self.trades_against += 1
            
        if self.trades_against > 0:
            self.trade_efficiency = self.trades_for / self.trades_against
    
    def record_economy_round(self, round_type: str, won: bool):
        """Record an economy round (eco, bonus, full-buy)."""
        if round_type == "eco":
            self.economy["eco_rounds_played"] += 1
            if won:
                self.economy["eco_rounds_won"] += 1
        elif round_type == "bonus":
            self.economy["bonus_rounds_played"] += 1
            if won:
                self.economy["bonus_rounds_won"] += 1
        elif round_type == "full_buy":
            self.economy["full_buy_rounds"] += 1
            if won:
                self.economy["full_buy_rounds_won"] += 1
    
    def get_win_rate(self) -> float:
        """Calculate overall win rate."""
        total_rounds = self.rounds_won + self.rounds_lost
        if total_rounds == 0:
            return 0.0
        return (self.rounds_won / total_rounds) * 100.0
    
    def get_first_blood_success_rate(self) -> float:
        """Calculate first blood success rate."""
        total_rounds = self.rounds_won + self.rounds_lost
        if total_rounds == 0:
            return 0.0
        return (self.first_bloods / total_rounds) * 100.0
    
    def get_clutch_success_rate(self) -> float:
        """Calculate clutch success rate."""
        if self.clutches_attempted == 0:
            return 0.0
        return (self.clutches / self.clutches_attempted) * 100.0
    
    def get_retake_success_rate(self) -> float:
        """Calculate overall retake success rate."""
        total_retakes_attempted = sum(self.retakes_attempted.values())
        total_retakes_successful = sum(self.retakes_successful.values())
        
        if total_retakes_attempted == 0:
            return 0.0
        return (total_retakes_successful / total_retakes_attempted) * 100.0
    
    def get_headshot_percentage(self) -> float:
        """Calculate team headshot percentage."""
        if self.total_kills == 0:
            return 0.0
        return (self.total_headshots / self.total_kills) * 100.0
    
    def get_site_preferences(self) -> Dict[str, float]:
        """Get team site preferences."""
        result = {}
        total_plants = sum(self.plants_by_site.values())
        
        if total_plants > 0:
            for site, count in self.plants_by_site.items():
                result[site] = (count / total_plants) * 100.0
                
        return result
    
    def get_eco_round_performance(self) -> Dict[str, float]:
        """Calculate eco round performance."""
        result = {}
        
        if self.economy["eco_rounds_played"] > 0:
            result["eco_win_rate"] = (self.economy["eco_rounds_won"] / self.economy["eco_rounds_played"]) * 100.0
        else:
            result["eco_win_rate"] = 0.0
            
        if self.economy["bonus_rounds_played"] > 0:
            result["bonus_win_rate"] = (self.economy["bonus_rounds_won"] / self.economy["bonus_rounds_played"]) * 100.0
        else:
            result["bonus_win_rate"] = 0.0
            
        if self.economy["full_buy_rounds"] > 0:
            result["full_buy_win_rate"] = (self.economy["full_buy_rounds_won"] / self.economy["full_buy_rounds"]) * 100.0
        else:
            result["full_buy_win_rate"] = 0.0
            
        return result

    def get_summary(self) -> Dict:
        """Return a summary of the team's performance."""
        eco_performance = self.get_eco_round_performance()
        
        return {
            "score": f"{self.rounds_won}-{self.rounds_lost}",
            "win_rate": round(self.get_win_rate(), 1),
            "side_win_rates": {
                "attack": round(self.side_win_rates["attack"] * 100, 1),
                "defense": round(self.side_win_rates["defense"] * 100, 1)
            },
            "first_bloods": self.first_bloods,
            "clutches": f"{self.clutches}/{self.clutches_attempted}",
            "eco_performance": {
                "eco": round(eco_performance.get("eco_win_rate", 0), 1),
                "bonus": round(eco_performance.get("bonus_win_rate", 0), 1),
                "full_buy": round(eco_performance.get("full_buy_win_rate", 0), 1)
            },
            "avg_damage_per_round": round(self.avg_damage_per_round, 1),
            "headshot_percentage": round(self.get_headshot_percentage(), 1),
            "retake_success_rate": round(self.get_retake_success_rate(), 1),
            "flawless_rounds": self.flawless_rounds,
            "thrifty_rounds": self.thrifty_rounds,
            "multi_kills": self.multi_kills,
            "trade_efficiency": round(self.trade_efficiency, 2),
            "site_preferences": {site: round(pct, 1) for site, pct in self.get_site_preferences().items()},
            "pistol_rounds_won": self.pistol_rounds_won,
            "eco_rounds_won": self.eco_rounds_won,
            "full_buy_rounds_won": self.full_buy_rounds_won,
            "total_credits_spent": self.total_credits_spent,
            "total_credits_earned": self.total_credits_earned,
            "avg_credits_per_round": round(self.avg_credits_per_round, 1),
            "save_rounds": self.save_rounds,
            "plant_retakes": self.plant_retakes,
            "plant_defends": self.plant_defends,
            "avg_round_time": round(self.avg_round_time, 1) if hasattr(self, 'avg_round_time') else 0,
            "avg_defuse_time": round(self.avg_defuse_time, 1) if hasattr(self, 'avg_defuse_time') else 0,
            "total_round_time": round(self.total_round_time, 1) if hasattr(self, 'total_round_time') else 0,
            "total_rounds_timed": self.total_rounds_timed,
            "total_first_bloods": self.total_first_bloods,
            "total_entry_kills": self.total_entry_kills,
            "total_entry_deaths": self.total_entry_deaths
        }
    
    def _update_attack_timing_stats(self, time_remaining: float):
        """Update attack timing statistics."""
        if self.attack_rounds_won == 0:
            self.avg_round_duration_attack = 100 - time_remaining  # Assuming 100s rounds
        else:
            current_total = self.avg_round_duration_attack * (self.attack_rounds_won - 1)
            self.avg_round_duration_attack = (current_total + (100 - time_remaining)) / self.attack_rounds_won
    
    def _update_defense_timing_stats(self, time_remaining: float):
        """Update defense timing statistics."""
        if self.defense_rounds_won == 0:
            self.avg_round_duration_defense = 100 - time_remaining  # Assuming 100s rounds
        else:
            current_total = self.avg_round_duration_defense * (self.defense_rounds_won - 1)
            self.avg_round_duration_defense = (current_total + (100 - time_remaining)) / self.defense_rounds_won 
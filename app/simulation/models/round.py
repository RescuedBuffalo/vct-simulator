from typing import Dict, List, Optional, Tuple, Any, Union, Set
import random
import math
from dataclasses import dataclass, field
from enum import Enum

from .player import Player
from .map import MapLayout, MapArea
from .blackboard import Blackboard
from .ability import AbilityInstance, AbilityType, AbilityTarget

# Constants
ROUND_TIMER = 100  # seconds
SPIKE_TIMER = 45  # seconds after plant
BUY_PHASE_TIMER = 30  # seconds
FIRST_ROUND_BUY_PHASE_TIMER = 45  # seconds
POST_ROUND_TIMER = 5  # seconds

# Combat constants
PLANT_TIME = 4.0  # seconds to plant the spike
DEFUSE_TIME = 7.0  # seconds to defuse the spike
HALF_DEFUSE_TIME = 3.5  # seconds for half defuse

# Sound visibility ranges (in game distance units)
FOOTSTEP_RANGE = 20.0
GUNSHOT_RANGE = 50.0
ABILITY_SOUND_RANGE = 35.0

class RoundPhase(Enum):
    BUY = "buy"
    ROUND = "round"
    END = "end"

class RoundWinner(Enum):
    ATTACKERS = "attackers"
    DEFENDERS = "defenders"
    NONE = "none"  # Round still in progress

class RoundEndCondition(Enum):
    ELIMINATION = "elimination"
    SPIKE_DETONATION = "spike_detonation"
    SPIKE_DEFUSED = "spike_defused"
    TIME_EXPIRED = "time_expired"

@dataclass
class DeathEvent:
    """Track player death events."""
    victim_id: str
    killer_id: Optional[str]
    assist_ids: List[str]
    weapon: str
    time: float
    position: Tuple[float, float]
    is_wallbang: bool = False
    is_headshot: bool = False
    ability_used: Optional[str] = None  # Name of ability if killed by ability


@dataclass
class DroppedWeapon:
    """Track weapons dropped on the map."""
    weapon_type: str
    ammo: int
    position: Tuple[float, float]
    dropped_time: float


@dataclass
class DroppedShield:
    """Track shields dropped on the map."""
    shield_type: str  # "light" or "heavy"
    position: Tuple[float, float]
    dropped_time: float


@dataclass
class InfoEvent:
    """Information gathered by players."""
    type: str  # "spot", "sound", "damage", "ability"
    source_id: str
    target_id: Optional[str]
    position: Tuple[float, float]
    time: float
    info: Dict


@dataclass
class CommEvent:
    """Communication between teammates."""
    sender_id: str
    message: str
    time: float
    target_id: Optional[str] = None  # If None, broadcast to all teammates

@dataclass
class RoundResult:
    def __init__(self, round_number: int, round_summary: Dict):
        self.round_number = round_number
        self.phase = round_summary["phase"]
        self.time_remaining = round_summary["time_remaining"]
        self.spike_planted = round_summary["spike_planted"]
        self.spike_time_remaining = round_summary["spike_time_remaining"]
        self.alive_attackers = round_summary["alive_attackers"]
        self.alive_defenders = round_summary["alive_defenders"]
        self.winner = round_summary["winner"]
        self.end_condition = round_summary["end_condition"]
        self.kill_count = round_summary["kill_count"]

    def get_round_summary(self) -> Dict:
        return {
            "round_number": self.round_number,
            "phase": self.phase,
            "time_remaining": self.time_remaining,
            "spike_planted": self.spike_planted,
            "spike_time_remaining": self.spike_time_remaining,
            "alive_attackers": self.alive_attackers,
            "alive_defenders": self.alive_defenders,
            "winner": self.winner,
            "end_condition": self.end_condition,
            "kill_count": self.kill_count
        }


class Round:
    """
    Simulates a single round of a match.
    """
    def __init__(
        self,
        round_number: int,
        players: Dict[str, Player],
        attacker_ids: List[str],
        defender_ids: List[str],
        map_data: Dict,
        attacker_blackboard: Blackboard = None,
        defender_blackboard: Blackboard = None,
        seed: Optional[int] = None,
        loss_bonus_attackers: int = 1900,
        loss_bonus_defenders: int = 1900,
    ):
        self.round_number = round_number
        self.players = players
        self.attacker_ids = attacker_ids
        self.defender_ids = defender_ids
        self.map_data = map_data
        
        # Initialize or use provided blackboards for each team
        self.attacker_blackboard = attacker_blackboard if attacker_blackboard else Blackboard("attackers")
        self.defender_blackboard = defender_blackboard if defender_blackboard else Blackboard("defenders")
        
        # Set attacking/defending status in blackboards
        self.attacker_blackboard.set("is_attacking", True)
        self.defender_blackboard.set("is_attacking", False)
        
        # Update current round in blackboards
        self.attacker_blackboard.set("current_round", round_number)
        self.defender_blackboard.set("current_round", round_number)
        
        # Set random seed for deterministic simulation if provided
        if seed is not None:
            random.seed(seed)
            
        # Round state
        self.phase = RoundPhase.BUY
        self.tick = 0.0  # simulation time in seconds
        self.round_winner = RoundWinner.NONE
        self.round_end_condition = None
        self.spike_planted = False
        self.spike_carrier_id = None
        self.spike_plant_time = None
        self.spike_position = None
        
        # Timers
        self.round_time_remaining = ROUND_TIMER
        self.buy_phase_time = FIRST_ROUND_BUY_PHASE_TIMER if round_number == 1 else BUY_PHASE_TIMER
        self.spike_time_remaining = None
        
        # Events
        self.deaths: List[DeathEvent] = []
        self.dropped_weapons: List[DroppedWeapon] = []
        self.dropped_shields: List[DroppedShield] = []
        self.active_abilities: List[AbilityInstance] = []
        self.info_events: List[InfoEvent] = []
        self.comms: List[CommEvent] = []
        
        # Initialize blackboards with alive players
        self._update_alive_players_in_blackboards()
        
        # Spike assignment
        self._assign_spike()
        
        # Initialize player positions
        self._initialize_player_positions()
        
        # Initialize round strategies for both teams
        self._set_initial_strategies()
        
        self.loss_bonus_attackers = loss_bonus_attackers
        self.loss_bonus_defenders = loss_bonus_defenders
        
        # Enhanced event tracking for statistics
        self._death_events: List[DeathEvent] = []
        self._plant_events: List[Dict] = []
        self._defuse_events: List[Dict] = []
        self._damage_events: List[Dict] = []
        self._utility_events: List[Dict] = []
        self._purchase_events: List[Dict] = []
        self.kill_count = 0
        self.print_kills = False
    
    def _update_alive_players_in_blackboards(self) -> None:
        """Update the blackboards with currently alive players."""
        attacker_alive = set(pid for pid in self.attacker_ids if self.players[pid].alive)
        defender_alive = set(pid for pid in self.defender_ids if self.players[pid].alive)
        
        self.attacker_blackboard.set("alive_players", attacker_alive)
        self.defender_blackboard.set("alive_players", defender_alive)
    
    def _set_initial_strategies(self) -> None:
        """Set initial strategies for both teams based on blackboard data and round state."""
        # Get strategy suggestions from blackboards
        att_strategy, att_site, _ = self.attacker_blackboard.suggest_strategy()
        def_strategy, def_site, _ = self.defender_blackboard.suggest_strategy()
        
        # Set strategies in blackboards
        # Use the IGL or a random player from each team to be the caller
        att_igl = random.choice(self.attacker_ids)
        def_igl = random.choice(self.defender_ids)
        
        self.attacker_blackboard.set_strategy(att_strategy, att_igl, att_site)
        self.defender_blackboard.set_strategy(def_strategy, def_igl, def_site)
    
    def _assign_spike(self) -> None:
        """Assign the spike to a random attacker."""
        if not self.attacker_ids:
            return
            
        spike_carrier_id = random.choice(self.attacker_ids)
        self.spike_carrier_id = spike_carrier_id
        self.players[spike_carrier_id].spike = True
    
    def _initialize_player_positions(self) -> None:
        """Set initial positions for all players based on map data."""
        # Position attackers at attacker spawn points
        attacker_spawns = self.map_data.get("attacker_spawns", [])
        for i, player_id in enumerate(self.attacker_ids):
            spawn_idx = i % len(attacker_spawns) if attacker_spawns else 0
            spawn_position = attacker_spawns[spawn_idx] if attacker_spawns else (0.0, 0.0)
            
            # Add some randomness to avoid players on exact same spot
            jitter_x = random.uniform(-1.0, 1.0)
            jitter_y = random.uniform(-1.0, 1.0)
            
            self.players[player_id].location = (
                spawn_position[0] + jitter_x,
                spawn_position[1] + jitter_y
            )
            self.players[player_id].direction = 0.0  # Face forward
            
        # Position defenders at defender spawn points
        defender_spawns = self.map_data.get("defender_spawns", [])
        for i, player_id in enumerate(self.defender_ids):
            spawn_idx = i % len(defender_spawns) if defender_spawns else 0
            spawn_position = defender_spawns[spawn_idx] if defender_spawns else (0.0, 0.0)
            
            # Add some randomness to avoid players on exact same spot
            jitter_x = random.uniform(-1.0, 1.0)
            jitter_y = random.uniform(-1.0, 1.0)
            
            self.players[player_id].location = (
                spawn_position[0] + jitter_x,
                spawn_position[1] + jitter_y
            )
            self.players[player_id].direction = 180.0  # Face opposite direction
    
    def simulate(self, time_step: float = 0.5) -> Dict:
        """
        Run the round simulation until it ends.
        Returns the round results including winner and player stats.
        """
        while self.round_winner == RoundWinner.NONE:
            self.update(time_step)
            
        # Collect round stats
        round_results = {
            "round_number": self.round_number,
            "winner": self.round_winner.value,
            "end_condition": self.round_end_condition.value if self.round_end_condition else None,
            "duration": self.tick,
            "spike_planted": self.spike_planted,
            "player_stats": {},
        }
        
        # Add player stats
        for player_id, player in self.players.items():
            round_results["player_stats"][player_id] = {
                "kills": player.kills,
                "deaths": player.deaths,
                "assists": player.assists,
                "plants": player.plants,
                "defuses": player.defuses,
            }
        
        # Record round result in blackboards
        attacker_won = self.round_winner == RoundWinner.ATTACKERS
        defender_won = self.round_winner == RoundWinner.DEFENDERS
        end_condition = self.round_end_condition.value if self.round_end_condition else "unknown"
        
        # Determine site if spike was planted
        site = None
        if self.spike_position:
            # Determine which site the spike was at
            for site_name, site_info in self.map_data.get("plant_sites", {}).items():
                if self._calculate_distance(self.spike_position, site_info.get("center", (0, 0))) <= site_info.get("radius", 10.0):
                    site = site_name
                    break
        
        # Record in both blackboards
        self.attacker_blackboard.record_round_result(
            self.round_number, 
            attacker_won, 
            end_condition, 
            site
        )
        
        self.defender_blackboard.record_round_result(
            self.round_number, 
            defender_won, 
            end_condition, 
            site
        )
            
        return round_results

    def update(self, time_step: float) -> None:
        """Update the round state by one time step."""
        self.tick += time_step
        
        # Update phase
        if self.phase == RoundPhase.BUY:
            self._process_buy_phase(time_step)
        elif self.phase == RoundPhase.ROUND:
            self._process_round_phase(time_step)
        elif self.phase == RoundPhase.END:
            # Nothing to do in end phase
            pass
            
        # Update utility effects
        self._update_utility(time_step)
        
        # Update player states
        for player_id in self.players:
            self._update_player(player_id, time_step)
            
        # Check for round end conditions
        self._check_round_end_conditions()
        
        # Decay knowledge in blackboards
        self.attacker_blackboard.decay_knowledge(time_step)
        self.defender_blackboard.decay_knowledge(time_step)
        
        # Update alive players in blackboards
        self._update_alive_players_in_blackboards()
    
    def _process_buy_phase(self, time_step: float) -> None:
        """Handle buy phase logic."""
        self.buy_phase_time -= time_step
        
        # Simulate players buying
        if self.buy_phase_time <= 0:
            # Buy phase is over, transition to round phase
            self.phase = RoundPhase.ROUND
            self.round_time_remaining = ROUND_TIMER
            
            # Simulate buying decisions for all players
            for player_id, player in self.players.items():
                self._simulate_buy_decision(player)
    
    def _simulate_buy_decision(self, player: Player) -> None:
        """Simulate a player's buy decision based on credits available and team economy."""
        # Get team blackboard for this player
        team_blackboard = self.attacker_blackboard if player.id in self.attacker_ids else self.defender_blackboard
        
        # Update economy info in blackboard
        economy = team_blackboard.get("economy")
        economy.team_credits += player.creds
        
        # Basic buy logic - can be expanded based on economy and team strategy
        if player.creds >= 3900:  # Full buy threshold
            # Buy rifle, heavy shield, and abilities
            player.weapon = "Vandal" if random.random() < 0.5 else "Phantom"
            player.shield = "heavy"
            player.creds -= 3900
            economy.can_full_buy = True
        elif player.creds >= 2400:  # Light buy threshold
            # Buy SMG or shotgun and light shield
            player.weapon = "Spectre" if random.random() < 0.7 else "Bulldog"
            player.shield = "light"
            player.creds -= 2400
            economy.can_half_buy = True
        elif player.creds >= 950:  # Eco round
            # Buy pistol and maybe light shield
            player.weapon = "Sheriff" if random.random() < 0.6 else "Ghost"
            if player.creds >= 1400:
                player.shield = "light"
                player.creds -= 450
            player.creds -= 950
        else:
            # Very low economy - consider saving
            economy.saving = True
        
        # Update average credits after purchases
        alive_player_count = len(team_blackboard.get("alive_players"))
        if alive_player_count > 0:
            all_creds = [self.players[pid].creds for pid in team_blackboard.get("alive_players")]
            economy.avg_credits = sum(all_creds) / alive_player_count
        
        # Track purchase events for statistics
        if player.weapon:
            item_cost = {
                "light_shield": 400,
                "heavy_shield": 1000,
                "Spectre": 1600,
                "Bulldog": 2050,
                "Phantom": 2900,
                "Vandal": 2900,
                "Operator": 4700,
                "Sheriff": 800,
                "Marshal": 950,
                "Odin": 3200
            }.get(player.weapon, 500)  # Default cost for unknown items
            
            item_type = "shield" if player.shield == "heavy" or player.shield == "light" else f"weapon_{player.weapon}"
            self._log_purchase_event(player.id, item_type, item_cost)
    
    def _process_round_phase(self, time_step: float) -> None:
        """Handle round phase logic."""
        # Update timers
        self.round_time_remaining -= time_step
        if self.spike_time_remaining is not None:
            self.spike_time_remaining -= time_step
            
        # Process spike planting/defusing
        self._process_spike_actions(time_step)
        
        # Update information and communications
        self._update_vision_and_sound()
        self._process_team_communications()
        
        # Update mid-round strategies if needed based on info
        self._update_strategies_mid_round()
        
        # Simulate combat and movement
        self._simulate_combat_interactions()
        self._simulate_player_movements(time_step)
        
        # Update utility usage
        self._simulate_utility_usage()
    
    def _update_strategies_mid_round(self) -> None:
        """Update team strategies mid-round based on new information."""
        # For attackers - consider changing strategy based on defender positions
        att_strat = self.attacker_blackboard.get("current_strategy")
        if att_strat:
            # Check if we've seen multiple defenders at a site other than our target
            enemy_info = self.attacker_blackboard.get("enemy_info")
            if enemy_info and att_strat.target_site:
                # Count enemies spotted at each site
                site_enemies = {}
                for _, info in enemy_info.items():
                    if info.position:
                        # Determine which site this position is near
                        nearest_site = self._position_to_site(info.position)
                        if nearest_site:
                            site_enemies[nearest_site] = site_enemies.get(nearest_site, 0) + 1
                
                # If another site has fewer defenders, consider rotating
                current_target = att_strat.target_site
                for site, count in site_enemies.items():
                    if site != current_target and count <= 1 and site_enemies.get(current_target, 0) >= 3:
                        # This site looks weaker - consider rotating
                        att_igl = att_strat.issued_by
                        self.attacker_blackboard.set_strategy(
                            "rotate", 
                            att_igl,
                            site, 
                            {"reason": f"Detected {site_enemies.get(current_target, 0)} defenders at {current_target}"}
                        )
                        
                        # Add a team warning
                        self.attacker_blackboard.add_warning(f"Rotating to site {site} - weak defense detected")
                        break
        
        # For defenders - consider rotating based on attacker movements
        def_strat = self.defender_blackboard.get("current_strategy")
        if def_strat:
            # Check if we've heard or seen attackers on a specific site
            enemy_info = self.defender_blackboard.get("enemy_info")
            noise_events = self.defender_blackboard.get("noise_events")
            
            # Count attackers spotted/heard at each site
            site_attacker_activity = {}
            
            # From spotted enemies
            for _, info in enemy_info.items():
                if info.position:
                    nearest_site = self._position_to_site(info.position)
                    if nearest_site:
                        site_attacker_activity[nearest_site] = site_attacker_activity.get(nearest_site, 0) + 2  # Visual confirmation is stronger
            
            # From noise
            for event in noise_events:
                if event.get("location"):
                    nearest_site = self._position_to_site(event["location"])
                    if nearest_site:
                        site_attacker_activity[nearest_site] = site_attacker_activity.get(nearest_site, 0) + 1
            
            # Check if there's significant activity at one site
            if site_attacker_activity:
                most_active_site = max(site_attacker_activity.keys(), key=lambda k: site_attacker_activity[k])
                if site_attacker_activity[most_active_site] >= 3:  # Threshold for rotation decision
                    # Significant activity detected - rotate to that site
                    def_igl = def_strat.issued_by
                    self.defender_blackboard.set_strategy(
                        "rotate", 
                        def_igl,
                        most_active_site, 
                        {"reason": f"Multiple enemies detected at {most_active_site}"}
                    )
                    
                    # Add a team warning
                    self.defender_blackboard.add_warning(f"Rotate to {most_active_site} - enemy activity detected")
    
    def _position_to_site(self, position: Tuple[float, float]) -> Optional[str]:
        """Determine which site (if any) a position is nearest to."""
        for site_name, site_info in self.map_data.get("plant_sites", {}).items():
            center = site_info.get("center", (0, 0))
            radius = site_info.get("radius", 10.0)
            
            if self._calculate_distance(position, center) <= radius * 1.5:  # Use 1.5x radius to include approaches
                return site_name
                
        return None
    
    def _process_spike_actions(self, time_step: float) -> None:
        """Handle spike-related actions such as planting and defusing."""
        # Handle spike planting
        for player_id in self.attacker_ids:
            player = self.players[player_id]
            if not player.alive or not player.spike:
                continue
                
            # Check if at a valid plant site
            at_plant_site = self._is_at_plant_site(player.location)
            
            if player.is_planting and at_plant_site:
                player.plant_progress += time_step
                
                # Complete planting
                if player.plant_progress >= PLANT_TIME:
                    self.spike_planted = True
                    self.spike_plant_time = self.tick
                    self.spike_position = player.location
                    player.spike = False
                    player.is_planting = False
                    player.plants += 1
                    self.spike_time_remaining = SPIKE_TIMER
                    
                    # Log planting event
                    self._log_spike_planted(player_id)
                    
                    # Update spike info in blackboards
                    plant_site = self._position_to_site(player.location)
                    spike_info = {
                        "location": player.location,
                        "status": "planted",
                        "plant_time": self.tick,
                        "plant_site": plant_site
                    }
                    self.attacker_blackboard.update_spike_info(**spike_info)
                    self.defender_blackboard.update_spike_info(**spike_info)
                    
                    # Change defenders strategy to "retake" if spike is planted
                    def_igl = random.choice(self.defender_ids)
                    self.defender_blackboard.set_strategy(
                        "retake", 
                        def_igl,
                        plant_site
                    )
                    
                    # Change attackers strategy to "post_plant"
                    att_igl = random.choice(self.attacker_ids)
                    self.attacker_blackboard.set_strategy(
                        "post_plant", 
                        att_igl,
                        plant_site
                    )
            elif not player.is_planting and at_plant_site and not self.spike_planted:
                # Start planting
                player.is_planting = True
                player.plant_progress = 0.0
                
                # Notify team that planting is starting
                self.attacker_blackboard.add_warning(
                    f"Spike being planted by {player.name}", 
                    player.location
                )
            elif player.is_planting and not at_plant_site:
                # Cancel planting if moved away
                player.is_planting = False
                player.plant_progress = 0.0
        
        # Handle spike defusing
        if self.spike_planted:
            for player_id in self.defender_ids:
                player = self.players[player_id]
                if not player.alive:
                    continue
                    
                # Check if at the spike
                at_spike = self._is_near_spike(player.location)
                
                if player.is_defusing and at_spike:
                    player.defuse_progress += time_step
                    
                    # Complete defusing
                    if player.defuse_progress >= DEFUSE_TIME:
                        self.spike_planted = False
                        player.is_defusing = False
                        player.defuses += 1
                        self.round_winner = RoundWinner.DEFENDERS
                        self.round_end_condition = RoundEndCondition.SPIKE_DEFUSED
                        self.phase = RoundPhase.END
                        
                        # Log defusing event
                        self._log_spike_defused(player_id)
                        
                        # Update spike info in blackboards
                        spike_info = {
                            "status": "defused",
                        }
                        self.attacker_blackboard.update_spike_info(**spike_info)
                        self.defender_blackboard.update_spike_info(**spike_info)
                elif not player.is_defusing and at_spike:
                    # Start defusing
                    player.is_defusing = True
                    player.defuse_progress = 0.0
                    
                    # Notify team that defusing is starting
                    self.defender_blackboard.add_warning(
                        f"Spike being defused by {player.name}", 
                        player.location
                    )
                elif player.is_defusing and not at_spike:
                    # Cancel defusing if moved away
                    player.is_defusing = False
                    player.defuse_progress = 0.0
    
    def _is_at_plant_site(self, location: Tuple[float, float]) -> bool:
        """Check if the location is at a valid plant site."""
        plant_sites = self.map_data.get("plant_sites", [])
        for site in plant_sites:
            site_center = site.get("center", (0, 0))
            site_radius = site.get("radius", 10.0)
            
            distance = self._calculate_distance(location, site_center)
            if distance <= site_radius:
                return True
                
        return False
    
    def _is_near_spike(self, location: Tuple[float, float]) -> bool:
        """Check if the location is near the planted spike."""
        if not self.spike_position:
            return False
            
        distance = self._calculate_distance(location, self.spike_position)
        return distance <= 3.0  # Defuse range
    
    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate the distance between two points."""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def _update_vision_and_sound(self) -> None:
        """Update what each player can see and hear."""
        # Reset perception for all players
        for player in self.players.values():
            if player.alive:
                player.visible_enemies = []
                player.heard_sounds = []
        
        # Calculate line of sight and sounds for each player
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            # Calculate what this player can see
            self._calculate_player_vision(player_id)
            
            # Calculate what this player can hear
            self._calculate_player_hearing(player_id)
    
    def _calculate_player_vision(self, player_id: str) -> None:
        """Calculate what a player can see."""
        player = self.players[player_id]
        is_attacker = player_id in self.attacker_ids
        enemy_ids = self.defender_ids if is_attacker else self.attacker_ids
        team_blackboard = self.attacker_blackboard if is_attacker else self.defender_blackboard
        
        for enemy_id in enemy_ids:
            enemy = self.players[enemy_id]
            if not enemy.alive:
                continue
                
            # Check if enemy is in line of sight
            if self._has_line_of_sight(player.location, enemy.location):
                player.visible_enemies.append(enemy_id)
                
                # Log info event
                self._log_info_event(
                    player_id, enemy_id, enemy.location, "spot",
                    {"agent": enemy.agent, "weapon": enemy.weapon}
                )
                
                # Update team blackboard with enemy info
                status = {
                    "agent": enemy.agent,
                    "weapon": enemy.weapon,
                    "shield": enemy.shield
                }
                team_blackboard.update_enemy_info(enemy_id, enemy.location, player_id, status)
                
                # Mark the area as cleared in blackboard
                area_id = team_blackboard._position_to_area_id(enemy.location)
                team_blackboard.mark_area_cleared(area_id)
                
                # Check for spike
                if enemy.spike:
                    spike_info = {
                        "status": "carried",
                        "carrier_id": enemy_id,
                        "location": enemy.location,
                        "seen_by": player_id
                    }
                    team_blackboard.update_spike_info(**spike_info)
    
    def _has_line_of_sight(self, source: Tuple[float, float], target: Tuple[float, float]) -> bool:
        """Check if there is a clear line of sight between two points."""
        # Simplified implementation - check for walls in the map data
        walls = self.map_data.get("walls", [])
        
        for wall in walls:
            if self._line_intersects_wall(source, target, wall):
                return False
                
        return True
    
    def _line_intersects_wall(
        self, source: Tuple[float, float], target: Tuple[float, float], wall: Dict
    ) -> bool:
        """Check if line from source to target intersects with a wall."""
        # Simplified implementation - assume walls are line segments
        wall_start = wall.get("start", (0, 0))
        wall_end = wall.get("end", (0, 0))
        
        # Line-line intersection check
        return self._line_segments_intersect(
            source, target, wall_start, wall_end
        )
    
    def _line_segments_intersect(
        self, p1: Tuple[float, float], p2: Tuple[float, float], 
        p3: Tuple[float, float], p4: Tuple[float, float]
    ) -> bool:
        """Check if line segments (p1, p2) and (p3, p4) intersect."""
        # Calculate direction vectors
        d1x = p2[0] - p1[0]
        d1y = p2[1] - p1[1]
        d2x = p4[0] - p3[0]
        d2y = p4[1] - p3[1]
        
        # Calculate determinant
        det = d1x * d2y - d1y * d2x
        
        # Lines are parallel if determinant is approximately 0
        if abs(det) < 1e-10:
            return False
            
        # Calculate s and t parameters
        s = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / det
        t = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / det
        
        # Check if intersection point is within both line segments
        return 0 <= s <= 1 and 0 <= t <= 1
    
    def _calculate_player_hearing(self, player_id: str) -> None:
        """Calculate what a player can hear."""
        player = self.players[player_id]
        is_attacker = player_id in self.attacker_ids
        team_blackboard = self.attacker_blackboard if is_attacker else self.defender_blackboard
        
        # Check for footsteps from other players
        for other_id, other_player in self.players.items():
            if other_id == player_id or not other_player.alive:
                continue
                
            # Calculate distance
            distance = self._calculate_distance(player.location, other_player.location)
            
            # Check if player is moving (would make footstep sounds)
            is_moving = other_player.velocity[0] != 0 or other_player.velocity[1] != 0
            
            if is_moving and distance <= FOOTSTEP_RANGE:
                # Log sound event
                sound_info = {
                    "type": "footstep",
                    "location": other_player.location,
                    "intensity": 1.0 - (distance / FOOTSTEP_RANGE)
                }
                player.heard_sounds.append(sound_info)
                
                # Log info event
                self._log_info_event(
                    player_id, other_id, other_player.location, "sound",
                    {"type": "footstep", "intensity": sound_info["intensity"]}
                )
                
                # Add to team blackboard noise events
                is_enemy = (other_id in self.attacker_ids) != is_attacker
                if is_enemy:
                    noise_event = {
                        "type": "footstep",
                        "location": other_player.location,
                        "intensity": sound_info["intensity"],
                        "heard_by": player_id,
                        "time": self.tick
                    }
                    current_events = team_blackboard.get("noise_events")
                    current_events.append(noise_event)
                    
                    # Mark area as potentially dangerous
                    area_id = team_blackboard._position_to_area_id(other_player.location)
                    team_blackboard.mark_area_dangerous(area_id)
    
    def _process_team_communications(self) -> None:
        """Simulate team communications based on information gathered."""
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            # Communicate enemy positions to teammates
            if player.visible_enemies:
                for enemy_id in player.visible_enemies:
                    enemy = self.players[enemy_id]
                    
                    # Create communication message
                    message = f"Enemy {enemy.agent} spotted at {enemy.location}"
                    
                    # Log comm event
                    self._log_comm_event(player_id, message)
                    
                    # Update teammates' knowledge
                    self._update_team_knowledge(player_id, enemy_id, enemy.location)
    
    def _update_team_knowledge(
        self, player_id: str, enemy_id: str, enemy_location: Tuple[float, float]
    ) -> None:
        """Update teammates' knowledge about enemy positions."""
        is_attacker = player_id in self.attacker_ids
        teammate_ids = self.attacker_ids if is_attacker else self.defender_ids
        
        for teammate_id in teammate_ids:
            if teammate_id == player_id or not self.players[teammate_id].alive:
                continue
                
            # Update teammate's knowledge
            self.players[teammate_id].known_enemy_positions[enemy_id] = enemy_location
    
    def _simulate_combat_interactions(self) -> None:
        """Simulate combat encounters between players with line of sight."""
        # Check each player for potential combat
        for player_id, player in self.players.items():
            if not player.alive or not player.visible_enemies:
                continue
                
            # Determine which enemies to engage
            for enemy_id in player.visible_enemies:
                enemy = self.players[enemy_id]
                if not enemy.alive:
                    continue
                    
                # Simulate combat outcome
                self._simulate_duel(player_id, enemy_id)
    
    def _simulate_duel(self, player1_id: str, player2_id: str) -> None:
        """Simulate a duel between two players and determine the outcome."""
        player1 = self.players[player1_id]
        player2 = self.players[player2_id]
        
        # Calculate combat advantage based on equipment, position, and stats
        player1_advantage = self._calculate_combat_advantage(player1_id, player2_id)
        player2_advantage = self._calculate_combat_advantage(player2_id, player1_id)
        
        # Determine winner based on advantage and random factor
        random_factor = random.random()
        player1_win_prob = player1_advantage / (player1_advantage + player2_advantage)
        
        if random_factor < player1_win_prob:
            # Player 1 wins
            self._handle_player_death(player2_id, player1_id)
        else:
            # Player 2 wins
            self._handle_player_death(player1_id, player2_id)
    
    def _calculate_combat_advantage(self, player_id: str, opponent_id: str) -> float:
        """Calculate a player's combat advantage against an opponent."""
        player = self.players[player_id]
        opponent = self.players[opponent_id]
        
        # Base advantage from aim rating
        advantage = player.aim_rating
        
        # Weapon advantage
        weapon_tiers = {
            "Operator": 5.0,
            "Vandal": 4.0,
            "Phantom": 4.0,
            "Bulldog": 3.0,
            "Guardian": 3.5,
            "Spectre": 2.5,
            "Stinger": 2.0,
            "Marshal": 3.0,
            "Sheriff": 2.5,
            "Ghost": 2.0,
            "Classic": 1.0,
            "Shorty": 1.5,
            "Frenzy": 1.8,
            None: 0.5, # Melee only
        }
        
        weapon_advantage = weapon_tiers.get(player.weapon, 1.0)
        advantage *= weapon_advantage
        
        # Armor advantage
        armor_multiplier = 1.0
        if player.shield == "heavy":
            armor_multiplier = 1.3
        elif player.shield == "light":
            armor_multiplier = 1.15
            
        advantage *= armor_multiplier
        
        # Status effects
        if "flashed" in player.status_effects:
            advantage *= 0.2  # Severe penalty when flashed
        if "slowed" in player.status_effects:
            advantage *= 0.8  # Minor penalty when slowed
            
        # Movement penalty (if moving while shooting)
        is_moving = player.velocity[0] != 0 or player.velocity[1] != 0
        if is_moving:
            advantage *= (0.5 + 0.5 * player.movement_accuracy)
            
        # First engagement advantage (surprise factor)
        if opponent_id not in player.visible_enemies:
            advantage *= 1.5
            
        return max(0.1, advantage)  # Ensure minimum advantage
    
    def _handle_player_death(self, victim_id: str, killer_id: str) -> None:
        """Handle a player's death."""
        victim = self.players[victim_id]
        killer = self.players[killer_id]
        
        # Update stats
        victim.alive = False
        victim.deaths += 1
        killer.kills += 1
        
        # Drop weapon
        if victim.weapon:
            self._drop_weapon(victim_id, victim.weapon, victim.location)
            
        # Drop shield
        if victim.shield:
            self._drop_shield(victim_id, victim.shield, victim.location)
            
        # Drop spike if carrying
        if victim.spike:
            self.spike_carrier_id = None
            # Create a virtual dropped spike at victim's location
            self.spike_position = victim.location
            victim.spike = False
            
        # Log death event
        is_headshot = random.random() < 0.3  # 30% chance of headshot
        self._log_death_event(victim_id, killer_id, killer.weapon, is_headshot)
        
        # Check team elimination
        self._check_team_elimination()
    
    def _drop_weapon(self, player_id: str, weapon: str, location: Tuple[float, float]) -> None:
        """Create a dropped weapon on the map."""
        # Create dropped weapon
        dropped = DroppedWeapon(
            weapon_type=weapon,
            ammo=random.randint(5, 25),  # Random ammo amount
            position=location,
            dropped_time=self.tick
        )
        
        self.dropped_weapons.append(dropped)
        
        # Remove weapon from player
        self.players[player_id].weapon = None
    
    def _drop_shield(self, player_id: str, shield_type: str, location: Tuple[float, float]) -> None:
        """Create a dropped shield on the map."""
        # Create dropped shield
        dropped = DroppedShield(
            shield_type=shield_type,
            position=location,
            dropped_time=self.tick
        )
        
        self.dropped_shields.append(dropped)
        
        # Remove shield from player
        self.players[player_id].shield = None
        # Reset player armor to 0 when shield is dropped
        self.players[player_id].armor = 0
    
    def _check_team_elimination(self) -> None:
        """Check if one team has been completely eliminated."""
        attackers_alive = sum(1 for pid in self.attacker_ids if self.players[pid].alive)
        defenders_alive = sum(1 for pid in self.defender_ids if self.players[pid].alive)
        
        if attackers_alive == 0:
            # All attackers eliminated
            self.round_winner = RoundWinner.DEFENDERS
            self.round_end_condition = RoundEndCondition.ELIMINATION
            self.phase = RoundPhase.END
        elif defenders_alive == 0:
            # All defenders eliminated
            self.round_winner = RoundWinner.ATTACKERS
            self.round_end_condition = RoundEndCondition.ELIMINATION
            self.phase = RoundPhase.END
    
    def _simulate_player_movements(self, time_step: float) -> None:
        """Simulate all player movements based on current inputs and game state."""
        # For each player, calculate movement direction based on their goals
        # and use the new physics-based movement system
        
        # Create a Map object from map_data for collision detection
        game_map = self._get_map_collision_data()
        
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            # Skip movement if planting or defusing
            if player.is_planting or player.is_defusing:
                player.set_movement_input((0, 0))  # Stop movement
                continue
            
            # Determine desired movement direction based on team, strategy, etc.
            movement_dir = self._get_desired_movement_direction(player_id)
            
            # Set player's movement input
            is_walking = random.random() < 0.3  # Simulate walk intent (shift key)
            is_crouching = random.random() < 0.1  # Simulate crouch intent (ctrl key)
            
            # Decide if AI should jump (occasionally jump when encountering obstacles or stairs)
            is_jumping = False
            
            # Check if player needs to jump to get over obstacles
            current_x, current_y = player.location[:2]
            desired_x = current_x + movement_dir[0]
            desired_y = current_y + movement_dir[1]
            
            # Check for elevation differences that might require jumping
            current_elevation = game_map.get_elevation_at_position(current_x, current_y)
            target_elevation = game_map.get_elevation_at_position(desired_x, desired_y)
            
            # If there's a significant elevation difference, consider jumping
            elevation_difference = target_elevation - current_elevation
            if elevation_difference > 0.3 and elevation_difference < 1.5:
                # Try to jump over small obstacles or up stairs
                is_jumping = random.random() < 0.7  # 70% chance to try jumping
            
            # Also randomly jump sometimes (for pathing variations)
            elif random.random() < 0.02 and player.is_on_ground():  # 2% chance to jump randomly
                is_jumping = True
            
            # Set player's movement input with jump decision
            player.set_movement_input(movement_dir, is_walking, is_crouching, is_jumping)
            
            # Update player movement using physics system
            player.update_movement(time_step, game_map)
            
            # Weapon pickup logic: only allowed during round phase (not buy phase)
            if self.phase == RoundPhase.ROUND:
                self._attempt_pickup_weapon(player)
                self._attempt_pickup_shield(player)
            
            # Check if player has fallen outside map bounds (safety check)
            if player.z_position < -10.0:  # If player has fallen far below the map
                # Reset player to a safe position
                safe_pos = self._find_safe_position_for_player(player_id)
                if safe_pos:
                    player.location = (safe_pos[0], safe_pos[1])
                    player.z_position = safe_pos[2]
                    player.velocity = (0.0, 0.0)
                    player.z_velocity = 0.0
    
    def _attempt_pickup_weapon(self, player):
        """Allow a player to pick up a dropped weapon if close enough and doesn't already have one (or swaps)."""
        pickup_radius = 1.5  # Distance within which a weapon can be picked up
        px, py = player.location[:2]
        weapon_to_remove = None
        for dropped in self.dropped_weapons:
            dx, dy = dropped.position[:2]
            dist = math.sqrt((px - dx) ** 2 + (py - dy) ** 2)
            if dist <= pickup_radius:
                # If player already has a weapon, drop it at their current location
                if player.weapon:
                    self._drop_weapon(player.id, player.weapon, (px, py))
                # Pick up the dropped weapon
                player.weapon = dropped.weapon_type
                weapon_to_remove = dropped
                break
        if weapon_to_remove:
            self.dropped_weapons.remove(weapon_to_remove)
    
    def _attempt_pickup_shield(self, player):
        """Allow a player to pick up a dropped shield if close enough and doesn't already have one (or swaps)."""
        pickup_radius = 1.5  # Distance within which a shield can be picked up
        px, py = player.location[:2]
        shield_to_remove = None
        for dropped in self.dropped_shields:
            dx, dy = dropped.position[:2]
            dist = math.sqrt((px - dx) ** 2 + (py - dy) ** 2)
            if dist <= pickup_radius:
                # If player already has a shield, drop it at their current location
                if player.shield:
                    self._drop_shield(player.id, player.shield, (px, py))
                # Pick up the dropped shield
                player.shield = dropped.shield_type
                # Update player armor based on shield type
                player.armor = 50 if dropped.shield_type == "light" else 100
                shield_to_remove = dropped
                break
        if shield_to_remove:
            self.dropped_shields.remove(shield_to_remove)
    
    def _find_safe_position_for_player(self, player_id: str) -> Optional[Tuple[float, float, float]]:
        """Find a safe position to reset a player who has fallen out of bounds."""
        player = self.players[player_id]
        is_attacker = player_id in self.attacker_ids
        
        # Check if player is in a team
        if is_attacker and self.attacker_ids:
            # Find a nearby teammate
            for teammate_id in self.attacker_ids:
                if teammate_id != player_id and self.players[teammate_id].alive:
                    teammate = self.players[teammate_id]
                    return (teammate.location[0], teammate.location[1], teammate.z_position)
        elif not is_attacker and self.defender_ids:
            # Find a nearby teammate
            for teammate_id in self.defender_ids:
                if teammate_id != player_id and self.players[teammate_id].alive:
                    teammate = self.players[teammate_id]
                    return (teammate.location[0], teammate.location[1], teammate.z_position)
        
        # If no teammates found, use spawn point
        if is_attacker and self.map_data.get("attacker_spawns"):
            spawn = random.choice(self.map_data["attacker_spawns"])
            return (spawn[0], spawn[1], 0.0)
        elif not is_attacker and self.map_data.get("defender_spawns"):
            spawn = random.choice(self.map_data["defender_spawns"])
            return (spawn[0], spawn[1], 0.0)
        
        # Last resort - return to center of map
        return (16.0, 16.0, 0.0)
    
    def _get_map_collision_data(self):
        """Get collision data from map_data for player movement."""
        try:
            from app.simulation.models.map import Map
            # Create a Map object that the player's movement system can use
            map_size = self.map_data.get("metadata", {}).get("map-size", [32, 32])
            game_map = Map(self.map_data.get("metadata", {}).get("name", "Unknown"), 
                          map_size[0], map_size[1])
            
            # Load map areas, walls, etc. from map_data
            for name, area_data in self.map_data.get("map-areas", {}).items():
                game_map.areas[name] = {
                    "x": area_data["x"],
                    "y": area_data["y"],
                    "w": area_data["w"],
                    "h": area_data["h"],
                    "z": area_data.get("z", 0)
                }
            
            for name, wall_data in self.map_data.get("walls", {}).items():
                game_map.walls[name] = {
                    "x": wall_data["x"],
                    "y": wall_data["y"],
                    "w": wall_data["w"],
                    "h": wall_data["h"],
                    "z": wall_data.get("z", 0)
                }
            
            # Add objects and other collision elements
            for name, obj_data in self.map_data.get("objects", {}).items():
                if name != "instructions":
                    game_map.objects[name] = {
                        "x": obj_data["x"],
                        "y": obj_data["y"],
                        "w": obj_data["w"],
                        "h": obj_data["h"],
                        "z": obj_data.get("z", 0)
                    }
            
            return game_map
        except ImportError:
            # If Map class is not available, return a simplified object that
            # implements the necessary collision methods
            class SimpleMap:
                def is_valid_position(self, x, y, z=0.0, radius=0.5):
                    # Simple check that position is within map bounds
                    map_size = self.map_data.get("metadata", {}).get("map-size", [32, 32])
                    return 0 <= x < map_size[0] and 0 <= y < map_size[1]
                
                def get_elevation_at_position(self, x, y):
                    # By default, everything is at ground level
                    return 0.0
                
                def get_area_at_position(self, x, y, z=0.0):
                    # Simple implementation that just checks if within map bounds
                    if 0 <= x < self.map_data.get("metadata", {}).get("map-size", [32, 32])[0] and \
                       0 <= y < self.map_data.get("metadata", {}).get("map-size", [32, 32])[1]:
                        return "default-area"
                    return None
            
            simple_map = SimpleMap()
            simple_map.map_data = self.map_data
            return simple_map
    
    def _get_desired_movement_direction(self, player_id: str) -> Tuple[float, float]:
        """Calculate the desired movement direction for a player based on their current objectives."""
        player = self.players[player_id]
        is_attacker = player_id in self.attacker_ids
        
        # Default: no movement
        direction = (0, 0)
        
        # For now, implement a simple placeholder logic based on team and phase
        if self.phase == RoundPhase.BUY:
            # During buy phase, move toward position based on role
            pass
        elif self.phase == RoundPhase.ROUND:
            if is_attacker:
                if not self.spike_planted:
                    # Attackers move toward plant sites
                    site_positions = self._get_plant_site_positions()
                    if site_positions:
                        # Pick a site based on team strategy
                        team_blackboard = self.attacker_blackboard
                        strategy = team_blackboard.get("current_strategy")
                        target_site = None
                        
                        if strategy and strategy.target_site:
                            target_site = strategy.target_site
                        else:
                            # Random site if no strategy
                            target_site = random.choice(list(site_positions.keys()))
                        
                        if target_site in site_positions:
                            site_pos = site_positions[target_site]
                            direction = self._direction_to_target(player.location, site_pos)
                else:
                    # After plant, defend the spike
                    spike_pos = self._get_spike_position()
                    if spike_pos:
                        # Move near spike but not too close
                        dist_to_spike = self._calculate_distance(player.location, spike_pos)
                        if dist_to_spike > 8.0:  # Stay within reasonable distance
                            direction = self._direction_to_target(player.location, spike_pos)
                        elif dist_to_spike < 3.0:  # Too close, back up
                            direction = self._direction_to_target(spike_pos, player.location)
            else:  # Defender
                if not self.spike_planted:
                    # Defenders defend sites or rotate based on info
                    # This would be based on team strategy and enemy information
                    site_positions = self._get_plant_site_positions()
                    if site_positions:
                        # Simple strategy: distribute defenders across sites
                        site_keys = list(site_positions.keys())
                        defender_idx = self.defender_ids.index(player_id) if player_id in self.defender_ids else 0
                        assigned_site = site_keys[defender_idx % len(site_keys)]
                        site_pos = site_positions[assigned_site]
                        
                        # Only move if not already at site
                        dist_to_site = self._calculate_distance(player.location, site_pos)
                        if dist_to_site > 5.0:
                            direction = self._direction_to_target(player.location, site_pos)
                else:
                    # After plant, move toward spike
                    spike_pos = self._get_spike_position()
                    if spike_pos:
                        direction = self._direction_to_target(player.location, spike_pos)
        
        # Add some randomness to movement for more realistic behavior
        if random.random() < 0.2:  # 20% chance to add noise
            noise_x = random.uniform(-0.3, 0.3)
            noise_y = random.uniform(-0.3, 0.3)
            direction = (direction[0] + noise_x, direction[1] + noise_y)
        
        # Normalize direction vector
        if direction[0] != 0 or direction[1] != 0:
            magnitude = math.sqrt(direction[0]**2 + direction[1]**2)
            direction = (direction[0] / magnitude, direction[1] / magnitude)
        
        return direction
    
    def _direction_to_target(self, source: Tuple[float, float], target: Tuple[float, float]) -> Tuple[float, float]:
        """Calculate a normalized direction vector from source to target."""
        dx = target[0] - source[0]
        dy = target[1] - source[1]
        
        # Normalize
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > 0:
            return (dx/distance, dy/distance)
        else:
            return (0, 0)
    
    def _get_plant_site_positions(self) -> Dict[str, Tuple[float, float]]:
        """Get positions of all plant sites."""
        site_positions = {}
        for site_key, site_info in self.map_data.get("bomb-sites", {}).items():
            site_positions[site_key] = (site_info["x"] + site_info["w"]/2, site_info["y"] + site_info["h"]/2)
        return site_positions
    
    def _get_spike_position(self) -> Optional[Tuple[float, float]]:
        """Get the current position of the spike."""
        if not self.spike_planted:
            # Spike is carried by a player
            for player_id, player in self.players.items():
                if player.spike:
                    return player.location
            # Spike might be dropped
            spike_info = self.attacker_blackboard.get("spike_info")
            if spike_info and spike_info.status == "dropped":
                return spike_info.location
        else:
            # Spike is planted
            spike_info = self.attacker_blackboard.get("spike_info")
            if spike_info and spike_info.status == "planted":
                return spike_info.location
        return None

    def _update_player(self, player_id: str, time_step: float) -> None:
        """Update a single player's state."""
        player = self.players[player_id]
        if not player.alive:
            return
            
        # Movement is now handled by the physics-based movement system
        # in _simulate_player_movements
        
        # Process other status updates
        # Decay status effects over time
        new_status_effects = []
        for effect in player.status_effects:
            # In a real implementation, we would track effect durations
            # For now, each effect has a chance to wear off each update
            if effect == "flashed":
                # Flash effects are short-lived
                if random.random() < 0.3:  # 30% chance to recover per update
                    pass  # Don't add back to list
                else:
                    new_status_effects.append(effect)
            elif effect == "slowed":
                # Slow effects last a bit longer
                if random.random() < 0.2:  # 20% chance to recover per update
                    pass
                else:
                    new_status_effects.append(effect)
            else:
                # Other effects persist
                new_status_effects.append(effect)
                
        player.status_effects = new_status_effects

    def _check_round_end_conditions(self) -> None:
        """Check for round end conditions."""
        # Round timer expired
        if self.round_time_remaining <= 0 and self.phase == RoundPhase.ROUND:
            if self.spike_planted:
                # If spike is planted, round continues until spike explodes or is defused
                pass
            else:
                # Defenders win if time expires without spike plant
                self.round_winner = RoundWinner.DEFENDERS
                self.round_end_condition = RoundEndCondition.TIME_EXPIRED
                self.phase = RoundPhase.END
        
        # Spike detonated
        if self.spike_planted and self.spike_time_remaining <= 0:
            self.round_winner = RoundWinner.ATTACKERS
            self.round_end_condition = RoundEndCondition.SPIKE_DETONATION
            self.phase = RoundPhase.END
    
    def _log_death_event(
        self, victim_id: str, killer_id: str, weapon: str, is_headshot: bool
    ) -> None:
        """Log a death event for statistics tracking."""
        # Get victim position
        victim_position = self.players[victim_id].location[:2] if len(self.players[victim_id].location) >= 2 else (0.0, 0.0)
        
        # Create and store the death event
        event = DeathEvent(
            victim_id=victim_id,
            killer_id=killer_id,
            assist_ids=[],  # Would need more tracking for assists
            weapon=weapon,
            time=self.tick,
            position=victim_position,
            is_wallbang=False,  # Would need line-of-sight checks
            is_headshot=is_headshot,
        )
        self._death_events.append(event)
        
        # Update stats for existing trackers
        self.kill_count += 1
        
        # Echo to console if print_kills is True
        if self.print_kills:
            print(f"Round {self.round_number}, {self.tick:.1f}s: {killer_id} killed {victim_id} with {weapon}" + 
                  (" (headshot)" if is_headshot else ""))

    def _log_info_event(
        self, source_id: str, target_id: str, position: Tuple[float, float], 
        event_type: str, info: Dict
    ) -> None:
        """Log an information event."""
        event = InfoEvent(
            type=event_type,
            source_id=source_id,
            target_id=target_id,
            position=position,
            time=self.tick,
            info=info
        )
        
        self.info_events.append(event)
    
    def _log_comm_event(self, sender_id: str, message: str) -> None:
        """Log a team communication event."""
        event = CommEvent(
            sender_id=sender_id,
            message=message,
            time=self.tick
        )
        
        self.comms.append(event)
    
    def _log_spike_planted(self, planter_id: str) -> None:
        """Log a spike plant event for statistics tracking."""
        # Get site information
        spike_position = self._get_spike_position() or (0.0, 0.0)
        site = self._position_to_site(spike_position) or "Unknown"
        
        # Create and store the plant event
        event = {
            "planter_id": planter_id,
            "time": self.tick,
            "site": site,
            "position": spike_position,
            "remaining_defenders": len(self.get_alive_players("defenders"))
        }
        self._plant_events.append(event)
        
        # Echo to console if enabled
        print(f"Round {self.round_number}, {self.tick:.1f}s: {planter_id} planted the spike at {site}")
    
    def _log_spike_defused(self, defuser_id: str) -> None:
        """Log a spike defuse event for statistics tracking."""
        # Get site information
        spike_position = self._get_spike_position() or (0.0, 0.0)
        site = self._position_to_site(spike_position) or "Unknown"
        
        # Create and store the defuse event
        event = {
            "defuser_id": defuser_id,
            "time": self.tick,
            "site": site,
            "position": spike_position,
            "remaining_attackers": len(self.get_alive_players("attackers"))
        }
        self._defuse_events.append(event)
        
        # Echo to console if enabled
        print(f"Round {self.round_number}, {self.tick:.1f}s: {defuser_id} defused the spike at {site}")
    
    def _log_damage_event(
        self, attacker_id: str, victim_id: str, damage: int, weapon: str, 
        hitbox: str = "body", is_through_smoke: bool = False, is_wallbang: bool = False
    ) -> None:
        """Log a damage event for statistics tracking."""
        # Get positions
        attacker_position = self.players[attacker_id].location[:2] if len(self.players[attacker_id].location) >= 2 else (0.0, 0.0)
        victim_position = self.players[victim_id].location[:2] if len(self.players[victim_id].location) >= 2 else (0.0, 0.0)
        
        # Create and store the damage event
        event = {
            "attacker_id": attacker_id,
            "victim_id": victim_id,
            "damage": damage,
            "weapon": weapon,
            "hitbox": hitbox,
            "time": self.tick,
            "attacker_position": attacker_position,
            "victim_position": victim_position,
            "is_through_smoke": is_through_smoke,
            "is_wallbang": is_wallbang
        }
        self._damage_events.append(event)

    def _log_utility_usage(
        self, player_id: str, utility_type: str, position: Tuple[float, float],
        enemies_affected: int = 0, teammates_affected: int = 0
    ) -> None:
        """Log utility usage for statistics tracking."""
        # Create and store the utility event
        event = {
            "player_id": player_id,
            "utility_type": utility_type,
            "time": self.tick,
            "position": position,
            "enemies_affected": enemies_affected,
            "teammates_affected": teammates_affected
        }
        self._utility_events.append(event)

    def _log_purchase_event(
        self, player_id: str, item_type: str, cost: int
    ) -> None:
        """Log a purchase event for statistics tracking."""
        # Create and store the purchase event
        event = {
            "player_id": player_id,
            "item_type": item_type,
            "cost": cost,
            "time": self.tick
        }
        self._purchase_events.append(event)
        
    def get_alive_players(self, team: str) -> List[str]:
        """Get IDs of alive players on the specified team."""
        if team == "attackers":
            return [pid for pid in self.attacker_ids if self.players[pid].alive]
        elif team == "defenders":
            return [pid for pid in self.defender_ids if self.players[pid].alive]
        else:
            return []
    
    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Get a player by ID."""
        return self.players.get(player_id)
    
    def get_round_summary(self) -> RoundResult:
        """Get a summary of the round's current state."""
        alive_attackers = len(self.get_alive_players("attackers"))
        alive_defenders = len(self.get_alive_players("defenders"))
        
        summary = {
            "round_number": self.round_number,
            "phase": self.phase.value,
            "time_remaining": self.round_time_remaining,
            "spike_planted": self.spike_planted,
            "spike_time_remaining": self.spike_time_remaining,
            "alive_attackers": alive_attackers,
            "alive_defenders": alive_defenders,
            "winner": self.round_winner.value if self.round_winner != RoundWinner.NONE else None,
            "end_condition": self.round_end_condition.value if self.round_end_condition else None,
            "kill_count": len(self._death_events)
        }
        
        return RoundResult(self.round_number, summary)
    
    def _simulate_utility_usage(self) -> None:
        """Simulate players using their abilities."""
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            # Get available abilities
            available_abilities = player.abilities.get_available_abilities()
            
            for ability in available_abilities:
                # Simulate decision to use ability based on situation
                if self._should_use_ability(player_id, ability):
                    self._use_ability(player_id, ability)

    def _should_use_ability(self, player_id: str, ability: AbilityInstance) -> bool:
        """Decide if player should use an ability based on situation."""
        # This would be a complex decision based on many factors:
        # - Current strategy
        # - Known enemy positions
        # - Team economy
        # - Round phase
        # - etc.
        
        # For now, implement a simple placeholder logic
        return random.random() < 0.1  # 10% chance to use ability each check

    def _use_ability(self, player_id: str, ability: AbilityInstance) -> None:
        """Use an ability in the simulation."""
        player = self.players[player_id]
        
        # Determine target position based on targeting type
        target_pos = self._determine_ability_target(player_id, ability)
        if not target_pos:
            return
            
        # Update ability state
        ability.charges_remaining -= 1
        ability.is_active = True
        ability.current_position = target_pos
        ability.start_time = self.tick
        ability.end_time = self.tick + ability.definition.duration
        
        # Add to active abilities
        self.active_abilities.append(ability)
        
        # Log ability usage
        self._log_info_event(
            player_id,
            None,
            target_pos,
            "ability",
            {"type": "use", "ability": ability.definition.name}
        )
        
        # Track utility usage for statistics
        player_pos = self.players[player_id].location[:2] if len(self.players[player_id].location) >= 2 else (0.0, 0.0)
        
        # Count affected players (simplified)
        enemies_affected = 0
        teammates_affected = 0
        
        if ability.ability_type in ["flash", "smoke", "molly"]:
            # Simple radius check for affected players
            affect_radius = {
                "flash": 10.0,
                "smoke": 5.0,
                "molly": 5.0
            }.get(ability.ability_type, 3.0)
            
            for pid, other_player in self.players.items():
                if not other_player.alive:
                    continue
                    
                other_pos = other_player.location[:2] if len(other_player.location) >= 2 else (0.0, 0.0)
                distance = self._calculate_distance(player_pos, other_pos)
                
                if distance <= affect_radius:
                    if (player_id in self.attacker_ids and pid in self.defender_ids) or \
                       (player_id in self.defender_ids and pid in self.attacker_ids):
                        enemies_affected += 1
                    elif pid != player_id:  # Don't count self
                        teammates_affected += 1
        
        self._log_utility_usage(
            player_id=player_id,
            utility_type=ability.ability_type,
            position=player_pos,
            enemies_affected=enemies_affected,
            teammates_affected=teammates_affected
        )

    def _determine_ability_target(
        self, player_id: str, ability: AbilityInstance
    ) -> Optional[Tuple[float, float]]:
        """Determine where to target an ability based on current situation."""
        player = self.players[player_id]
        is_attacker = player_id in self.attacker_ids
        team_blackboard = self.attacker_blackboard if is_attacker else self.defender_blackboard
        
        # Get current strategy
        strategy = team_blackboard.get("current_strategy")
        if not strategy:
            return None
            
        # Different targeting logic based on ability type and targeting type
        if ability.definition.targeting_type == AbilityTarget.POINT:
            # For point-targeted abilities, use strategic locations
            return self._get_strategic_point(player_id, ability, strategy)
        elif ability.definition.targeting_type == AbilityTarget.PROJECTILE:
            # For projectiles, consider trajectory and bounces
            return self._get_projectile_target(player_id, ability, strategy)
        elif ability.definition.targeting_type == AbilityTarget.SELF:
            # Self-targeted abilities use player's current position
            return player.location
        elif ability.definition.targeting_type == AbilityTarget.AREA:
            # Area abilities need to consider coverage and team positioning
            return self._get_area_target(player_id, ability, strategy)
            
        return None

    def _get_strategic_point(
        self, player_id: str, ability: AbilityInstance, strategy: Any
    ) -> Optional[Tuple[float, float]]:
        """Get a strategic point to target an ability."""
        # This would use map knowledge and current strategy to determine
        # good locations for smokes, recon, etc.
        # For now, return a simple placeholder implementation
        if strategy.target_site:
            site_info = self.map_data.get("plant_sites", {}).get(strategy.target_site, {})
            return site_info.get("center", None)
        return None

    def _get_projectile_target(
        self, player_id: str, ability: AbilityInstance, strategy: Any
    ) -> Optional[Tuple[float, float]]:
        """Calculate target for projectile abilities considering bounces."""
        # This would implement complex trajectory calculations
        # For now, return a simple target
        player = self.players[player_id]
        return (
            player.location[0] + random.uniform(-ability.definition.max_range, ability.definition.max_range),
            player.location[1] + random.uniform(-ability.definition.max_range, ability.definition.max_range)
        )

    def _get_area_target(
        self, player_id: str, ability: AbilityInstance, strategy: Any
    ) -> Optional[Tuple[float, float]]:
        """Determine target for area-effect abilities."""
        # This would consider team positions and map control
        # For now, return a simple target
        if strategy.target_site:
            site_info = self.map_data.get("plant_sites", {}).get(strategy.target_site, {})
            return site_info.get("center", None)
        return None

    def _update_utility(self, time_step: float) -> None:
        """Update active ability effects on the map."""
        current_time = self.tick
        
        # Update and filter out expired abilities
        active_abilities = []
        for ability in self.active_abilities:
            if ability.get_remaining_duration(current_time) > 0:
                active_abilities.append(ability)
                
                # Apply ability effects based on type
                if ability.definition.ability_type == AbilityType.SMOKE:
                    # Smoke just blocks vision, handled in line of sight checks
                    pass
                elif ability.definition.ability_type == AbilityType.FLASH:
                    self._apply_flash_effect(ability)
                elif ability.definition.ability_type == AbilityType.MOLLY:
                    self._apply_molly_effect(ability, time_step)
                elif ability.definition.ability_type == AbilityType.RECON:
                    self._apply_recon_effect(ability)
                elif ability.definition.ability_type == AbilityType.TRAP:
                    self._check_trap_trigger(ability)
                    
        self.active_abilities = active_abilities

    def _apply_flash_effect(self, flash: AbilityInstance) -> None:
        """Apply flash effects to players looking at the flash."""
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            # Check if player is within flash radius
            distance = self._calculate_distance(player.location, flash.current_position)
            if distance <= flash.definition.effect_radius:
                # In a more complex implementation, we would check if player is looking at flash
                if "flashed" not in player.status_effects:
                    player.status_effects.append("flashed")
                    
                    # Log info event
                    self._log_info_event(
                        flash.owner_id,
                        player_id,
                        player.location,
                        "ability",
                        {"type": "flash", "ability": flash.definition.name}
                    )

    def _apply_molly_effect(self, molly: AbilityInstance, time_step: float) -> None:
        """Apply damage and slow effects to players in molly radius."""
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            # Check if player is in molly
            distance = self._calculate_distance(player.location, molly.current_position)
            if distance <= molly.definition.effect_radius:
                # Apply damage
                damage = molly.definition.damage * time_step
                player.health -= damage
                
                # Apply status effects
                for effect in molly.definition.status_effects:
                    if effect not in player.status_effects:
                        player.status_effects.append(effect)
                
                # Check if player died from molly
                if player.health <= 0:
                    self._handle_player_death(
                        player_id,
                        molly.owner_id,
                        ability_used=molly.definition.name
                    )

    def _apply_recon_effect(self, recon: AbilityInstance) -> None:
        """Reveal enemies hit by recon ability."""
        owner = self.players[recon.owner_id]
        is_attacker = recon.owner_id in self.attacker_ids
        enemy_ids = self.defender_ids if is_attacker else self.attacker_ids
        
        for enemy_id in enemy_ids:
            enemy = self.players[enemy_id]
            if not enemy.alive:
                continue
                
            # Check if enemy is hit by recon
            distance = self._calculate_distance(enemy.location, recon.current_position)
            if distance <= recon.definition.effect_radius:
                # Add to affected players
                recon.affected_players.add(enemy_id)
                
                # Reveal enemy position to all teammates
                owner_team_ids = self.attacker_ids if is_attacker else self.defender_ids
                for teammate_id in owner_team_ids:
                    self.players[teammate_id].known_enemy_positions[enemy_id] = enemy.location
                    
                # Log reveal event
                self._log_info_event(
                    recon.owner_id,
                    enemy_id,
                    enemy.location,
                    "ability",
                    {"type": "reveal", "ability": recon.definition.name}
                )

    def _check_trap_trigger(self, trap: AbilityInstance) -> None:
        """Check if any enemies trigger a trap ability."""
        is_attacker_trap = trap.owner_id in self.attacker_ids
        enemy_ids = self.defender_ids if is_attacker_trap else self.attacker_ids
        
        for enemy_id in enemy_ids:
            enemy = self.players[enemy_id]
            if not enemy.alive:
                continue
                
            # Check if enemy triggers trap
            distance = self._calculate_distance(enemy.location, trap.current_position)
            if distance <= trap.definition.effect_radius and enemy_id not in trap.affected_players:
                # Trigger trap effects
                trap.affected_players.add(enemy_id)
                
                # Apply status effects
                for effect in trap.definition.status_effects:
                    if effect not in enemy.status_effects:
                        enemy.status_effects.append(effect)
                
                # Apply damage if any
                if trap.definition.damage > 0:
                    enemy.health -= trap.definition.damage
                    if enemy.health <= 0:
                        self._handle_player_death(
                            enemy_id,
                            trap.owner_id,
                            ability_used=trap.definition.name
                        )
                
                # Log trap trigger event
                self._log_info_event(
                    trap.owner_id,
                    enemy_id,
                    enemy.location,
                    "ability",
                    {"type": "trap_trigger", "ability": trap.definition.name}
                )

    def get_carryover_state(self, loss_bonus_attackers: int = None, loss_bonus_defenders: int = None) -> Dict:
        """
        Return a summary of what each player carries to the next round,
        and the credits they should receive (win/loss, spike, kills, etc).
        Accepts optional loss bonus values for attackers and defenders.
        """
        carryover = {}
        winner = self.round_winner
        loser = RoundWinner.ATTACKERS if winner == RoundWinner.DEFENDERS else RoundWinner.DEFENDERS

        WIN_CREDITS = 3000
        # Use passed-in loss bonus if provided, else use self.loss_bonus_* values
        LOSS_CREDITS_ATTACKERS = loss_bonus_attackers if loss_bonus_attackers is not None else self.loss_bonus_attackers
        LOSS_CREDITS_DEFENDERS = loss_bonus_defenders if loss_bonus_defenders is not None else self.loss_bonus_defenders
        SPIKE_PLANT_CREDITS = 300
        SPIKE_DEFUSE_CREDITS = 300
        KILL_CREDITS = 200

        for pid, player in self.players.items():
            carryover[pid] = {
                "alive": player.alive,
                "weapon": player.weapon if player.alive else None,
                "shield": player.shield if player.alive else None,
                "creds": player.creds,
                "agent": player.agent,
                "team": "attackers" if pid in self.attacker_ids else "defenders",
                "kills": player.kills,
                "deaths": player.deaths,
                "plants": player.plants,
                "defuses": player.defuses,
                "abilities": player.abilities,  # or a summary of ability charges
            }

        for pid, state in carryover.items():
            player = self.players[pid]
            # Base win/loss
            if (winner == RoundWinner.ATTACKERS and pid in self.attacker_ids) or \
               (winner == RoundWinner.DEFENDERS and pid in self.defender_ids):
                state["round_credits"] = WIN_CREDITS
            else:
                if pid in self.attacker_ids:
                    state["round_credits"] = LOSS_CREDITS_ATTACKERS
                else:
                    state["round_credits"] = LOSS_CREDITS_DEFENDERS

            # Spike plant/defuse bonuses
            if player.plants > 0:
                state["round_credits"] += SPIKE_PLANT_CREDITS
            if player.defuses > 0:
                state["round_credits"] += SPIKE_DEFUSE_CREDITS

            # Kill rewards
            state["round_credits"] += player.kills * KILL_CREDITS

        return carryover
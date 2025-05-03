from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING, Set
import random
import math
import time as time_module

from app.simulation.models.player import Player
from app.simulation.models.blackboard import Blackboard, EconomyInfo
from app.simulation.models.ability import AbilityInstance
from app.simulation.models.map_pathfinding import PathFinder, CollisionDetector
from app.simulation.models.weapon import Weapon, WeaponFactory
# Import Map for typing but avoid circular imports
if TYPE_CHECKING:
    from app.simulation.models.map import Map, MapArea

# Constants
ROUND_TIMER = 100.0  # seconds
BUY_PHASE_TIMER = 30.0  # seconds
FIRST_ROUND_BUY_PHASE_TIMER = 45.0  # seconds
SPIKE_TIMER = 45.0  # seconds
DEFUSE_TIME = 7.0  # seconds
PLANT_TIME = 4.0  # seconds

# Combat constants
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
    weapon: Weapon
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
    """Represents an information event like spotting an enemy."""
    type: str
    source_id: str
    target_id: str
    position: Tuple[float, float, float]
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
            "winner": self.winner.value if self.winner else RoundWinner.NONE.value,
            "end_condition": self.end_condition.value if self.end_condition else None,
            "kill_count": self.kill_count
        }


class Round:
    """
    Simulates a single round of a tactical FPS match.
    
    This class handles all round mechanics including:
    - Player movement and positioning
    - Spike planting and defusing
    - Combat and utility usage
    - Round state progression and resolution
    
    The Round class now uses a Map object for all map-related operations.
    """
    def __init__(
        self,
        round_number: int,
        players: Dict[str, Player],
        attacker_ids: List[str],
        defender_ids: List[str],
        map_data: Dict = None,
        attacker_blackboard: Blackboard = None,
        defender_blackboard: Blackboard = None,
        seed: Optional[int] = None,
        loss_bonus_attackers: int = 1900,
        loss_bonus_defenders: int = 1900,
        map_obj: Map = None,
    ):
        """Initialize the round."""
        self.round_number = round_number
        self.players = players
        
        # Set player teams and reset player state
        for player_id in players:
            player = players[player_id]
            if player_id in attacker_ids:
                player.team_id = "attackers"
            elif player_id in defender_ids:
                player.team_id = "defenders"
        
        self.attacker_ids = attacker_ids
        self.defender_ids = defender_ids
        
        # Setup blackboards
        if attacker_blackboard:
            self.attacker_blackboard = attacker_blackboard
        else:
            self.attacker_blackboard = Blackboard("attackers")
        
        if defender_blackboard:
            self.defender_blackboard = defender_blackboard
        else:
            self.defender_blackboard = Blackboard("defenders")
        
        # Initialize team stats in blackboards
        self.attacker_blackboard.data["is_attacking"] = True
        self.defender_blackboard.data["is_attacking"] = False
        self.attacker_blackboard.data["current_round"] = round_number
        self.defender_blackboard.data["current_round"] = round_number
        
        # Initialize alive players in blackboards
        alive_attackers = {player_id for player_id in attacker_ids if players[player_id].alive}
        alive_defenders = {player_id for player_id in defender_ids if players[player_id].alive}
        self.attacker_blackboard.data["alive_players"] = alive_attackers
        self.defender_blackboard.data["alive_players"] = alive_defenders
        
        # Initialize economy in blackboards
        self.attacker_blackboard.data["economy"] = EconomyInfo()
        self.defender_blackboard.data["economy"] = EconomyInfo()
        
        # Store the map data for compatibility with Match class
        self.map_data = map_data if map_data is not None else {}
        
        # Store the map object or load from map_data
        if map_obj:
            self.map = map_obj
        else:
            # Load map from map_data
            self.map = Map.from_json(map_data)
                
        self.round_winner = RoundWinner.NONE
        self.round_end_condition = None
        
        # Economy settings
        self.loss_bonus_attackers = loss_bonus_attackers
        self.loss_bonus_defenders = loss_bonus_defenders
        
        # Random seed for reproducibility if specified
        if seed is not None:
            random.seed(seed)
        
        # Round status
        self.phase = RoundPhase.BUY
        self.buy_phase_time = BUY_PHASE_TIMER
        self.round_time_remaining = ROUND_TIMER
        self.tick = 0.0  # Time elapsed in the round
        
        # Spike status
        self.spike_planted = False
        self.spike_plant_time = None  # When was the spike planted
        self.spike_time_remaining = None  # Time until spike detonates
        self.spike_position = None  # Location of planted spike
        
        # Track events for statistics and replay
        self._death_events = []  # DeathEvent objects
        self._damage_events = []  # List of damage events
        self._info_events = []  # InfoEvent objects
        self._comm_events = []  # CommEvent objects
        self._purchase_events = []  # Purchase events
        self._plant_events = []  # Spike plant events
        self._defuse_events = []  # Spike defuse events
        self._utility_events = []  # Utility usage events
        self.comms = []  # Communication events list
        self.active_abilities = []  # Active abilities list
        self.tick_logs = []  # RL tick logs
        self.print_kills = False  # Whether to print kill messages
        self.kill_count = 0  # Counter for number of kills
        
        # Dropped weapons/shields
        self.dropped_weapons = []  # DroppedWeapon objects
        self.dropped_shields = []  # DroppedShield objects
        
        # Round setup
        self._set_initial_strategies()
        self._assign_spike()
        self._initialize_player_positions()
    
    def _update_alive_players_in_blackboards(self) -> None:
        """Update the alive_players sets in both blackboards."""
        alive_attackers = {player_id for player_id in self.attacker_ids if self.players[player_id].alive}
        alive_defenders = {player_id for player_id in self.defender_ids if self.players[player_id].alive}
        
        self.attacker_blackboard.data["alive_players"] = alive_attackers
        self.defender_blackboard.data["alive_players"] = alive_defenders
    
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
        """Set up initial positions for all players."""
        # Ensure attacker/defender arrays exist
        if not hasattr(self.map, 'attacker_spawns') or not self.map.attacker_spawns:
            self.map.attacker_spawns = [(2, 2)] * len(self.attacker_ids)
        
        if not hasattr(self.map, 'defender_spawns') or not self.map.defender_spawns:
            self.map.defender_spawns = [(28, 28)] * len(self.defender_ids)
        
        # Make sure we have enough spawn points (duplicate if necessary)
        while len(self.map.attacker_spawns) < len(self.attacker_ids):
            self.map.attacker_spawns.append(self.map.attacker_spawns[0])
        
        while len(self.map.defender_spawns) < len(self.defender_ids):
            self.map.defender_spawns.append(self.map.defender_spawns[0])
        
        # Shuffle spawn points
        random.shuffle(self.map.attacker_spawns)
        random.shuffle(self.map.defender_spawns)
        
        # Set attacker positions
        for i, player_id in enumerate(self.attacker_ids):
            spawn = self.map.attacker_spawns[i % len(self.map.attacker_spawns)]
            self.players[player_id].x = spawn[0]
            self.players[player_id].y = spawn[1]
            # self.players[player_id].set_position(spawn[0], spawn[1], 0.0)
            self.players[player_id].location = (spawn[0], spawn[1], 0.0)
        
        # Set defender positions
        for i, player_id in enumerate(self.defender_ids):
            spawn = self.map.defender_spawns[i % len(self.map.defender_spawns)]
            self.players[player_id].x = spawn[0]
            self.players[player_id].y = spawn[1]
            # self.players[player_id].set_position(spawn[0], spawn[1], 0.0)
            self.players[player_id].location = (spawn[0], spawn[1], 0.0)
    
    def simulate(self, time_step: float = 0.5) -> Dict:
        """
        Simulate the round forward until it ends.
        """
        while self.phase != RoundPhase.END:
            self.update(time_step)
        # Get living players on each team
        alive_attackers = sum(1 for pid in self.attacker_ids if self.players[pid].alive)
        alive_defenders = sum(1 for pid in self.defender_ids if self.players[pid].alive)
        # Determine winner
        winner = self.round_winner
        # Provide round summary
        round_summary = {
            "phase": self.phase.value,
            "time_remaining": self.round_time_remaining,
            "spike_planted": self.spike_planted,
            "spike_time_remaining": self.spike_time_remaining,
            "alive_attackers": alive_attackers,
            "alive_defenders": alive_defenders,
            "winner": winner.value if winner else RoundWinner.NONE.value,
            "end_condition": self.round_end_condition.value if self.round_end_condition else None,
            "kill_count": self.kill_count
        }
        return round_summary

    def update(self, time_step: float, match_id=None, agents_dict=None) -> None:
        """Update the round state by one time step. Optionally log RL data."""
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
        # --- RL per-tick logging ---
        self.log_tick_data(match_id=match_id, agents_dict=agents_dict)
    
    def _process_buy_phase(self, time_step: float) -> None:
        """Handle buy phase logic."""
        self.buy_phase_time -= time_step
        
        # Ensure alive_players is properly updated before buy decisions
        self._update_alive_players_in_blackboards()
        
        # Simulate players buying immediately, but keep in buy phase until timer expires
        if self.buy_phase_time <= 0:
            # Buy phase is over, transition to round phase
            self.phase = RoundPhase.ROUND
            self.round_time_remaining = ROUND_TIMER
        else:
            # Still in buy phase, but simulate buying decisions for all players
            # This ensures players have equipment even when inspecting round state during buy phase
            for player_id, player in self.players.items():
                if not hasattr(player, "_buy_simulated"):
                    self._simulate_buy_decision(player)
                    player._buy_simulated = True
    
    def _simulate_buy_decision(self, player: Player) -> None:
        """Simulate a player's buy decision based on credits available and team economy."""
        
        # Get team blackboard for this player
        team_blackboard = self.attacker_blackboard if player.id in self.attacker_ids else self.defender_blackboard
        
        # Update economy info in blackboard
        economy = team_blackboard.get("economy")
        if economy is None:
            economy = EconomyInfo()
            team_blackboard.set("economy", economy)
        
        economy.team_credits += player.creds

        # Get weapon catalog
        weapon_catalog = WeaponFactory.create_weapon_catalog()
        
        # Basic buy logic - can be expanded based on economy and team strategy
        if player.creds >= 3900:  # Full buy threshold
            # Buy rifle, heavy shield, and abilities
            player.weapon = weapon_catalog["Vandal"] if random.random() < 0.5 else weapon_catalog["Phantom"]
            player.shield = "heavy"
            player.creds -= 2900  # Rifle cost
            player.creds -= 1000  # Heavy shield cost
            economy.can_full_buy = True
        elif player.creds >= 2400:  # Light buy threshold
            # Buy SMG or shotgun and light shield
            player.weapon = weapon_catalog["Spectre"] if random.random() < 0.7 else weapon_catalog["Bulldog"]
            player.shield = "light"
            player.creds -= 1600  # SMG cost (approximation)
            player.creds -= 400   # Light shield cost
            economy.can_half_buy = True
        elif player.creds >= 950:  # Eco round
            # Buy pistol and maybe light shield
            player.weapon = weapon_catalog["Sheriff"] if random.random() < 0.6 else weapon_catalog["Ghost"]
            if player.creds >= 1400:
                player.shield = "light"
                player.creds -= 400  # Light shield cost
            player.creds -= 800  # Pistol cost (approximation)
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
            item_cost = player.weapon.cost
            item_type = f"weapon_{player.weapon.name}"
            self._log_purchase_event(player.id, item_type, item_cost)
        
        if player.shield:
            item_cost = 1000 if player.shield == "heavy" else 400
            item_type = f"shield_{player.shield}"
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
        """
        Determine which site (if any) a position is in.
        """
        if not position:
            return None
        # Accept both 2D and 3D tuples
        x, y = position[:2]
        return self.map.is_within_bomb_site(x, y)
    
    def _is_at_plant_site(self, location: Tuple[float, float]) -> bool:
        """Check if a location is within any bomb site."""
        return self._position_to_site(location) is not None
    
    def _process_spike_actions(self, time_step: float) -> None:
        """Handle spike-related actions such as planting and defusing."""
        # Handle spike planting
        for player_id in self.attacker_ids:
            player = self.players[player_id]
            if not player.alive or not player.spike:
                continue
            at_plant_site = self._is_at_plant_site(player.location)
            if at_plant_site and not player.is_planting and not self.spike_planted:
                player.start_plant(self)
            if player.is_planting and at_plant_site:
                player.plant_progress += time_step
                if player.plant_progress >= PLANT_TIME:
                    self.spike_planted = True
                    self.spike_plant_time = self.tick
                    self.spike_position = player.location
                    player.spike = False
                    player.stop_plant(self)
                    player.plants += 1
                    self.spike_time_remaining = SPIKE_TIMER
                    self._log_spike_planted(player_id)
                    plant_site = self._position_to_site(player.location)
                    spike_info = {
                        "location": player.location,
                        "status": "planted",
                        "plant_time": self.tick,
                        "plant_site": plant_site
                    }
                    self.attacker_blackboard.update_spike_info(**spike_info)
                    self.defender_blackboard.update_spike_info(**spike_info)
                    def_igl = random.choice(self.defender_ids)
                    self.defender_blackboard.set_strategy(
                        "retake", 
                        def_igl,
                        plant_site
                    )
                    att_igl = random.choice(self.attacker_ids)
                    self.attacker_blackboard.set_strategy(
                        "post_plant", 
                        att_igl,
                        plant_site
                    )
            if player.is_planting and not at_plant_site:
                player.stop_plant(self)
        # Handle spike defusing
        if self.spike_planted:
            for player_id in self.defender_ids:
                player = self.players[player_id]
                if not player.alive:
                    continue
                at_spike = self._is_near_spike(player.location)
                if at_spike and not player.is_defusing:
                    player.start_defuse(self)
                if player.is_defusing and at_spike:
                    player.defuse_progress += time_step
                    if player.defuse_progress >= DEFUSE_TIME:
                        self.spike_planted = False
                        player.stop_defuse(self)
                        player.defuses += 1
                        self.round_winner = RoundWinner.DEFENDERS
                        self.round_end_condition = RoundEndCondition.SPIKE_DEFUSED
                        self.phase = RoundPhase.END
                        self._log_spike_defused(player_id)
                        spike_info = {
                            "status": "defused",
                        }
                        self.attacker_blackboard.update_spike_info(**spike_info)
                        self.defender_blackboard.update_spike_info(**spike_info)
                if player.is_defusing and not at_spike:
                    player.stop_defuse(self)
    
    def _is_near_spike(self, location: Tuple[float, float]) -> bool:
        """Check if the location is near the planted spike."""
        if not self.spike_position:
            return False
        loc2d = location[:2] if len(location) >= 2 else location
        spike2d = self.spike_position[:2] if len(self.spike_position) >= 2 else self.spike_position
        distance = self._calculate_distance(loc2d, spike2d)
        return distance <= 3.0  # Defuse range
    
    def _calculate_distance(self, point1: Tuple[float, ...], point2: Tuple[float, ...]) -> float:
        """Calculate the distance between two points (2D or 3D)."""
        # Pad to 3D if needed
        if len(point1) == 2:
            point1 = (point1[0], point1[1], 0.0)
        if len(point2) == 2:
            point2 = (point2[0], point2[1], 0.0)
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)
    
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
        """
        Check if there is a clear line of sight between source and target.
        
        Args:
            source: (x, y) position of source
            target: (x, y) position of target
            
        Returns:
            True if there is line of sight, False otherwise
        """
        if hasattr(self.map, "raycast"):
            # Use the Map's raycast function if available
            hit_distance, hit_point, hit_boundary = self.map.raycast(
                (source[0], source[1], 0.0),  # source with z=0
                (target[0] - source[0], target[1] - source[1], 0.0),  # direction vector
                self._calculate_distance(source, target) + 0.1  # max distance slightly beyond target
            )
            return hit_boundary is None or hit_distance is None
        else:
            # Fallback to simplified line of sight check
            for wall in self.map.walls.values():
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
            if not player.alive or not player.visible_enemies and player.weapon is None:
                continue
                
            for enemy_id in player.visible_enemies:
                enemy = self.players[enemy_id]
                if not enemy.alive:
                    continue
                    
                # Use collision detector to check line of sight
                if not self.map.collision_detector.check_collision(
                    player.location,
                    enemy.location
                ):
                    self._simulate_duel(player_id, enemy_id)
    
    def _simulate_duel(self, player1_id: str, player2_id: str, accuracy_modifier: float = 1.0) -> None:
        """Simulate a duel between two players with enhanced mechanics."""
        player1 = self.players[player1_id]
        player2 = self.players[player2_id]
        
        # Calculate combat advantage
        advantage = self._calculate_combat_advantage(player1_id, player2_id)
        
        # Apply accuracy modifier
        advantage *= accuracy_modifier
        
        # Apply weapon stats if available
        if player1.weapon is not None:
            # Range-based damage
            distance = self._calculate_distance(player1.location, player2.location)
            range_type = "close" if distance < 10 else "medium" if distance < 25 else "long"
            damage_multiplier = player1.weapon.range_multipliers.get(range_type, 1.0)
            
            # Calculate damage
            base_damage = player1.weapon.damage * damage_multiplier
            
            # Armor penetration
            if player2.shield:
                armor_damage = base_damage * (1 - player1.weapon.armor_penetration)
                health_damage = base_damage * player1.weapon.armor_penetration
            else:
                armor_damage = 0
                health_damage = base_damage
            
            # Apply damage
            if player2.shield:
                player2.armor = max(0, player2.armor - int(armor_damage))
            player2.health = max(0, player2.health - int(health_damage))
            
            # Track damage
            player1.damage_dealt += int(armor_damage + health_damage)
            
            # Check for kill
            if player2.health <= 0:
                self._handle_player_death(player2_id, player1_id, weapon=player1.weapon)
        # else:
        #     # Fallback to simple combat if no weapon system
        #     if random.random() < advantage:
        #         self._handle_player_death(player2_id, player1_id, weapon=player1.weapon)

    def _calculate_combat_advantage(self, player_id: str, opponent_id: str) -> float:
        """Calculate combat advantage with enhanced mechanics."""
        player = self.players[player_id]
        opponent = self.players[opponent_id]
        
        # Base advantage from aim rating
        advantage = player.aim_rating / 100.0
        
        # Movement accuracy penalty
        if player.is_moving:
            advantage *= player.movement_accuracy / 100.0
        
        # Status effects
        if "flashed" in list(player.status_effects.keys()):
            advantage *= 0.2
        if "slowed" in list(player.status_effects.keys()):
            advantage *= 0.8
        
        # First shot advantage
        if opponent_id not in player.visible_enemies:
            advantage *= 1.5
        
        # Positional advantage (height)
        height_diff = player.location[2] - opponent.location[2]
        if height_diff > 0.5:  # Player has height advantage
            advantage *= 1.2
        
        # Distance factor
        distance = self._calculate_distance(player.location, opponent.location)
        if distance < 5.0:  # Close range
            advantage *= 0.9  # Slightly harder to track at very close range
        elif distance > 30.0:  # Long range
            advantage *= 0.8  # Harder at long range
        
        return advantage

    def _handle_player_death(self, victim_id: str, killer_id: str, weapon: str = None) -> None:
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
        self._log_death_event(victim_id, killer_id, weapon, is_headshot)
        
        # Check team elimination
        self._check_team_elimination()
    
    def _drop_weapon(self, player_id: str, weapon: Weapon, location: Tuple[float, float]) -> None:
        """Create a dropped weapon on the map."""
        # Create dropped weapon
        dropped = DroppedWeapon(
            weapon=weapon,
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
        
        if attackers_alive == 0 and not self.spike_planted:
            # All attackers eliminated before spike plant
            self.round_winner = RoundWinner.DEFENDERS
            self.round_end_condition = RoundEndCondition.ELIMINATION
            self.phase = RoundPhase.END
        elif defenders_alive == 0 and not self.spike_planted:
            # All defenders eliminated before spike plant
            self.round_winner = RoundWinner.ATTACKERS
            self.round_end_condition = RoundEndCondition.ELIMINATION
            self.phase = RoundPhase.END

    def _simulate_player_movements(self, time_step: float) -> None:
        """Simulate all player movements based on current inputs and game state."""
        # For each player, calculate movement direction based on their goals
        # and use the new physics-based movement system
        
        # Create a Map object from map_data for collision detection
        for player_id, player in self.players.items():
            if not player.alive:
                continue
                
            if player.is_planting or player.is_defusing:
                player.set_movement_input((0, 0))
                continue
            
            # Get current and target positions
            current_pos = player.location
            target_pos = self._get_player_target_position(player_id)
            
            if target_pos:
                # Check if pathfinder is available
                if hasattr(self.map, 'pathfinder') and self.map.pathfinder is not None:
                    # Find path using A* pathfinding
                    path = self.map.pathfinder.find_path(
                        start=current_pos,
                        goal=target_pos
                    )
                    
                    if path:
                        # Get next waypoint
                        next_pos = path[1] if len(path) > 1 else path[0]
                        
                        # Calculate movement direction to next waypoint
                        direction = self._direction_to_target(current_pos, next_pos)
                        
                        # Check for collisions before moving if collision_detector exists
                        if hasattr(self.map, 'collision_detector') and self.map.collision_detector is not None:
                            if not self.map.collision_detector.check_collision(
                                current_pos, next_pos
                            ):
                                player.set_movement_input(direction)
                            else:
                                # Find alternative path or wait
                                player.set_movement_input((0, 0))
                        else:
                            # No collision detector, just set the movement
                            player.set_movement_input(direction)
                else:
                    # No pathfinder, use direct movement toward target
                    direction = self._direction_to_target(current_pos, target_pos)
                    player.set_movement_input(direction)
            
            # Check for weapon pickups
            self._attempt_pickup_weapon(player)
    
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
                player.weapon = dropped.weapon
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
        """Find a safe starting position for a player in case of collision or validation issues."""
        is_attacker = player_id in self.attacker_ids
        spawn = None
        
        # Try to use team-appropriate spawn
        if self.map:
            # Ensure the map has the required attributes for pathfinding
            if not hasattr(self.map, 'nav_mesh') or self.map.nav_mesh is None:
                from app.simulation.models.map_pathfinding import NavigationMesh
                self.map.nav_mesh = NavigationMesh(self.map.width, self.map.height)
                
            if not hasattr(self.map, 'pathfinder') or self.map.pathfinder is None:
                from app.simulation.models.map_pathfinding import PathFinder
                self.map.pathfinder = PathFinder(self.map.nav_mesh)
                
            if not hasattr(self.map, 'collision_detector') or self.map.collision_detector is None:
                from app.simulation.models.map_pathfinding import CollisionDetector
                self.map.collision_detector = CollisionDetector(self.map.nav_mesh)
            
            if is_attacker and self.map.attacker_spawns:
                spawn = random.choice(self.map.attacker_spawns)
            elif not is_attacker and self.map.defender_spawns:
                spawn = random.choice(self.map.defender_spawns)
        else:
            # Legacy fallback
            if is_attacker and self.map_data.get("attacker_spawns"):
                spawn = random.choice(self.map_data["attacker_spawns"])
            elif not is_attacker and self.map_data.get("defender_spawns"):
                spawn = random.choice(self.map_data["defender_spawns"])
            
        # If no spawn found, use center of map
        if not spawn:
            if self.map:
                spawn = (self.map.width / 2, self.map.height / 2, 0)
            else:
                map_size = self.map_data.get("metadata", {}).get("map-size", [32, 32])
                spawn = (map_size[0] / 2, map_size[1] / 2, 0)
            
        # Ensure 3D coordinates
        if len(spawn) == 2:
            spawn = (spawn[0], spawn[1], 0.0)
            
        # Add jitter to avoid overlap with other players
        jitter_x = random.uniform(-1.0, 1.0)
        jitter_y = random.uniform(-1.0, 1.0)
        safe_x = spawn[0] + jitter_x
        safe_y = spawn[1] + jitter_y
        safe_z = spawn[2]
        
        # Validate position is within map bounds
        if self.map and not self.map.is_valid_position(safe_x, safe_y, safe_z):
            # Try again with less jitter
            jitter_x = random.uniform(-0.5, 0.5)
            jitter_y = random.uniform(-0.5, 0.5)
            safe_x = spawn[0] + jitter_x
            safe_y = spawn[1] + jitter_y
            
        return (safe_x, safe_y, safe_z)
    
    def _get_map_collision_data(self):
        """Get collision data for the map (walls, objects, etc.)."""
        # First try to use the Map object directly
        if hasattr(self.map, "is_valid_position"):
            return self.map
        
        # Fallback to simple map wrapper
        return SimpleMap(self.map)
        
        class SimpleMap:
            """Simple wrapper for map data to provide collision detection."""
            def __init__(self, map_obj):
                self.map = map_obj
                
            def is_valid_position(self, x, y, z=0.0, radius=0.5):
                """Simple check that position is within map bounds and not in a wall."""
                # Check map bounds
                if not (0 <= x < self.map.width and 0 <= y < self.map.height):
                    return False
                
                # Check collision with walls
                for wall in self.map.walls.values():
                    wall_x = wall.get("x", 0)
                    wall_y = wall.get("y", 0)
                    wall_w = wall.get("w", 0)
                    wall_h = wall.get("h", 0)
                    
                    # Expand wall rect by player radius for collision check
                    expanded_x = wall_x - radius
                    expanded_y = wall_y - radius
                    expanded_w = wall_w + 2 * radius
                    expanded_h = wall_h + 2 * radius
                    
                    # Check if point is inside expanded rect
                    if (expanded_x <= x <= expanded_x + expanded_w and
                        expanded_y <= y <= expanded_y + expanded_h):
                        return False
                
                # Check collision with objects
                for obj in self.map.objects.values():
                    obj_x = obj.get("x", 0)
                    obj_y = obj.get("y", 0)
                    obj_w = obj.get("w", 0)
                    obj_h = obj.get("h", 0)
                    
                    # Expand object rect by player radius for collision check
                    expanded_x = obj_x - radius
                    expanded_y = obj_y - radius
                    expanded_w = obj_w + 2 * radius
                    expanded_h = obj_h + 2 * radius
                    
                    # Check if point is inside expanded rect
                    if (expanded_x <= x <= expanded_x + expanded_w and
                        expanded_y <= y <= expanded_y + expanded_h):
                        return False
                
                return True
                
            def get_elevation_at_position(self, x, y):
                """Get elevation (z-coordinate) at position."""
                # By default, everything is at ground level
                if hasattr(self.map, "get_elevation_at_position"):
                    return self.map.get_elevation_at_position(x, y)
                return 0.0
                
            def get_area_at_position(self, x, y, z=0.0):
                """Get area name at position."""
                # Simple implementation that just checks if within map bounds
                if hasattr(self.map, "get_area_at_position"):
                    return self.map.get_area_at_position(x, y, z)
                
                if 0 <= x < self.map.width and 0 <= y < self.map.height:
                    return "main"
                return None
    
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
        """Get the center position of each plant site."""
        plant_sites = {}
        
        # Try to get bomb sites from the map object
        if hasattr(self.map, "bomb_sites"):
            for site_name, site_data in self.map.bomb_sites.items():
                if isinstance(site_data, dict):
                    # Site data is a dictionary
                    x = site_data.get("x", 0)
                    y = site_data.get("y", 0)
                    w = site_data.get("w", 0)
                    h = site_data.get("h", 0)
                    # Center of the site
                    plant_sites[site_name] = (x + w/2, y + h/2)
                else:
                    # Site data is an object with attributes
                    x = getattr(site_data, "x", 0)
                    y = getattr(site_data, "y", 0)
                    w = getattr(site_data, "width", 0)
                    h = getattr(site_data, "height", 0)
                    # Center of the site
                    plant_sites[site_name] = (x + w/2, y + h/2)
        
        return plant_sites
    
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
        
        # Process status effects
        # Decay effect durations over time and remove expired effects
        effects_to_remove = []
        for effect, duration in player.status_effects.items():
            # Reduce duration by time step
            new_duration = duration - time_step
            if new_duration <= 0:
                # Effect has expired
                effects_to_remove.append(effect)
            else:
                # Update remaining duration
                player.status_effects[effect] = new_duration
                
        # Remove expired effects
        for effect in effects_to_remove:
            del player.status_effects[effect]
            
        # Note: Continuous effects like molly damage are handled by their respective
        # ability instances in their update methods, which will maintain the effect
        # duration as long as the player remains in the area of effect

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
        self._info_events.append(event)
    
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
        # Check if _purchase_events exists, and create it if not
        if not hasattr(self, "_purchase_events"):
            self._purchase_events = []
            
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
        alive_attackers = sum(1 for pid in self.attacker_ids if self.players[pid].alive)
        alive_defenders = sum(1 for pid in self.defender_ids if self.players[pid].alive)
        
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
                
            # Check if player has abilities attribute
            if not hasattr(player, 'abilities'):
                # Skip players without abilities
                continue
                
            # Get available abilities
            available_abilities = player.abilities.get_available_abilities()
            
            for ability in available_abilities:
                # Simulate decision to use ability based on situation
                if self._should_use_ability(player_id, ability):
                    self._use_ability(player_id, ability)

    def _should_use_ability(self, player_id: str, ability: AbilityInstance) -> bool:
        """Decide if player should use an ability based on situation."""
        player = self.players[player_id]
        
        # Check if player has abilities attribute
        if not hasattr(player, 'abilities'):
            return False
        
        # This would be a complex decision based on many factors:
        # - Current strategy
        # - Known enemy positions
        # - Team economy
        # - Round phase
        # - etc.
        
        # For now, implement a simple placeholder logic
        return random.random() < 0.1  # 10% chance to use ability each check

    def _use_ability(self, player_id: str, ability_name: str, target_location: Tuple[float, float], charge_time: float = 0.0) -> None:
        """Handle ability usage with proper mechanics."""
        player = self.players[player_id]
        if not player.alive:
            return
            
        # Check if player has abilities attribute
        if not hasattr(player, 'abilities'):
            return
            
        # Check if ability exists
        if ability_name not in player.abilities:
            return
            
        # Check if ability has clear path to target
        if not self.map.collision_detector.check_collision(
            player.location,
            target_location
        ):
            ability = player.abilities[ability_name]
            
        if not ability.is_available():
            return
            
        # Convert 2D target to 3D
        target_3d = (target_location[0], target_location[1], 0.0)
        
        # Calculate direction from player to target
        player_pos = player.location
        dx = target_3d[0] - player_pos[0]
        dy = target_3d[1] - player_pos[1]
        dz = target_3d[2] - player_pos[2]
        
        # Normalize direction
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length > 0:
            direction = (dx/length, dy/length, dz/length)
        else:
            direction = (1.0, 0.0, 0.0)  # Default forward direction
        
        # Activate the ability
        ability.activate(
            current_time=self.tick,
            origin=player_pos,
            direction=direction
        )
        
        # Add to active abilities
        self.active_abilities.append(ability)
        
        # Log ability usage
        self._log_utility_usage(
            player_id=player_id,
            utility_type=ability.definition.ability_type.value,
            position=player_pos,
            enemies_affected=0,  # Will be updated when ability affects players
            teammates_affected=0
        )

    def _update_utility(self, time_step: float) -> None:
        """Update active abilities with proper mechanics."""
        current_time = self.tick
        
        # Update and filter active abilities
        active_abilities = []
        for ability in self.active_abilities:
            if ability.get_remaining_duration(current_time) > 0:
                # Update ability state
                ability.update(time_step, current_time, self.map, list(self.players.values()))
                active_abilities.append(ability)
                
                # Track affected players
                if ability.effect_applied:
                    enemies_affected = 0
                    teammates_affected = 0
                    ability_owner = self.players[ability.owner_id]
                    
                    for pid in ability.affected_players:
                        if pid in self.players:
                            affected_player = self.players[pid]
                            if (ability_owner.id in self.attacker_ids) == (affected_player.id in self.attacker_ids):
                                teammates_affected += 1
                            else:
                                enemies_affected += 1
                    
                    # Update utility stats
                    self._log_utility_usage(
                        player_id=ability.owner_id,
                        utility_type=ability.definition.ability_type.value,
                        position=ability.current_position3d or ability.origin,
                        enemies_affected=enemies_affected,
                        teammates_affected=teammates_affected
                    )
        
        self.active_abilities = active_abilities

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

    def notify_planting_started(self, player):
        """Called when a player starts planting the spike."""
        self.attacker_blackboard.add_warning(
            f"Spike being planted by {player.name}",
            player.location
        )
        # Optionally, set a flag or update map state if needed
        # self.planting_in_progress = True
        print(f"[ROUND] Planting started by {player.id} at {player.location}")

    def notify_planting_stopped(self, player):
        """Called when a player stops planting the spike."""
        self.attacker_blackboard.add_warning(
            f"Spike planting stopped by {player.name}",
            player.location
        )
        # Optionally, clear a flag or update map state if needed
        # self.planting_in_progress = False
        print(f"[ROUND] Planting stopped by {player.id} at {player.location}")

    def notify_defusing_started(self, player):
        """Called when a player starts defusing the spike."""
        self.defender_blackboard.add_warning(
            f"Spike being defused by {player.name}",
            player.location
        )
        print(f"[ROUND] Defusing started by {player.id} at {player.location}")

    def notify_defusing_stopped(self, player):
        """Called when a player stops defusing the spike."""
        self.defender_blackboard.add_warning(
            f"Spike defusing stopped by {player.name}",
            player.location
        )
        print(f"[ROUND] Defusing stopped by {player.id} at {player.location}")

    def log_tick_data(self, match_id=None, agents_dict=None):
        """
        Log (obs, action, reward, done) for each player at this tick.
        Args:
            match_id: Optional match identifier
            agents_dict: Dict of player_id -> agent (must have decide_action method)
        Appends a dict per player to self.tick_logs.
        """
        for player_id, player in self.players.items():
            # Determine team blackboard
            team_blackboard = self.attacker_blackboard if player_id in self.attacker_ids else self.defender_blackboard
            obs = player.get_observation(self, team_blackboard)
            action = None
            if agents_dict and player_id in agents_dict:
                action = agents_dict[player_id].decide_action(self)
            else:
                action = None
            # For now, reward is 0 unless player has a reward attribute
            reward = getattr(player, 'reward', 0)
            # Done if player is dead or round is over
            done = (not player.alive) or (self.phase == RoundPhase.END)
            self.tick_logs.append({
                'match_id': match_id,
                'round_number': self.round_number,
                'tick': getattr(self, 'tick', None),
                'player_id': player_id,
                'observation': obs,
                'action': action,
                'reward': reward,
                'done': done
            })

    def _get_player_target_position(self, player_id: str) -> Tuple[float, float, float]:
        """Get the target position for a player based on their current objective."""
        player = self.players[player_id]
        is_attacker = player_id in self.attacker_ids
        
        # Default to current position
        current_pos = player.location
        if len(current_pos) == 2:
            current_pos = (current_pos[0], current_pos[1], 0.0)
        
        # If in buy phase, stay at spawn
        if self.phase == RoundPhase.BUY:
            return current_pos
            
        # If planting or defusing, stay put
        if player.is_planting or player.is_defusing:
            return current_pos
            
        # Initialize target position with current position
        target_pos = current_pos
        
        if self.phase == RoundPhase.ROUND:
            if is_attacker:
                # Attackers logic
                if not self.spike_planted:
                    # Try to move to a bomb site
                    site_positions = self._get_plant_site_positions()
                    if site_positions:
                        # Get target site from team strategy if available
                        team_blackboard = self.attacker_blackboard
                        strategy = team_blackboard.get("current_strategy")
                        target_site = None
                        
                        if strategy and hasattr(strategy, 'target_site') and strategy.target_site:
                            target_site = strategy.target_site
                        else:
                            # Random site if no strategy
                            target_site = random.choice(list(site_positions.keys()))
                        
                        if target_site in site_positions:
                            site_pos = site_positions[target_site]
                            target_pos = (site_pos[0], site_pos[1], 0.0)
                else:
                    # After plant, defend the spike
                    spike_pos = self._get_spike_position()
                    if spike_pos:
                        # Move near spike but not too close
                        dist_to_spike = self._calculate_distance(player.location, spike_pos)
                        if dist_to_spike > 8.0:  # Stay within reasonable distance
                            target_pos = (spike_pos[0], spike_pos[1], 0.0)
                        elif dist_to_spike < 3.0:  # Too close, back up
                            # Move away from spike slightly
                            direction = self._direction_to_target(spike_pos, player.location)
                            target_pos = (
                                player.location[0] + direction[0] * 3.0,
                                player.location[1] + direction[1] * 3.0,
                                0.0
                            )
            else:
                # Defenders logic
                if not self.spike_planted:
                    # Defend sites
                    site_positions = self._get_plant_site_positions()
                    if site_positions:
                        # Assign defenders to sites based on index
                        site_keys = list(site_positions.keys())
                        defender_idx = self.defender_ids.index(player_id) if player_id in self.defender_ids else 0
                        assigned_site = site_keys[defender_idx % len(site_keys)]
                        site_pos = site_positions[assigned_site]
                        
                        # Only move if not already at site
                        dist_to_site = self._calculate_distance(player.location, site_pos)
                        if dist_to_site > 5.0:
                            target_pos = (site_pos[0], site_pos[1], 0.0)
                else:
                    # After plant, move toward spike
                    spike_pos = self._get_spike_position()
                    if spike_pos:
                        target_pos = (spike_pos[0], spike_pos[1], 0.0)
        
        # Ensure we have a 3D position
        if len(target_pos) == 2:
            target_pos = (target_pos[0], target_pos[1], 0.0)
            
        return target_pos
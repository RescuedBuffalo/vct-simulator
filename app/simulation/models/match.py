from app.simulation.models.player import Player
from app.simulation.models.map import Map
from app.simulation.models.round import Round, RoundResult, RoundWinner, RoundEndCondition, DeathEvent
from app.simulation.models.team import Team
from app.simulation.models.weapon import Weapon
from app.simulation.models.ability import AbilityInstance
from app.simulation.models.match_stats import MatchStats

from typing import Dict, List, Optional, Tuple, Any, Union, Set

class MatchResult:
    def __init__(self, team_a_score: int, team_b_score: int):
        self.team_a_score = team_a_score
        self.team_b_score = team_b_score

class Match:
    def __init__(self, map: Map, round: Round, team_a: Team, team_b: Team):
        self.map = map
        
        self.round = round
        self.team_a = team_a
        self.team_b = team_b

        self.map_picked_by = None
        self.starting_side = None # the team that DID NOT pick the map, chooses the side they will start on

        self.team_a_score = 0
        self.team_b_score = 0

        self.current_half = 1
        self.current_round = 1
        self.is_overtime = False

        self.round_results: Dict[int, RoundResult] = {}
        self.match_results: MatchResult = None
        
        # Enhanced match statistics tracking
        self.stats = MatchStats()
        self.stats.map_name = getattr(self.map, 'name', 'Unknown Map')
        
        # Initialize player statistics for all players
        for player in self.team_a.players:
            self.stats.initialize_player(player.id)
        for player in self.team_b.players:
            self.stats.initialize_player(player.id)

        self.loss_streak_a = 0
        self.loss_streak_b = 0
        
        # Match timing
        self.match_start_time = 0.0
        self.match_end_time = 0.0

        self.timeouts_remaining = {team_a.id: 1, team_b.id: 1}  # 1 timeout per team by default
        self.timeout_duration = 60.0  # 60 seconds simulation time
        self.timeout_pending = None  # None or team_id if a timeout is pending
        self.timeout_timer = 0.0

    def agent_selection_phase(self, agent_choices: dict = None):
        """
        Assign agents to all players before the match starts.
        agent_choices: Optional dict mapping player_id to agent name. If not provided, assign randomly.
        """
        import random
        AGENTS = ["Jett", "Sage", "Phoenix", "Brimstone", "Viper", "Omen", "Sova", "Reyna", "Killjoy", "Cypher"]
        all_players = self.team_a.players + self.team_b.players
        assigned_agents = set()
        for player in all_players:
            if agent_choices and player.id in agent_choices:
                player.agent = agent_choices[player.id]
            else:
                # Assign a random agent not already taken (if possible)
                available = [a for a in AGENTS if a not in assigned_agents]
                if not available:
                    available = AGENTS  # allow duplicates if all taken
                player.agent = random.choice(available)
            assigned_agents.add(player.agent)

    def call_timeout(self, team_id):
        """Call a timeout for the given team if available."""
        if self.timeouts_remaining.get(team_id, 0) > 0 and self.timeout_pending is None:
            self.timeout_pending = team_id
            self.timeout_timer = self.timeout_duration
            self.timeouts_remaining[team_id] -= 1
            return True
        return False

    def run(self):
        # Constants
        ROUNDS_TO_WIN = 13
        MAX_REGULAR_ROUNDS = 24
        OVERTIME_ROUNDS = 2
        halftime_round = 13
        self.current_half = 1
        self.is_overtime = False
        self.current_round = 1
        max_rounds = MAX_REGULAR_ROUNDS
        overtime_active = False
        
        # Track match start time
        self.match_start_time = 0.0  # Simulation time
        
        # Prepare player state references
        players = self.round.players
        attacker_ids = self.round.attacker_ids
        defender_ids = self.round.defender_ids
        map_data = self.round.map_data
        attacker_blackboard = self.round.attacker_blackboard
        defender_blackboard = self.round.defender_blackboard

        # Agent selection phase before first round
        self.agent_selection_phase()

        while True:
            # Handle timeout if pending
            if self.timeout_pending:
                if self.timeout_timer > 0:
                    self.timeout_timer -= 1.0  # Simulate 1s per loop iteration (or adjust as needed)
                    continue  # Pause match progression during timeout
                else:
                    self.timeout_pending = None

            # Regulation end or win conditions
            if not self.is_overtime:
                # Win in regulation
                if self.team_a_score >= ROUNDS_TO_WIN or self.team_b_score >= ROUNDS_TO_WIN:
                    break
                # Regulation rounds exhausted
                if self.current_round > max_rounds:
                    # If tied at regulation end, enter overtime
                    if self.team_a_score == self.team_b_score:
                        self.is_overtime = True
                        # add overtime frames
                        max_rounds = self.current_round + OVERTIME_ROUNDS
                    else:
                        break
            else:
                # In overtime: need a 2-round lead and at least 13 rounds
                if abs(self.team_a_score - self.team_b_score) >= 2 and (self.team_a_score >= ROUNDS_TO_WIN or self.team_b_score >= ROUNDS_TO_WIN):
                    break

            # Reset abilities and ultimates for both teams at round start
            self.team_a.reset_abilities_and_ultimates()
            self.team_b.reset_abilities_and_ultimates()
            
            # Track round equipment values
            team_a_equipment = sum(self._calculate_player_equipment_value(p) for p in self.team_a.players)
            team_b_equipment = sum(self._calculate_player_equipment_value(p) for p in self.team_b.players)
            
            # Run the round
            round_result = self.round.simulate()
            self.round_results[self.current_round] = self.round.get_round_summary()
            
            # Process round statistics
            self._process_round_statistics(
                round_number=self.current_round,
                round_obj=self.round,
                round_result=round_result,
                team_a_equipment=team_a_equipment,
                team_b_equipment=team_b_equipment,
                is_overtime=self.is_overtime
            )
            
            # Update scores
            if round_result["winner"] == "attackers":
                if self.current_half == 1:
                    self.team_a_score += 1
                    self.loss_streak_a = 0
                    self.loss_streak_b += 1
                else:
                    self.team_b_score += 1
                    self.loss_streak_b = 0
                    self.loss_streak_a += 1
            elif round_result["winner"] == "defenders":
                if self.current_half == 1:
                    self.team_b_score += 1
                    self.loss_streak_b = 0
                    self.loss_streak_a += 1
                else:
                    self.team_a_score += 1
                    self.loss_streak_a = 0
                    self.loss_streak_b += 1
            
            # Update player carryover state and credits
            carryover = self.round.get_carryover_state(
                loss_bonus_attackers=1900 + min(self.loss_streak_a, 4) * 500,
                loss_bonus_defenders=1900 + min(self.loss_streak_b, 4) * 500
            )
            for pid, state in carryover.items():
                player = players[pid]
                player.creds += state["round_credits"]
                if not state["alive"]:
                    player.weapon = None
                    player.shield = None
                player.health = 100
                player.status_effects = []
                player.alive = True
                player.spike = False
                player.is_planting = False
                player.is_defusing = False
                player.plant_progress = 0.0
                player.defuse_progress = 0.0
            for pid, state in carryover.items():
                player = players[pid]
                if state["plants"] > 0:
                    if pid in self.team_a.alive_players:
                        self.team_a.increment_player_ult(pid)
                    else:
                        self.team_b.increment_player_ult(pid)
                if state["defuses"] > 0:
                    if pid in self.team_a.alive_players:
                        self.team_a.increment_player_ult(pid)
                    else:
                        self.team_b.increment_player_ult(pid)
                if state["kills"] > 0:
                    if pid in self.team_a.alive_players:
                        self.team_a.increment_player_ult(pid, state["kills"])
                    else:
                        self.team_b.increment_player_ult(pid, state["kills"])
            
            # Side switch at halftime
            if self.current_round == halftime_round:
                self._switch_sides(players, attacker_ids, defender_ids)
                self.current_half += 1
            
            # Overtime logic
            if self.team_a_score == 12 and self.team_b_score == 12 and not self.is_overtime:
                self.is_overtime = True
                overtime_active = True
                max_rounds = self.current_round + OVERTIME_ROUNDS
            
            # If in overtime and both teams tied after OVERTIME_ROUNDS, add more rounds
            if self.is_overtime and (self.current_round - halftime_round) % OVERTIME_ROUNDS == 0 and self.team_a_score == self.team_b_score:
                max_rounds += OVERTIME_ROUNDS
            
            self.current_round += 1
            self.round = Round(
                round_number=self.current_round,
                players=players,
                attacker_ids=attacker_ids,
                defender_ids=defender_ids,
                map_data=map_data,
                attacker_blackboard=attacker_blackboard,
                defender_blackboard=defender_blackboard
            )

        # After match ends, mark overtime if extra rounds were played
        if self.current_round > MAX_REGULAR_ROUNDS:
            self.is_overtime = True
            
        # Record match end time
        self.match_end_time = self.current_round * 100.0  # Approximate duration
        
        # Finalize match statistics
        self.stats.record_match_end(
            winner="team_a" if self.team_a_score > self.team_b_score else "team_b",
            final_score_a=self.team_a_score,
            final_score_b=self.team_b_score,
            match_duration=self.match_end_time - self.match_start_time,
            total_rounds=self.current_round - 1
        )

    def _switch_sides(self, players, attacker_ids, defender_ids):
        # Swap attacker/defender roles for teams and players
        attacker_ids[:], defender_ids[:] = defender_ids[:], attacker_ids[:]
        # Update player team assignments if needed
        for pid in players:
            player = players[pid]
            if pid in attacker_ids:
                player.team = "attackers"
            else:
                player.team = "defenders"

    def update_player_knowledge(self, player: Player):
        pass

    def get_match_summary(self) -> MatchResult:
        return MatchResult(self.team_a_score, self.team_b_score)
    
    def get_detailed_match_stats(self) -> Dict:
        """Get detailed match statistics."""
        return self.stats.get_match_summary()

    def get_round_summary(self) -> RoundResult:
        return self.round_results[self.current_round]

    def handle_orb_pickup(self, player_id: str, team: str):
        """Call this when a player picks up an orb to increment ult points."""
        if team == "attackers":
            self.team_a.increment_player_ult(player_id)
        else:
            self.team_b.increment_player_ult(player_id)
            
    def _process_round_statistics(self, round_number: int, round_obj: Round, round_result: Dict, 
                                team_a_equipment: int, team_b_equipment: int, is_overtime: bool = False):
        """Process and record statistics from a round."""
        # Get side information
        team_a_side = "attack" if self.current_half == 1 else "defense"
        team_b_side = "defense" if self.current_half == 1 else "attack"
        
        # Get round end condition
        end_condition = round_result.get("end_condition", "")
        site = round_result.get("site", None)
        time_remaining = round_result.get("time_remaining", 0.0)
        
        # Count alive players
        team_a_alive = sum(1 for p in self.team_a.players if p.alive)
        team_b_alive = sum(1 for p in self.team_b.players if p.alive)
        
        # Record round result in statistics
        self.stats.record_round_result(
            round_number=round_number,
            winner="team_a" if (
                (round_result["winner"] == "attackers" and team_a_side == "attack") or
                (round_result["winner"] == "defenders" and team_a_side == "defense")
            ) else "team_b",
            end_condition=end_condition,
            site=site,
            time_remaining=time_remaining,
            team_a_alive=team_a_alive,
            team_b_alive=team_b_alive,
            team_a_equipment=team_a_equipment,
            team_b_equipment=team_b_equipment,
            team_a_side=team_a_side,
            team_b_side=team_b_side,
            is_overtime=is_overtime
        )
        
        # Process kill events
        for death_event in round_obj._death_events:
            self._process_death_event(round_number, death_event)
        
        # Process plant events
        for plant_event in round_obj._plant_events:
            self._process_plant_event(round_number, plant_event)
        
        # Process defuse events
        for defuse_event in round_obj._defuse_events:
            self._process_defuse_event(round_number, defuse_event)
        
        # Process utility events (if tracked)
        for utility_event in getattr(round_obj, "_utility_events", []):
            self._process_utility_event(round_number, utility_event)
        
        # Process damage events (if tracked)
        for damage_event in getattr(round_obj, "_damage_events", []):
            self._process_damage_event(round_number, damage_event)
    
    def _process_death_event(self, round_number: int, death_event: DeathEvent):
        """Process a death event and record kill statistics."""
        # Extract data from death event
        victim_id = death_event.victim_id
        killer_id = death_event.killer_id
        weapon = death_event.weapon
        time = death_event.time
        position = death_event.position
        is_headshot = death_event.is_headshot
        is_wallbang = death_event.is_wallbang
        
        # Determine teams
        victim_team = self._get_player_team(victim_id)
        killer_team = "team_a" if killer_id in [p.id for p in self.team_a.players] else "team_b"
        
        # Determine if first blood
        is_first_blood = len([e for e in self.round._death_events if e.time <= time]) == 1
        
        # Get assist IDs (if available)
        assist_ids = death_event.assist_ids if hasattr(death_event, "assist_ids") else []
        
        # Record kill in match statistics
        self.stats.record_kill(
            round_number=round_number,
            time=time,
            killer_id=killer_id,
            victim_id=victim_id,
            weapon=weapon,
            is_headshot=is_headshot,
            position=position,
            is_wallbang=is_wallbang,
            assist_ids=assist_ids,
            is_first_blood=is_first_blood,
            is_trade=False,  # Would need more sophisticated logic
            is_through_smoke=False,  # Would need more tracking
            flash_assist_id=None,  # Would need more tracking
            killer_health=self.round.players[killer_id].health if killer_id in self.round.players else 100,
            killer_team=killer_team,
            victim_team=victim_team
        )
    
    def _process_plant_event(self, round_number: int, plant_event):
        """Process a spike plant event."""
        # Extract data from plant event
        planter_id = plant_event.get("planter_id", "")
        site = plant_event.get("site", "")
        time = plant_event.get("time", 0.0)
        
        # Determine team
        planter_team = self._get_player_team(planter_id)
        
        # Get remaining defenders
        remaining_defenders = sum(1 for p in self.team_b.players if self.current_half == 1 and p.alive) or \
                             sum(1 for p in self.team_a.players if self.current_half == 2 and p.alive)
        
        # Record plant in match statistics
        self.stats.record_plant(
            round_number=round_number,
            time=time,
            planter_id=planter_id,
            site=site,
            position=(0.0, 0.0),  # Position data may not be available
            team=planter_team,
            remaining_defenders=remaining_defenders,
            time_elapsed=100.0 - self.round.round_time_remaining
        )
    
    def _process_defuse_event(self, round_number: int, defuse_event):
        """Process a spike defuse event."""
        # Extract data from defuse event
        defuser_id = defuse_event.get("defuser_id", "")
        site = defuse_event.get("site", "")
        time = defuse_event.get("time", 0.0)
        
        # Determine team
        defuser_team = self._get_player_team(defuser_id)
        
        # Get remaining attackers
        remaining_attackers = sum(1 for p in self.team_a.players if self.current_half == 1 and p.alive) or \
                             sum(1 for p in self.team_b.players if self.current_half == 2 and p.alive)
        
        # Determine if this was a retake (simplified logic)
        was_retake = False  # Would need more tracking
        
        # Record defuse in match statistics
        self.stats.record_defuse(
            round_number=round_number,
            time=time,
            defuser_id=defuser_id,
            site=site,
            position=(0.0, 0.0),  # Position data may not be available
            team=defuser_team,
            remaining_attackers=remaining_attackers,
            was_retake=was_retake
        )
    
    def _process_utility_event(self, round_number: int, utility_event):
        """Process a utility usage event."""
        # This would need to be implemented if utility events are tracked
        pass
    
    def _process_damage_event(self, round_number: int, damage_event):
        """Process a damage event."""
        # This would need to be implemented if damage events are tracked
        pass
    
    def _get_player_team(self, player_id: str) -> str:
        """Get the team (team_a or team_b) for a player ID."""
        if any(p.id == player_id for p in self.team_a.players):
            return "team_a"
        else:
            return "team_b"
    
    def _calculate_player_equipment_value(self, player: Player) -> int:
        """Calculate the equipment value for a player."""
        value = 0
        
        # Weapon values
        weapon_values = {
            "Classic": 0,    # Free
            "Shorty": 150,
            "Frenzy": 450,
            "Ghost": 500,
            "Sheriff": 800,
            "Stinger": 950,
            "Spectre": 1600,
            "Bucky": 850,
            "Judge": 1850,
            "Bulldog": 2050,
            "Guardian": 2250,
            "Phantom": 2900,
            "Vandal": 2900,
            "Marshal": 950,
            "Operator": 4700,
            "Ares": 1600,
            "Odin": 3200
        }
        
        # Add weapon value
        if player.weapon and player.weapon in weapon_values:
            value += weapon_values[player.weapon]
        
        # Add shield value
        if player.shield == "light":
            value += 400
        elif player.shield == "heavy":
            value += 1000
        
        # Add abilities value (approximation)
        value += 400  # Average ability cost
        
        return value
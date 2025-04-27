from app.simulation.models.player import Player
from app.simulation.models.map import Map
from app.simulation.models.round import Round, RoundResult
from app.simulation.models.team import Team
from app.simulation.models.weapon import Weapon
from app.simulation.models.ability import AbilityInstance

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

        self.loss_streak_a = 0
        self.loss_streak_b = 0

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

        # Prepare player state references
        players = self.round.players
        attacker_ids = self.round.attacker_ids
        defender_ids = self.round.defender_ids
        map_data = self.round.map_data
        attacker_blackboard = self.round.attacker_blackboard
        defender_blackboard = self.round.defender_blackboard

        while self.team_a_score < ROUNDS_TO_WIN and self.team_b_score < ROUNDS_TO_WIN and self.current_round <= max_rounds:
            # Reset abilities and ultimates for both teams at round start
            self.team_a.reset_abilities_and_ultimates()
            self.team_b.reset_abilities_and_ultimates()
            
            # Run the round
            round_result = self.round.simulate()
            self.round_results[self.current_round] = self.round.get_round_summary()

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
                # Update credits
                player.creds += state["round_credits"]
                # Reset weapon/shield if dead
                if not state["alive"]:
                    player.weapon = None
                    player.shield = None
                # Reset health, status, etc.
                player.health = 100
                player.status_effects = []
                player.alive = True
                player.spike = False
                player.is_planting = False
                player.is_defusing = False
                player.plant_progress = 0.0
                player.defuse_progress = 0.0
                # Optionally reset ability charges here

            # Increment ult points for round events (kills, plants, defuses)
            for pid, state in carryover.items():
                player = players[pid]
                # 1 point for plant, defuse, or kill (typical Valorant rules)
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
                max_rounds += OVERTIME_ROUNDS  # Add overtime rounds

            self.current_round += 1
            # Prepare next round (create new Round object with updated player states)
            self.round = Round(
                round_number=self.current_round,
                players=players,
                attacker_ids=attacker_ids,
                defender_ids=defender_ids,
                map_data=map_data,
                attacker_blackboard=attacker_blackboard,
                defender_blackboard=defender_blackboard
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

    def get_round_summary(self) -> RoundResult:
        return self.round_results[self.current_round]

    def handle_orb_pickup(self, player_id: str, team: str):
        """Call this when a player picks up an orb to increment ult points."""
        if team == "attackers":
            self.team_a.increment_player_ult(player_id)
        else:
            self.team_b.increment_player_ult(player_id)
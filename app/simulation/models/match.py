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

    def run(self):
        pass

    def update_player_knowledge(self, player: Player):
        pass

    def get_match_summary(self) -> MatchResult:
        return MatchResult(self.team_a_score, self.team_b_score)

    def get_round_summary(self) -> RoundResult:
        return self.round_results[self.current_round]
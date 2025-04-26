from app.simulation.models.player import Player
from app.simulation.models.map import Map
from app.simulation.models.round import Round
from app.simulation.models.team import Team
from app.simulation.models.weapon import Weapon
from app.simulation.models.ability import AbilityInstance

class SimulationEngine:
    def __init__(self, map: Map, round: Round, team: Team):
        self.map = map
        self.round = round
        self.team = team

    def run(self):
        pass

    def update_player_knowledge(self, player: Player):
        pass
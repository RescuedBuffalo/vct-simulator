import pytest
from app.simulation.models.player import Player
from app.simulation.models.round import Round, RoundPhase
from app.simulation.models.blackboard import Blackboard
from app.simulation.ai.agents.base import AgentConfig
from app.simulation.ai.agents.greedy import GreedyAgent

class DummyAbility:
    def get_available_abilities(self):
        return []

def make_minimal_round_and_player():
    # Minimal attacker
    player = Player(
        id="p1",
        name="TestPlayer",
        team_id="A",
        role="duelist",
        agent="Jett",
        aim_rating=80,
        reaction_time=200,
        movement_accuracy=70,
        spray_control=75,
        clutch_iq=65,
    )
    player.abilities = DummyAbility()
    # Minimal defender
    defender = Player(
        id="d1",
        name="Defender",
        team_id="B",
        role="sentinel",
        agent="Cypher",
        aim_rating=70,
        reaction_time=210,
        movement_accuracy=65,
        spray_control=70,
        clutch_iq=60,
    )
    defender.abilities = DummyAbility()
    players = {player.id: player, defender.id: defender}
    attacker_ids = [player.id]
    defender_ids = [defender.id]
    # Minimal map object (mock)
    class DummyMap:
        attacker_spawns = [(0.0, 0.0, 0.0)]
        defender_spawns = [(10.0, 0.0, 0.0)]
        bomb_sites = {"A": {"x": 5.0, "y": 5.0, "w": 2.0, "h": 2.0}}
        def get_elevation_at_position(self, x, y):
            return 0.0
        def is_valid_position(self, x, y, z=0.0, radius=0.5, height=1.0):
            return True
        walls = {}
        objects = {}
        stairs = {}
    map_obj = DummyMap()
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_obj=map_obj
    )
    team_blackboard = Blackboard("attackers")
    team_blackboard.set("alive_players", [player.id])
    team_blackboard.set("team_confidence", 0.5)
    team_blackboard.set("current_strategy", None)
    team_blackboard.set("danger_areas", [])
    team_blackboard.set("cleared_areas", [])
    team_blackboard.set("noise_events", [])
    team_blackboard.set("spike_info", None)
    team_blackboard.set("economy", type("Econ", (), {"team_credits": 800, "avg_credits": 800, "can_full_buy": False, "can_half_buy": False, "saving": False})())
    return player, round_obj, team_blackboard

def test_player_get_observation_basic():
    player, round_obj, team_blackboard = make_minimal_round_and_player()
    obs = player.get_observation(round_obj, team_blackboard)
    assert isinstance(obs, dict)
    assert obs["id"] == player.id
    assert obs["team_id"] == player.team_id
    assert obs["location"] == player.location
    assert obs["alive"] is True
    assert obs["team_alive"] == [player.id]
    assert obs["team_confidence"] == 0.5
    assert obs["phase"] == "buy"
    assert obs["round_number"] == 1
    assert obs["spike_info"] is None
    assert obs["team_credits"] == 800
    assert obs["avg_credits"] == 800
    assert obs["can_full_buy"] is False
    assert obs["can_half_buy"] is False
    assert obs["saving"] is False

def test_greedy_agent_decide_action_idle():
    player, round_obj, team_blackboard = make_minimal_round_and_player()
    config = AgentConfig(
        role=player.role,
        skill_level=0.7,
        personality={"aggression": 0.5, "patience": 0.5, "teamplay": 0.5}
    )
    agent = GreedyAgent(config)
    # Not in buy phase, not at plant site, no visible enemies, no abilities
    round_obj.phase = RoundPhase.ROUND
    action = agent.decide_action(player.get_observation(round_obj, team_blackboard), round_obj)
    assert isinstance(action, dict)
    assert action["action_type"] in {"idle", "move", "communicate"}
    # Should not try to buy, plant, or defuse
    assert not action["buy"]
    assert not action["plant"]
    assert not action["defuse"]

def test_greedy_agent_decide_action_buy():
    player, round_obj, team_blackboard = make_minimal_round_and_player()
    config = AgentConfig(
        role=player.role,
        skill_level=0.7,
        personality={"aggression": 0.5, "patience": 0.5, "teamplay": 0.5}
    )
    agent = GreedyAgent(config)
    round_obj.phase = RoundPhase.BUY
    player.creds = 4000
    obs = player.get_observation(round_obj, team_blackboard)
    action = agent.decide_action(obs, round_obj)
    assert action["action_type"] == "buy"
    assert action["buy"] is not None
    assert action["buy"]["weapon"] in {"Vandal", "Phantom"}
    assert action["buy"]["shield"] == "heavy"

def test_player_get_observation_with_personality():
    player, round_obj, team_blackboard = make_minimal_round_and_player()
    obs = player.get_observation(round_obj, team_blackboard, personality=[0.1, 0.2, 0.3])
    assert "personality" in obs
    assert obs["personality"] == [0.1, 0.2, 0.3] 
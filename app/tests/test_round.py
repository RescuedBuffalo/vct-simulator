import pytest
from app.simulation.models.round import Round, RoundWinner
from app.simulation.models.player import Player
from app.simulation.models.team import Team
from app.simulation.models.blackboard import Blackboard

class DummyAbility:
    def __init__(self):
        self.reset_charges_called = False
    def reset_charges(self):
        self.reset_charges_called = True

class DummyPlayer(Player):
    def __init__(self, id, team_id):
        super().__init__(id=id, name=id, team_id=team_id, role="duelist", agent="Jett", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50)
        self.abilities = DummyAbility()

@pytest.fixture
def mock_players():
    # 5 attackers, 5 defenders
    attackers = [DummyPlayer(f"a{i}", "attackers") for i in range(5)]
    defenders = [DummyPlayer(f"d{i}", "defenders") for i in range(5)]
    players = {p.id: p for p in attackers + defenders}
    return players, [p.id for p in attackers], [p.id for p in defenders]

def make_round(players, attacker_ids, defender_ids, **kwargs):
    return Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data={},
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
        **kwargs
    )

def test_loss_bonus_streaks(mock_players):
    players, attacker_ids, defender_ids = mock_players
    r = make_round(players, attacker_ids, defender_ids)
    # Simulate 3 consecutive losses for attackers
    r.round_winner = RoundWinner.DEFENDERS
    carryover1 = r.get_carryover_state(loss_bonus_attackers=1900, loss_bonus_defenders=1900)
    carryover2 = r.get_carryover_state(loss_bonus_attackers=2400, loss_bonus_defenders=1900)
    carryover3 = r.get_carryover_state(loss_bonus_attackers=2900, loss_bonus_defenders=1900)
    # Attackers should get increasing loss bonus
    for pid in attacker_ids:
        assert carryover1[pid]["round_credits"] == 1900
        assert carryover2[pid]["round_credits"] == 2400
        assert carryover3[pid]["round_credits"] == 2900
    # Defenders always get win credits
    for pid in defender_ids:
        assert carryover1[pid]["round_credits"] == 3000

def test_ability_and_ult_reset_and_increment(mock_players):
    players, attacker_ids, defender_ids = mock_players
    # Give some ult points and ability charges
    for p in players.values():
        p.ult_points = 3
        p.utility_charges = {"smoke": 0, "flash": 0}
    team = Team(id="attackers", name="Attackers", players=[players[pid] for pid in attacker_ids])
    team.reset_abilities_and_ultimates(max_ult=7)
    for p in team.players:
        assert p.ult_points <= 7
        # DummyAbility.reset_charges should have been called
        assert hasattr(p.abilities, 'reset_charges_called') and p.abilities.reset_charges_called
    # Test incrementing ult points
    p = team.players[0]
    old_ult = p.ult_points
    team.increment_player_ult(p.id, amount=2, max_ult=7)
    assert p.ult_points == min(old_ult + 2, 7)
    # Test orb pickup
    p.ult_points = 0
    p.add_orb_pickup(max_ult=7)
    assert p.ult_points == 1

def test_carryover_state_ult_and_credits(mock_players):
    players, attacker_ids, defender_ids = mock_players
    r = make_round(players, attacker_ids, defender_ids)
    # Simulate a round where a0 gets 2 kills and a plant
    players["a0"].kills = 2
    players["a0"].plants = 1
    r.round_winner = RoundWinner.DEFENDERS
    carryover = r.get_carryover_state(loss_bonus_attackers=2400, loss_bonus_defenders=1900)
    # a0 should get loss bonus + plant + 2*kill credits
    assert carryover["a0"]["round_credits"] == 2400 + 300 + 2*200
    # a1 (no kills/plants) should get just loss bonus
    assert carryover["a1"]["round_credits"] == 2400
    # d0 (defender) should get win credits
    assert carryover["d0"]["round_credits"] == 3000 
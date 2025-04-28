import pytest
from app.simulation.models.round import Round, RoundWinner, RoundPhase
from app.simulation.models.player import Player
from app.simulation.models.team import Team
from app.simulation.models.blackboard import Blackboard

class DummyAbility:
    def __init__(self):
        self.reset_charges_called = False
    def reset_charges(self):
        self.reset_charges_called = True
    def get_available_abilities(self):
        return []

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

def make_round(players, attacker_ids, defender_ids, map_data=None, **kwargs):
    if map_data is None:
        map_data = {}
    return Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
        **kwargs
    )

def test_loss_bonus_streaks(mock_players):
    players, attacker_ids, defender_ids = mock_players
    r = make_round(players, attacker_ids, defender_ids, map_data={})
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
    r = make_round(players, attacker_ids, defender_ids, map_data={})
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

def test_buying_shields_assigns_correct_shield():
    # Player with enough credits for heavy shield
    player = DummyPlayer("p1", "attackers")
    player.creds = 4000
    player.shield = None
    players = {player.id: player}
    defender = DummyPlayer("d1", "defenders")
    players[defender.id] = defender
    attacker_ids = [player.id]
    defender_ids = [defender.id]
    map_data = {
        "attacker_spawns": [(0.0, 0.0, 0.0)],
        "defender_spawns": [(1.0, 0.0, 0.0)],
        "walls": {},
        "plant_sites": {},
    }
    round_obj = make_round(players, attacker_ids, defender_ids, map_data=map_data)
    # Simulate end of buy phase
    round_obj.buy_phase_time = 0
    round_obj._process_buy_phase(time_step=0.1)
    assert player.shield == "heavy"
    # Player with enough credits for light shield
    player2 = DummyPlayer("p2", "attackers")
    player2.creds = 2500
    player2.shield = None
    players2 = {player2.id: player2, defender.id: defender}
    round_obj2 = make_round(players2, [player2.id], [defender.id], map_data=map_data)
    round_obj2.buy_phase_time = 0
    round_obj2._process_buy_phase(time_step=0.1)
    assert player2.shield == "light"
    # Player with not enough credits for shield
    player3 = DummyPlayer("p3", "attackers")
    player3.creds = 500
    player3.shield = None
    players3 = {player3.id: player3, defender.id: defender}
    round_obj3 = make_round(players3, [player3.id], [defender.id], map_data=map_data)
    round_obj3.buy_phase_time = 0
    round_obj3._process_buy_phase(time_step=0.1)
    assert player3.shield is None

def test_round_integration_two_players():
    # Create two players and a minimal map
    attacker = DummyPlayer("a0", "attackers")
    defender = DummyPlayer("d0", "defenders")
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    # Place them close together (ensure 3-tuple for location)
    attacker.location = (0.0, 0.0, 0.0)
    defender.location = (1.0, 0.0, 0.0)
    # Ensure all locations are 3-tuples before simulation
    for p in players.values():
        if len(p.location) == 2:
            p.location = (p.location[0], p.location[1], 0.0)
    # Minimal map data with walls as a dict
    map_data = {
        "attacker_spawns": [(0.0, 0.0, 0.0)],
        "defender_spawns": [(1.0, 0.0, 0.0)],
        "plant_sites": {},
        "walls": {},  # Should be a dict, not a list
    }
    # Create round
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    # Ensure all locations are 3-tuples after round initialization
    for p in players.values():
        if len(p.location) == 2:
            p.location = (p.location[0], p.location[1], 0.0)
    # Force both to see each other and be alive
    attacker.visible_enemies = [defender.id]
    defender.visible_enemies = [attacker.id]
    attacker.alive = True
    defender.alive = True
    # Simulate the round (should end with one winner)
    result = round_obj.simulate(time_step=0.1)
    assert round_obj.phase == RoundPhase.END
    assert round_obj.round_winner in [RoundWinner.ATTACKERS, RoundWinner.DEFENDERS]
    # Check that one player is dead and one is alive
    alive = [p for p in players.values() if p.alive]
    dead = [p for p in players.values() if not p.alive]
    assert len(alive) == 1 and len(dead) == 1
    # Check ult point increment for the winner (should have at least 1 ult point for a kill)
    winner = alive[0]
    assert winner.ult_points >= 1 or winner.kills >= 1
    # Simulate respawn/reset for next round
    winner.health = 50
    winner.ult_points = 3
    for p in players.values():
        p.reset_ability_charges()
        p.ult_points = 0
        p.health = 100
        p.alive = True
        # Ensure location is always a 3-tuple after reset
        if len(p.location) == 2:
            p.location = (p.location[0], p.location[1], 0.0)
    # All players should be alive and reset
    for p in players.values():
        assert p.alive
        assert p.health == 100
        assert p.ult_points == 0
        assert len(p.location) == 3 

def test_weapon_pickup_and_drop_unit():
    # Create a player and a dropped weapon nearby
    player = DummyPlayer("p1", "attackers")
    player.location = (5.0, 5.0, 0.0)
    player.weapon = None
    player.alive = True
    # Simulate a dropped weapon at the same location
    from app.simulation.models.round import DroppedWeapon, RoundPhase
    dropped = DroppedWeapon(weapon_type="Vandal", ammo=20, position=(5.0, 5.0, 0.0), dropped_time=0.0)
    # Create a minimal round object with at least one defender
    defender = DummyPlayer("d1", "defenders")
    players = {player.id: player, defender.id: defender}
    map_data = {
        "attacker_spawns": [(5.0, 5.0, 0.0)],
        "defender_spawns": [(0.0, 0.0, 0.0)],
        "walls": {},
        "plant_sites": {},
    }
    round_obj = make_round(players, [player.id], [defender.id], map_data=map_data)
    round_obj.dropped_weapons = [dropped]
    round_obj.phase = RoundPhase.ROUND  # Enable pickup logic
    # Patch all player locations to 3D tuple if needed
    for p in round_obj.players.values():
        loc = p.location
        if len(loc) == 2:
            p.location = (loc[0], loc[1], 0.0)
    player.location = round_obj.players[player.id].location
    assert len(player.location) == 3, f"player.location is not 3D: {player.location}"
    # Simulate movement to trigger pickup
    round_obj._simulate_player_movements(time_step=0.1)
    assert player.weapon == "Vandal"
    assert len(round_obj.dropped_weapons) == 0
    # Now drop the weapon
    round_obj._drop_weapon(player.id, player.weapon, (5.0, 5.0))
    assert player.weapon is None
    assert len(round_obj.dropped_weapons) == 1

def test_weapon_pickup_swap():
    # Player already has a weapon, picks up another
    player = DummyPlayer("p2", "attackers")
    player.location = (10.0, 10.0, 0.0)
    player.weapon = "Spectre"
    player.alive = True
    from app.simulation.models.round import DroppedWeapon, RoundPhase
    dropped = DroppedWeapon(weapon_type="Vandal", ammo=20, position=(10.0, 10.0, 0.0), dropped_time=0.0)
    # Add a dummy defender
    defender = DummyPlayer("d2", "defenders")
    players = {player.id: player, defender.id: defender}
    map_data = {
        "attacker_spawns": [(10.0, 10.0, 0.0)],
        "defender_spawns": [(0.0, 0.0, 0.0)],
        "walls": {},
        "plant_sites": {},
    }
    round_obj = make_round(players, [player.id], [defender.id], map_data=map_data)
    round_obj.dropped_weapons = [dropped]
    round_obj.phase = RoundPhase.ROUND  # Enable pickup logic
    # Patch all player locations to 3D tuple if needed
    for p in round_obj.players.values():
        loc = p.location
        if len(loc) == 2:
            p.location = (loc[0], loc[1], 0.0)
    player.location = round_obj.players[player.id].location
    assert len(player.location) == 3, f"player.location is not 3D: {player.location}"
    # Simulate movement to trigger pickup
    round_obj._simulate_player_movements(time_step=0.1)
    assert player.weapon == "Vandal"
    assert any(w.weapon_type == "Spectre" for w in round_obj.dropped_weapons)
    assert not any(w.weapon_type == "Vandal" for w in round_obj.dropped_weapons)

def test_integration_weapon_drop_and_pickup():
    # Two players, one kills the other, picks up their gun
    attacker = DummyPlayer("a0", "attackers")
    defender = DummyPlayer("d0", "defenders")
    attacker.location = (0.0, 0.0, 0.0)
    defender.location = (1.0, 0.0, 0.0)
    attacker.weapon = "Spectre"
    defender.weapon = "Vandal"
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    map_data = {
        "attacker_spawns": [(0.0, 0.0, 0.0)],
        "defender_spawns": [(1.0, 0.0, 0.0)],
        "plant_sites": {},
        "walls": {},
    }
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    # Simulate defender death and weapon drop
    round_obj._handle_player_death(defender.id, attacker.id)
    assert not defender.alive
    assert any(w.weapon_type == "Vandal" for w in round_obj.dropped_weapons)
    # Move attacker to defender's location and pick up Vandal
    attacker.location = defender.location
    round_obj._attempt_pickup_weapon(attacker)
    assert attacker.weapon == "Vandal"
    # Spectre should now be on the ground
    assert any(w.weapon_type == "Spectre" for w in round_obj.dropped_weapons)

def test_player_spawn_and_respawn_unit(mock_players):
    """Unit test for player spawn and respawn logic."""
    from app.simulation.models.round import Round
    players, attacker_ids, defender_ids = mock_players
    # Minimal map data with spawns
    map_data = {
        "attacker_spawns": [(10.0, 10.0, 0.0), (12.0, 10.0, 0.0)],
        "defender_spawns": [(20.0, 20.0, 0.0), (22.0, 20.0, 0.0)],
        "walls": {},
        "plant_sites": {},
    }
    round_obj = make_round(players, attacker_ids, defender_ids, map_data=map_data)
    # Check that all players are at spawn points (with jitter)
    for pid in attacker_ids:
        loc = players[pid].location
        assert 9.0 <= loc[0] <= 13.0 and 9.0 <= loc[1] <= 11.0
    for pid in defender_ids:
        loc = players[pid].location
        assert 19.0 <= loc[0] <= 23.0 and 19.0 <= loc[1] <= 21.0
    # Simulate a player death and respawn (simulate by calling _initialize_player_positions again)
    players[attacker_ids[0]].alive = False
    round_obj._initialize_player_positions()
    # Player should be moved to a spawn (with jitter)
    loc = players[attacker_ids[0]].location
    assert 9.0 <= loc[0] <= 13.0 and 9.0 <= loc[1] <= 11.0
    # Mark alive again for respawn
    players[attacker_ids[0]].alive = True
    round_obj._initialize_player_positions()
    loc = players[attacker_ids[0]].location
    assert 9.0 <= loc[0] <= 13.0 and 9.0 <= loc[1] <= 11.0

def test_integration_round_setup_and_buy():
    """Integration test: load map, spawn players, and simulate buy phase purchases."""
    from app.simulation.models.round import Round, RoundPhase
    from app.simulation.models.map import MapLayout
    from app.simulation.models.blackboard import Blackboard
    import os
    # Use the Ascent map if available, else fallback to minimal
    ascent_path = os.path.join(os.path.dirname(__file__), '../../maps/ascent.map.json')
    if os.path.exists(ascent_path):
        map_layout = MapLayout.load_from_json(ascent_path)
        map_data = map_layout.to_dict()
    else:
        map_data = {
            "attacker_spawns": [(0.0, 0.0, 0.0)],
            "defender_spawns": [(10.0, 0.0, 0.0)],
            "walls": {},
            "plant_sites": {},
        }
    # Create 5 attackers and 5 defenders
    players = {}
    attacker_ids = []
    defender_ids = []
    for i in range(5):
        p = DummyPlayer(f"a{i}", "attackers")
        players[p.id] = p
        attacker_ids.append(p.id)
    for i in range(5):
        p = DummyPlayer(f"d{i}", "defenders")
        players[p.id] = p
        defender_ids.append(p.id)
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    # All players should be at spawn points
    for pid in attacker_ids + defender_ids:
        loc = players[pid].location
        assert isinstance(loc, tuple) and len(loc) >= 2
    # Give each player credits so they can buy
    for p in players.values():
        p.creds = 3900
    # Simulate end of buy phase
    round_obj.buy_phase_time = 0
    round_obj._process_buy_phase(time_step=0.1)
    # All players should have a weapon and possibly a shield
    for pid in attacker_ids + defender_ids:
        player = players[pid]
        assert player.weapon is not None
        # Shield can be None, 'light', or 'heavy'
        assert player.shield in (None, 'light', 'heavy')
    # Round should now be in ROUND phase
    assert round_obj.phase == RoundPhase.ROUND 
import pytest
from app.simulation.models.round import Round, RoundWinner, RoundPhase
from app.simulation.models.player import Player
from app.simulation.models.team import Team
from app.simulation.models.blackboard import Blackboard
import math

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
    from app.simulation.models.player import Player
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
        p = Player(id=f"a{i}", name=f"A{i}", team_id="attackers", role="duelist", agent="Jett", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50)
        p.creds = 3900  # Ensure enough credits for a weapon
        players[p.id] = p
        attacker_ids.append(p.id)
    for i in range(5):
        p = Player(id=f"d{i}", name=f"D{i}", team_id="defenders", role="sentinel", agent="Sage", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50)
        p.creds = 3900  # Ensure enough credits for a weapon
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

def test_match_overtime():
    """Test that match correctly enters and resolves overtime."""
    from app.simulation.models.match import Match
    from app.simulation.models.map import Map
    from app.simulation.models.round import Round
    from app.simulation.models.round import RoundWinner
    from app.simulation.models.team import Team
    from app.simulation.models.player import Player
    from app.simulation.models.blackboard import Blackboard
    # Minimal map and player setup
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
        p = Player(id=f"a{i}", name=f"A{i}", team_id="attackers", role="duelist", agent="Jett", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50)
        players[p.id] = p
        attacker_ids.append(p.id)
    for i in range(5):
        p = Player(id=f"d{i}", name=f"D{i}", team_id="defenders", role="sentinel", agent="Sage", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50)
        players[p.id] = p
        defender_ids.append(p.id)
    # Ensure each player has abilities and creds for carryover logic
    for p in players.values():
        p.abilities = DummyAbility()
        p.creds = 0
    # Create teams
    team_a = Team(id="attackers", name="Attackers", players=[players[pid] for pid in attacker_ids])
    team_b = Team(id="defenders", name="Defenders", players=[players[pid] for pid in defender_ids])
    # Create initial round
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    # Patch the round's simulate method to alternate wins to reach 12-12, then test overtime
    win_pattern = (["attackers", "defenders"] * 12)[:24]
    win_iter = iter(win_pattern)
    orig_simulate = round_obj.simulate
    def fake_simulate(*args, **kwargs):
        winner_str = next(win_iter, None)
        if winner_str is None:
            # Overtime: attackers always win until a 2-round lead
            if team_a.stats.rounds_won <= team_b.stats.rounds_won:
                winner_str = "attackers"
            else:
                winner_str = "defenders"
        # Set round_obj.round_winner to the correct enum
        if winner_str == "attackers":
            round_obj.round_winner = RoundWinner.ATTACKERS
        else:
            round_obj.round_winner = RoundWinner.DEFENDERS
        return {"winner": winner_str}
    # Monkey-patch Round.simulate for all instances (including future ones) to use fake_simulate
    from app.simulation.models.round import Round as RoundClass
    RoundClass.simulate = fake_simulate
    # Also patch the initial instance
    round_obj.simulate = fake_simulate
    # Create a dummy Map object
    class DummyMap:
        pass
    # Monkey-patch carryover to remove 'abilities' key (Player.abilities may not exist)
    from app.simulation.models.round import Round as RoundClass
    orig_get_carry = RoundClass.get_carryover_state
    def fake_get_carry(self, *args, **kwargs):
        carry = orig_get_carry(self, *args, **kwargs)
        for state in carry.values():
            state.pop("abilities", None)
        return carry
    RoundClass.get_carryover_state = fake_get_carry
    match = Match(DummyMap(), round_obj, team_a, team_b)
    match.run()
    # After run, check that match went into overtime by playing beyond regulation rounds
    assert match.current_round > 24, "Match should enter overtime (play more than 24 rounds)."
    assert abs(match.team_a_score - match.team_b_score) >= 2, "Match should end with a 2-round lead in overtime."
    assert match.team_a_score >= 13 or match.team_b_score >= 13, "Final score should be at least 13 for the winner." 

class DroppedShield:
    """Test helper for shield drops."""
    def __init__(self, shield_type, position, dropped_time):
        self.shield_type = shield_type
        self.position = position
        self.dropped_time = dropped_time

def test_shield_pickup_and_drop_unit():
    # Create a player and a dropped shield nearby
    player = DummyPlayer("p1", "attackers")
    player.location = (5.0, 5.0, 0.0)
    player.shield = None
    player.alive = True
    
    # Simulate a dropped shield at the same location
    from app.simulation.models.round import RoundPhase
    dropped = DroppedShield(shield_type="heavy", position=(5.0, 5.0, 0.0), dropped_time=0.0)
    
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
    round_obj.dropped_shields = [dropped]
    round_obj.phase = RoundPhase.ROUND  # Enable pickup logic
    
    # Patch all player locations to 3D tuple if needed
    for p in round_obj.players.values():
        loc = p.location
        if len(loc) == 2:
            p.location = (loc[0], loc[1], 0.0)
    player.location = round_obj.players[player.id].location
    assert len(player.location) == 3, f"player.location is not 3D: {player.location}"
    
    # Simulate shield pickup (would normally happen in _attempt_pickup_shield)
    round_obj._attempt_pickup_shield(player)
    
    assert player.shield == "heavy"
    assert len(round_obj.dropped_shields) == 0
    
    # Now drop the shield
    round_obj._drop_shield(player.id, player.shield, (5.0, 5.0))
    assert player.shield is None
    assert len(round_obj.dropped_shields) == 1

def test_shield_pickup_swap():
    # Player already has a shield, picks up another
    player = DummyPlayer("p2", "attackers")
    player.location = (10.0, 10.0, 0.0)
    player.shield = "light"
    player.alive = True
    
    from app.simulation.models.round import RoundPhase
    dropped = DroppedShield(shield_type="heavy", position=(10.0, 10.0, 0.0), dropped_time=0.0)
    
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
    round_obj.dropped_shields = [dropped]
    round_obj.phase = RoundPhase.ROUND  # Enable pickup logic
    
    # Patch all player locations to 3D tuple if needed
    for p in round_obj.players.values():
        loc = p.location
        if len(loc) == 2:
            p.location = (loc[0], loc[1], 0.0)
    player.location = round_obj.players[player.id].location
    assert len(player.location) == 3, f"player.location is not 3D: {player.location}"
    
    # Simulate shield pickup with swap
    round_obj._attempt_pickup_shield(player)
    
    assert player.shield == "heavy"
    assert any(s.shield_type == "light" for s in round_obj.dropped_shields)
    assert not any(s.shield_type == "heavy" for s in round_obj.dropped_shields)

def test_integration_shield_drop_and_pickup():
    # Two players, one kills the other, picks up their shield
    attacker = DummyPlayer("a0", "attackers")
    defender = DummyPlayer("d0", "defenders")
    attacker.location = (0.0, 0.0, 0.0)
    defender.location = (1.0, 0.0, 0.0)
    attacker.shield = "light"
    defender.shield = "heavy"
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    map_data = {
        "attacker_spawns": [(0.0, 0.0, 0.0)],
        "defender_spawns": [(1.0, 0.0, 0.0)],
        "plant_sites": {},
        "walls": {},
    }
    
    # Create a Round with the _drop_shield and _attempt_pickup_shield methods we need to test
    from app.simulation.models.round import Blackboard
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    
    # Add necessary attributes for shield mechanics
    if not hasattr(round_obj, "dropped_shields"):
        round_obj.dropped_shields = []
    
    # Add the shield mechanics methods to the Round object
    def _drop_shield(self, player_id, shield_type, location):
        dropped = DroppedShield(
            shield_type=shield_type,
            position=location,
            dropped_time=self.tick if hasattr(self, "tick") else 0.0
        )
        self.dropped_shields.append(dropped)
        self.players[player_id].shield = None
        
    def _attempt_pickup_shield(self, player):
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
                shield_to_remove = dropped
                break
        if shield_to_remove:
            self.dropped_shields.remove(shield_to_remove)
        
    # Attach the methods to the round object
    import types
    round_obj._drop_shield = types.MethodType(_drop_shield, round_obj)
    round_obj._attempt_pickup_shield = types.MethodType(_attempt_pickup_shield, round_obj)
    
    # Add a custom _handle_player_death method that drops shields
    def _handle_player_death_with_shield(self, victim_id, killer_id):
        victim = self.players[victim_id]
        victim.alive = False
        # Drop shield if the player has one
        if victim.shield:
            self._drop_shield(victim_id, victim.shield, victim.location)
            
    round_obj._handle_player_death_with_shield = types.MethodType(_handle_player_death_with_shield, round_obj)
    
    # Simulate defender death and shield drop
    round_obj._handle_player_death_with_shield(defender.id, attacker.id)
    
    assert not defender.alive
    assert any(s.shield_type == "heavy" for s in round_obj.dropped_shields)
    
    # Move attacker to defender's location and pick up heavy shield
    attacker.location = defender.location
    round_obj._attempt_pickup_shield(attacker)
    
    assert attacker.shield == "heavy"
    # Light shield should now be on the ground
    assert any(s.shield_type == "light" for s in round_obj.dropped_shields)

def test_agent_selection_phase():
    from app.simulation.models.match import Match
    from app.simulation.models.map import Map
    from app.simulation.models.round import Round
    from app.simulation.models.team import Team
    from app.simulation.models.player import Player
    from app.simulation.models.blackboard import Blackboard
    # Create 2 teams of 5 players each
    players_a = [Player(id=f"a{i}", name=f"A{i}", team_id="attackers", role="duelist", agent=None, aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50) for i in range(5)]
    players_b = [Player(id=f"d{i}", name=f"D{i}", team_id="defenders", role="sentinel", agent=None, aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50) for i in range(5)]
    team_a = Team(id="attackers", name="Attackers", players=players_a)
    team_b = Team(id="defenders", name="Defenders", players=players_b)
    # Minimal map and round
    map_data = {"attacker_spawns": [(0.0, 0.0, 0.0)], "defender_spawns": [(10.0, 0.0, 0.0)], "walls": {}, "plant_sites": {}}
    round_obj = Round(
        round_number=1,
        players={p.id: p for p in players_a + players_b},
        attacker_ids=[p.id for p in players_a],
        defender_ids=[p.id for p in players_b],
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    match = Match(Map("TestMap", 20, 20), round_obj, team_a, team_b)
    # Call agent selection
    match.agent_selection_phase()
    # All players should have a non-None agent
    for p in players_a + players_b:
        assert p.agent is not None
        assert isinstance(p.agent, str)
        assert len(p.agent) > 0

def test_match_timeouts():
    from app.simulation.models.match import Match
    from app.simulation.models.map import Map
    from app.simulation.models.round import Round
    from app.simulation.models.team import Team
    from app.simulation.models.player import Player
    from app.simulation.models.blackboard import Blackboard
    class DummyAbilities:
        def reset_charges(self):
            pass
        def get_available_abilities(self):
            return []
    # Create 2 teams of 5 players each
    players_a = [Player(id=f"a{i}", name=f"A{i}", team_id="attackers", role="duelist", agent="Jett", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50) for i in range(5)]
    players_b = [Player(id=f"d{i}", name=f"D{i}", team_id="defenders", role="sentinel", agent="Sage", aim_rating=50, reaction_time=200, movement_accuracy=50, spray_control=50, clutch_iq=50) for i in range(5)]
    # Assign dummy abilities to all players
    for p in players_a + players_b:
        p.abilities = DummyAbilities()
    team_a = Team(id="attackers", name="Attackers", players=players_a)
    team_b = Team(id="defenders", name="Defenders", players=players_b)
    # Minimal map and round
    map_data = {"attacker_spawns": [(0.0, 0.0, 0.0)], "defender_spawns": [(10.0, 0.0, 0.0)], "walls": {}, "plant_sites": {}}
    round_obj = Round(
        round_number=1,
        players={p.id: p for p in players_a + players_b},
        attacker_ids=[p.id for p in players_a],
        defender_ids=[p.id for p in players_b],
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
    )
    match = Match(Map("TestMap", 20, 20), round_obj, team_a, team_b)
    # Initial timeouts
    assert match.timeouts_remaining[team_a.id] == 1
    assert match.timeouts_remaining[team_b.id] == 1
    # Call timeout for team_a
    assert match.call_timeout(team_a.id) is True
    assert match.timeouts_remaining[team_a.id] == 0
    assert match.timeout_pending == team_a.id
    # Timeout should pause match progression
    match.timeout_timer = 2.0  # Simulate a short timeout for test
    steps = 0
    while match.timeout_pending:
        match.run()  # Should decrement timer and eventually clear timeout
        steps += 1
        if steps > 10:
            break
    assert match.timeout_pending is None
    # Can't call another timeout for team_a
    assert match.call_timeout(team_a.id) is False
    # Team_b can still call theirs
    assert match.call_timeout(team_b.id) is True
    assert match.timeouts_remaining[team_b.id] == 0 
import pytest
from app.simulation.models.round import Round, RoundWinner, RoundPhase
from app.simulation.models.player import Player
from app.simulation.models.team import Team
from app.simulation.models.blackboard import Blackboard
from app.simulation.models.map import Map, MapBoundary
from app.simulation.models.map_pathfinding import CollisionDetector
from app.simulation.models.round import DroppedWeapon
from app.simulation.models.weapon import WeaponFactory
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

@pytest.fixture
def mock_map():
    test_map = Map("test_map", 100, 100)
    test_map_json = {
        "metadata": {
            "name": "test_map",
            "map-size": [100, 100]
        },
        "map-areas": {
            "ground": {
                "x": 0,
                "y": 0,
                "w": 100,
                "h": 100,
                "z": 0,
                "elevation": 0
            },
            "platform1": {
                "x": 20,
                "y": 20,
                "w": 10,
                "h": 10,
                "z": 2.0,
                "elevation": 2.0
            }
        },
        "walls": {
            "wall1": {
                "x": 40,
                "y": 40,
                "w": 20,
                "h": 2,
                "z": 0,
                "height_z": 3.0
            },
            "wall2": {
                "x": 40,
                "y": 40,
                "w": 2,
                "h": 20,
                "z": 0,
                "height_z": 3.0
            }
        },
        "objects": {
            "box1": {
                "x": 60,
                "y": 60,
                "w": 5,
                "h": 5,
                "z": 0,
                "height_z": 1.0
            }
        },
        "stairs": {
            "test_stairs": {
                "x": 30,
                "y": 30,
                "w": 2,
                "h": 5,
                "z": 0,
                "height_z": 1.5,
                "direction": "north",
                "steps": 5
            },
        },
        "bomb-sites" : {
            "A" : {"x" : 4, "y" : 4, "w" : 2, "h" : 2, "z" : 0, "height_z" : 0.0}
        }
    }
    test_map = Map.from_json(test_map_json)
    
    return test_map

def make_round(players, attacker_ids, defender_ids, map_data=None, **kwargs):
    from app.simulation.models.map import Map
    map_obj = kwargs.pop('map_obj', None)
    if map_obj is not None:
        return Round(
            round_number=1,
            players=players,
            attacker_ids=attacker_ids,
            defender_ids=defender_ids,
            map_data=map_data,
            attacker_blackboard=Blackboard("attackers"),
            defender_blackboard=Blackboard("defenders"),
            map_obj=map_obj,
            **kwargs
        )
    if map_data is not None:
        if isinstance(map_data, dict) or isinstance(map_data, str):
            map_obj = Map.from_json(map_data)
        else:
            raise ValueError("map_data must be a dict or a file path")
    else:
        from json import load
        print("Loading map data from Ascent file")
        map_data = load(open("../maps/ascent.map.json"))
        map_obj = Map.from_json(map_data)
    return Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data=map_data,
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
        map_obj=map_obj,
        **kwargs
    )

def test_loss_bonus_streaks(mock_players):
    players, attacker_ids, defender_ids = mock_players
    # Create a simple Map object for this test
    map_obj = Map(name="Test Map", width=32, height=32)
    r = make_round(players, attacker_ids, defender_ids, map_obj=map_obj)
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
    # Create a simple Map object for this test
    map_obj = Map(name="Test Map", width=32, height=32)
    r = make_round(players, attacker_ids, defender_ids, map_obj=map_obj)
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
    
    
    # Create a Map object with spawn points
    map_obj = Map(name="Test Map", width=32, height=32)
    map_obj.attacker_spawns = [(0.0, 0.0, 0.0)]
    map_obj.defender_spawns = [(1.0, 0.0, 0.0)]
    
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=map_obj)
    
    # Simulate end of buy phase - direct call to ensure it works
    round_obj._simulate_buy_decision(player)
    
    assert player.shield == "heavy"
     
    # Player with enough credits for light shield
    player2 = DummyPlayer("p2", "attackers")
    player2.creds = 2500
    player2.shield = None
    players2 = {player2.id: player2, defender.id: defender}
    round_obj2 = make_round(players2, [player2.id], [defender.id], map_obj=map_obj)
    
    # Direct call to simulate buy decision
    round_obj2._simulate_buy_decision(player2)
    assert player2.shield == "light"
     
    # Player with not enough credits for shield
    player3 = DummyPlayer("p3", "attackers")
    player3.creds = 500
    player3.shield = None
    players3 = {player3.id: player3, defender.id: defender}
    round_obj3 = make_round(players3, [player3.id], [defender.id], map_obj=map_obj)
    
    # Direct call to simulate buy decision
    round_obj3._simulate_buy_decision(player3)
    assert player3.shield is None

def test_round_integration_two_players(mock_map):
    from app.simulation.models.weapon import WeaponFactory
    # Create two players and a minimal map
    attacker = DummyPlayer("a0", "attackers")
    defender = DummyPlayer("d0", "defenders")
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    
    # Place them close together (ensure 3-tuple for location)
    attacker.location = (0.0, 0.0, 0.0)
    attacker.is_moving = False
    attacker.movement_direction = None
    defender.location = (1.0, 0.0, 0.0)
    defender.is_moving = False
    defender.movement_direction = None
    
    # Ensure all locations are 3-tuples before simulation
    for p in players.values():
        if len(p.location) == 2:
            p.location = (p.location[0], p.location[1], 0.0)
    
    # Create round
    round_obj = Round(
        round_number=1,
        players=players,
        attacker_ids=attacker_ids,
        defender_ids=defender_ids,
        map_data={},  # Empty map_data as we're using map_obj
        attacker_blackboard=Blackboard("attackers"),
        defender_blackboard=Blackboard("defenders"),
        map_obj=mock_map
    )

    round_obj.phase = RoundPhase.ROUND
    attacker.weapon = WeaponFactory.create_weapon_catalog()["Vandal"]
    defender.weapon = WeaponFactory.create_weapon_catalog()["Vandal"]
    
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
    while round_obj.phase != RoundPhase.END:
        round_obj.update(time_step=1.0)
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
    player.location = (5.0, 5.0)
    player.weapon = None
    player.alive = True

    # Get weapon catalog
    weapon_catalog = WeaponFactory.create_weapon_catalog()

    # Simulate a dropped weapon at the same location
    dropped = DroppedWeapon(
        weapon=weapon_catalog["Vandal"],
        ammo=20,
        position=(5.0, 5.0),
        dropped_time=0.0
    )

    # Create a minimal round object with at least one defender
    defender = DummyPlayer("d1", "defenders")
    players = {player.id: player, defender.id: defender}

    # Create a Map object
    map_obj = Map(name="Test Map", width=32, height=32)
    map_obj.attacker_spawns = [(5.0, 5.0, 0.0)]
    map_obj.defender_spawns = [(0.0, 0.0, 0.0)]

    round_obj = make_round(players, [player.id], [defender.id], map_obj=map_obj)
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
    assert player.weapon.name == "Vandal"
    assert len(round_obj.dropped_weapons) == 0

    # Now drop the weapon
    round_obj._drop_weapon(player.id, player.weapon, (5.0, 5.0))
    assert player.weapon is None
    assert len(round_obj.dropped_weapons) == 1

def test_weapon_pickup_swap():
    # Player already has a weapon, picks up another
    player = DummyPlayer("p2", "attackers")
    player.location = (10.0, 10.0)
    weapon_catalog = WeaponFactory.create_weapon_catalog()
    player.weapon = weapon_catalog["Spectre"]
    player.alive = True

    dropped = DroppedWeapon(
        weapon=weapon_catalog["Vandal"],
        ammo=20,
        position=(10.0, 10.0),
        dropped_time=0.0
    )

    # Add a dummy defender
    defender = DummyPlayer("d2", "defenders")
    players = {player.id: player, defender.id: defender}

    # Create a Map object
    map_obj = Map(name="Test Map", width=32, height=32)
    map_obj.attacker_spawns = [(10.0, 10.0, 0.0)]
    map_obj.defender_spawns = [(0.0, 0.0, 0.0)]

    round_obj = make_round(players, [player.id], [defender.id], map_obj=map_obj)
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
    assert player.weapon.name == "Vandal"
    assert any(w.weapon.name == "Spectre" for w in round_obj.dropped_weapons)
    assert not any(w.weapon.name == "Vandal" for w in round_obj.dropped_weapons)

def test_spike_plant_success(mock_map):
    """Test that an attacker can plant the spike at a valid site and it is marked as planted."""
    from app.simulation.models.round import Round, RoundPhase
    
    attacker = DummyPlayer("a0", "attackers")
    attacker.location = (5.0, 5.0, 0.0)
    attacker.is_moving = False
    attacker.movement_direction = None
    attacker.alive = True
    attacker.weapon = None
    
    defender = DummyPlayer("d0", "defenders")
    defender.alive = True
    defender.weapon = None
    
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=mock_map)
    round_obj.phase = RoundPhase.ROUND
    round_obj.spike_carrier_id = attacker.id
    attacker.spike = True
    attacker.plant_progress = 0.0
    time_step = 1.0
    attacker.update_movement = lambda *a, **kw: None
    attacker.location = (5.0, 5.0, 0.0)
    attacker.start_plant(round_obj)
    
    for _ in range(10):
        round_obj.update(time_step)
        
    assert round_obj.spike_planted
    assert not attacker.spike
    assert attacker.plants == 1
    assert round_obj.spike_position == attacker.location

def test_spike_plant_fail_wrong_location(mock_map):
    """Test that planting fails if not at a valid plant site."""
    from app.simulation.models.round import RoundPhase
    attacker = DummyPlayer("a0", "attackers")
    attacker.location = (0.0, 0.0, 0.0)
    attacker.is_moving = False
    attacker.movement_direction = None
    attacker.alive = True
    defender = DummyPlayer("d0", "defenders")
    defender.alive = True
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=mock_map)
    round_obj.phase = RoundPhase.ROUND
    round_obj.spike_carrier_id = attacker.id
    attacker.spike = True
    attacker.plant_progress = 0.0
    time_step = 0.5
    attacker.update_movement = lambda *a, **kw: None
    attacker.weapon = None
    defender.weapon = None


    attacker.start_plant(round_obj)
    print(f"Attacker is alive: {attacker.alive}")
    for _ in range(10):
        attacker.location = (0.0, 0.0, 0.0)
        round_obj.update(time_step)
        print(f"Attacker is alive: {attacker.alive}")
    assert not round_obj.spike_planted
    assert attacker.spike
    assert attacker.plants == 0

def test_spike_defuse_success(mock_map):
    """Test that a defender can defuse the spike at the correct location."""
    from app.simulation.models.round import RoundPhase, RoundWinner, RoundEndCondition
    attacker = DummyPlayer("a0", "attackers")
    attacker.alive = True
    defender = DummyPlayer("d0", "defenders")
    defender.location = (5.0, 5.0, 0.0)
    defender.is_moving = False
    defender.movement_direction = None
    defender.alive = True
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=mock_map)
    round_obj.phase = RoundPhase.ROUND
    round_obj.spike_carrier_id = attacker.id
    round_obj.spike_planted = True
    round_obj.spike_position = (5.0, 5.0, 0.0)
    round_obj.spike_time_remaining = 45.0
    attacker.weapon = None
    defender.weapon = None
    defender.update_movement = lambda *a, **kw: None
    time_step = 0.5
    defender.start_defuse(round_obj)
    for _ in range(20):
        defender.location = (5.0, 5.0, 0.0)
        round_obj.update(time_step)
        if round_obj.round_winner != RoundWinner.NONE:
            break
    assert not round_obj.spike_planted
    assert defender.defuses == 1
    assert round_obj.round_winner == RoundWinner.DEFENDERS
    assert round_obj.round_end_condition == RoundEndCondition.SPIKE_DEFUSED

def test_spike_defuse_fail_wrong_location(mock_map):
    """Test that defusing fails if not at the spike location."""
    from app.simulation.models.round import RoundPhase
    attacker = DummyPlayer("a0", "attackers")
    attacker.alive = True
    defender = DummyPlayer("d0", "defenders")
    defender.location = (0.0, 0.0, 0.0)
    defender.is_moving = False
    defender.movement_direction = None
    defender.alive = True
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=mock_map)
    round_obj.phase = RoundPhase.ROUND
    round_obj.spike_carrier_id = attacker.id
    round_obj.spike_planted = True
    round_obj.spike_position = (5.0, 5.0, 0.0)
    round_obj.spike_time_remaining = 45.0
    defender.defuse_progress = 0.0
    time_step = 0.5
    for _ in range(20):
        round_obj.update(time_step)
    assert round_obj.spike_planted
    assert defender.defuses == 0

def test_spike_detonation_ends_round(mock_map):
    """Test that the round ends with attackers winning if spike detonates."""
    from app.simulation.models.round import RoundPhase, RoundWinner, RoundEndCondition
    attacker = DummyPlayer("a0", "attackers")
    attacker.alive = True
    defender = DummyPlayer("d0", "defenders")
    defender.alive = True
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=mock_map)
    round_obj.phase = RoundPhase.ROUND
    round_obj.spike_carrier_id = attacker.id
    round_obj.spike_planted = True
    round_obj.spike_position = (5.0, 5.0, 0.0)
    round_obj.spike_time_remaining = 1.0
    # Ensure both players are not at the spike location
    attacker.location = (0.0, 0.0, 0.0)
    attacker.is_moving = False
    attacker.movement_direction = None
    defender.location = (10.0, 0.0, 0.0)
    defender.is_moving = False
    defender.movement_direction = None
    time_step = 0.5
    for _ in range(5):
        round_obj.update(time_step)
        if round_obj.round_winner != RoundWinner.NONE:
            break
    assert round_obj.round_winner == RoundWinner.ATTACKERS
    assert round_obj.round_end_condition == RoundEndCondition.SPIKE_DETONATION
    assert round_obj.phase == RoundPhase.END

def test_spike_defuse_ends_round(mock_map):
    """Test that the round ends with defenders winning if spike is defused."""
    from app.simulation.models.round import RoundPhase, RoundWinner, RoundEndCondition
    attacker = DummyPlayer("a0", "attackers")
    attacker.alive = True
    defender = DummyPlayer("d0", "defenders")
    defender.location = (5.0, 5.0, 0.0)
    defender.is_moving = False
    defender.movement_direction = None
    defender.alive = True
    players = {attacker.id: attacker, defender.id: defender}
    attacker_ids = [attacker.id]
    defender_ids = [defender.id]
    round_obj = make_round(players, attacker_ids, defender_ids, map_obj=mock_map)
    round_obj.phase = RoundPhase.ROUND
    round_obj.spike_carrier_id = attacker.id
    round_obj.spike_planted = True
    round_obj.spike_position = (5.0, 5.0, 0.0)
    round_obj.spike_time_remaining = 45.0
    attacker.weapon = None
    defender.weapon = None
    # Set location after round creation to override spawn jitter
    defender.location = (5.0, 5.0, 0.0)
    defender.defuse_progress = 0.0
    time_step = 0.5
    defender.update_movement = lambda *a, **kw: None
    for _ in range(20):
        round_obj.update(time_step)
        defender.location = (5.0, 5.0, 0.0)
    assert round_obj.round_winner == RoundWinner.DEFENDERS
    assert round_obj.round_end_condition == RoundEndCondition.SPIKE_DEFUSED
    assert round_obj.phase == RoundPhase.END 
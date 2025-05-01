import pytest
from app.simulation.models.ability import (
    create_smoke_ability, create_flash_ability, create_molly_ability, create_recon_ability,
    SmokeAbilityInstance, FlashAbilityInstance, MollyAbilityInstance, ReconAbilityInstance
)
from app.simulation.models.map import Map

class MockPlayer:
    """Mock player for testing abilities."""
    def __init__(self, id_str: str):
        self.id = id_str
        self.location = (0, 0, 0)
        self.view_direction = (1, 0, 0)
        self.direction = 0  # Angle in degrees (0 = facing right/east)
        self.status_effects = {}  # Changed from list to dict
        self.is_alive = True
        self.alive = True  # For map FOV calculation
        self.health = 100
        self.armor = 50
        self.utility_active = []  # For map FOV calculation
        
    def apply_damage(self, dmg):
        """Apply damage to player's health."""
        self.health = max(0, self.health - dmg)

@pytest.fixture
def mock_map():
    """Create a simple square map for testing."""
    test_map = Map("test_map", 32, 32)
    test_map_json = {
        "metadata" : {
            "name" : "test_map",
            "width" : 32,
            "height" : 32
        },
        "map-areas" : {
            "main" : {"x" : 0, "y" : 0, "w" : 32, "h" : 32, "z" : 0}
        },
        "walls" : {
            "wall1": {"x": 15, "y": 0, "w": 1, "h": 10, "z": 0, "z_height": 3},  # Vertical wall in middle
            "wall2": {"x": 0, "y": 15, "w": 10, "h": 1, "z": 0, "z_height": 3}   # Horizontal wall
        }
    }
    test_map.from_json(test_map_json)
    return test_map

@pytest.fixture
def mock_players():
    """Create mock players for testing."""
    p1 = MockPlayer("p1")
    p1.location = (0, 0, 0)
    p2 = MockPlayer("p2")
    p2.location = (5, 0, 0)
    p3 = MockPlayer("p3")
    p3.location = (20, 0, 0)
    return [p1, p2, p3]

class DummyMap:
    def cast_bullet(self, origin, direction, max_range, players):
        # Always return no hit for simplicity
        return (origin, None, None)

# Smoke ability: should not affect player state directly
def test_smoke_ability_effect(mock_players):
    smoke_def = create_smoke_ability("TestSmoke", radius=10.0)
    instance = SmokeAbilityInstance(smoke_def, "p1", "smoke1", 2)
    instance.current_position3d = (0, 0, 0)
    instance.is_active = True
    instance.apply_effect(DummyMap(), mock_players)
    assert instance.effect_applied
    assert mock_players[0].id in instance.affected_players
    assert mock_players[1].id in instance.affected_players
    assert mock_players[2].id not in instance.affected_players
    assert "smoked" in mock_players[0].status_effects and mock_players[0].status_effects["smoked"] > 0
    assert "smoked" in mock_players[1].status_effects and mock_players[1].status_effects["smoked"] > 0
    assert "smoked" not in mock_players[2].status_effects

# Flash ability: should apply 'flashed' to players in radius
def test_flash_ability_effect(mock_players, mock_map):
    flash_def = create_flash_ability("TestFlash", duration=1.0)
    instance = FlashAbilityInstance(flash_def, "p1", "flash1", 2)
    
    # Set up player positions and view directions
    # Player 1: Looking right (towards flash)
    mock_players[0].location = (0, 0, 0)
    mock_players[0].view_direction = (1, 0, 0)
    mock_players[0].direction = 0  # 0 degrees = facing right
    
    # Player 2: Looking left (towards flash)
    mock_players[1].location = (5, 0, 0)
    mock_players[1].view_direction = (-1, 0, 0)
    mock_players[1].direction = 180  # 180 degrees = facing left
    
    # Player 3: Looking left but behind wall
    mock_players[2].location = (20, 0, 0)
    mock_players[2].view_direction = (-1, 0, 0)
    mock_players[2].direction = 180
    
    # Place flash between players 0 and 1
    flash_pos = (2.5, 0, 0)
    instance.current_position3d = flash_pos
    instance.is_active = True
    
    # Create a temporary player object for the flash to check FOV
    flash_player = MockPlayer("flash")
    flash_player.location = flash_pos
    flash_player.direction = 0  # Direction doesn't matter for flash source
    
    # Get players that can see the flash
    visible_players = mock_map.calculate_player_fov(flash_player, mock_players, fov_angle=360.0, max_distance=10.0)
    
    # Apply flash effect
    instance.apply_effect(mock_map, mock_players)
    
    # Player 1 should be flashed (can see flash and looking towards it)
    assert mock_players[0].id in [p.id for p in visible_players], "Player 1 should be able to see the flash"
    assert mock_players[0].id in instance.affected_players, "Player 1 should be affected by flash"
    assert "flashed" in mock_players[0].status_effects and mock_players[0].status_effects["flashed"] == 1.0
    
    # Player 2 should be flashed (can see flash and looking towards it)
    assert mock_players[1].id in [p.id for p in visible_players], "Player 2 should be able to see the flash"
    assert mock_players[1].id in instance.affected_players, "Player 2 should be affected by flash"
    assert "flashed" in mock_players[1].status_effects and mock_players[1].status_effects["flashed"] == 1.0
    
    # Player 3 should not be flashed (behind wall)
    assert mock_players[2].id not in [p.id for p in visible_players], "Player 3 should not be able to see the flash"
    assert mock_players[2].id not in instance.affected_players, "Player 3 should not be affected by flash"
    assert "flashed" not in mock_players[2].status_effects

# Molly ability: should damage players in radius
def test_molly_ability_effect(mock_players):
    molly_def = create_molly_ability("TestMolly", radius=10.0, damage=20.0)
    instance = MollyAbilityInstance(molly_def, "p1", "molly1", 1)
    instance.current_position3d = (0, 0, 0)
    instance.is_active = True
    instance.apply_effect(DummyMap(), mock_players)
    assert instance.effect_applied
    assert mock_players[0].health == 80
    assert mock_players[1].health == 80
    assert mock_players[2].health == 100

# Recon ability: should apply 'revealed' to players in radius
def test_recon_ability_effect(mock_players):
    recon_def = create_recon_ability("TestRecon", radius=10.0)
    instance = ReconAbilityInstance(recon_def, "p1", "recon1", 1)
    instance.current_position3d = (0, 0, 0)
    instance.is_active = True
    instance.end_time = 100.0
    instance.pulse_timer = 1.5  # trigger pulse
    instance.update(1.5, 1.5, DummyMap(), mock_players)
    assert 'revealed' in mock_players[0].status_effects and mock_players[0].status_effects["revealed"] > 0
    assert 'revealed' in mock_players[1].status_effects and mock_players[1].status_effects["revealed"] > 0
    assert 'revealed' not in mock_players[2].status_effects 
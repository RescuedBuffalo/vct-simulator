import pytest
import math
from app.simulation.models.ability import (
    AbilityType, AbilityDefinition, AbilityTarget,
    STANDARD_ABILITIES, MollyAbilityInstance
)
from app.simulation.models.map import Map
class MockPlayer:
    """Mock player for testing abilities."""
    def __init__(self, id_str: str):
        self.id = id_str
        self.location = (0, 0, 0)
        self.view_direction = (1, 0, 0)
        self.status_effects = {}  # Changed from list to dict
        self.is_alive = True  # Add is_alive attribute
        self.health = 100
        self.armor = 50
        self.shield = True
        self.alive = True
        self.direction = 0  # Added direction attribute

    def apply_damage(self, dmg: int):
        """Apply damage to player's health and armor."""
        # Armor absorbs 66% of damage
        if self.armor > 0:
            armor_damage = min(self.armor, int(dmg * 0.5))
            self.armor = max(0, self.armor - armor_damage)
            dmg = max(0, dmg - armor_damage)
        self.health = max(0, self.health - dmg)




@pytest.fixture
def mock_map():
    return MockMap()

@pytest.fixture
def mock_players():
    return [
        MockPlayer("player1"),  # Looking right
        MockPlayer("player2"),  # Looking left
        MockPlayer("player3"),  # Looking down
    ]

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
        }
    }
    test_map.from_json(test_map_json)
    return test_map

def test_ability_definition_initialization():
    """Test ability definition initialization and defaults."""
    flash = STANDARD_ABILITIES["flash"]
    assert flash.ability_type == AbilityType.FLASH
    assert flash.max_charges == 2
    assert flash.credit_cost == 200
    assert flash.duration == 1.5
    assert flash.effect_radius == 10.0
    assert flash.max_range == 30.0
    assert flash.properties["bounce_count"] == 1
    assert flash.properties["activation_delay"] == 0.2
    assert "flashed" in flash.status_effects

def test_ability_instance_creation():
    """Test ability instance creation and initial state."""
    flash_def = STANDARD_ABILITIES["flash"]
    instance = flash_def.create_instance("player1")
    
    assert instance.charges_remaining == flash_def.max_charges
    assert not instance.is_active
    assert not instance.effect_applied
    assert not instance.affected_players

def test_flash_mechanics(mock_players, mock_map):
    """Test flash ability mechanics and player effects."""
    flash_def = STANDARD_ABILITIES["flash"]
    instance = flash_def.create_instance("player1")
    
    # Set up player positions and view directions
    # Player 1: Looking left (away from flash)
    mock_players[0].location = (0, 0, 0)
    mock_players[0].view_direction = (-1, 0, 0)  # Looking left (away from flash)
    mock_players[0].direction = 180  # 180 degrees = facing left
    
    # Player 2: Looking left (towards flash)
    mock_players[1].location = (10, 0, 0)
    mock_players[1].view_direction = (-1, 0, 0)  # Looking left (towards flash)
    mock_players[1].direction = 180  # 180 degrees = facing left
    
    # Player 3: Looking perpendicular to flash
    # Place player at (7, 10) and flash at (7, 0) so the vector to flash is straight down
    # Then have player look right (1, 0, 0) which is perpendicular to the vector to flash
    mock_players[2].location = (7, 10, 0)
    mock_players[2].view_direction = (1, 0, 0)  # Looking right (perpendicular to flash)
    mock_players[2].direction = 0  # 0 degrees = facing right
    
    # Place flash
    instance.current_position3d = (7, 0, 0)  # Flash position
    instance.is_active = True
    
    # Calculate dot products manually to verify our test setup
    # Player 1 (looking away)
    dx1 = 0 - 7  # Player x - flash x (direction from player to flash)
    dy1 = 0 - 0  # Player y - flash y
    length1 = math.sqrt(dx1*dx1 + dy1*dy1)
    dx1, dy1 = dx1/length1, dy1/length1
    dot1 = dx1 * mock_players[0].view_direction[0] + dy1 * mock_players[0].view_direction[1]
    print(f"Player 1 dot product: {dot1}")  # Should be positive (looking away from flash)
    
    # Player 2 (looking towards)
    dx2 = 10 - 7  # Player x - flash x
    dy2 = 0 - 0   # Player y - flash y
    length2 = math.sqrt(dx2*dx2 + dy2*dy2)
    dx2, dy2 = dx2/length2, dy2/length2
    dot2 = dx2 * mock_players[1].view_direction[0] + dy2 * mock_players[1].view_direction[1]
    print(f"Player 2 dot product: {dot2}")  # Should be negative (looking towards flash)
    
    # Player 3 (looking perpendicular)
    dx3 = 7 - 7   # Player x - flash x (0, since same x-coordinate)
    dy3 = 10 - 0  # Player y - flash y (10, straight down to flash)
    length3 = math.sqrt(dx3*dx3 + dy3*dy3)
    dx3, dy3 = dx3/length3, dy3/length3  # This will be (0, 1) - straight down
    # Dot product with (1, 0) view direction should be 0 (perpendicular)
    dot3 = dx3 * mock_players[2].view_direction[0] + dy3 * mock_players[2].view_direction[1]
    print(f"Player 3 dot product: {dot3}")  # Should be 0 (perpendicular)
    
    # Apply flash effect
    instance.apply_effect(mock_map, mock_players)
    
    # Player2 should be flashed (looking towards flash)
    assert mock_players[1].id in list(instance.affected_players), "Player 2 should be affected by flash"
    assert "flashed" in mock_players[1].status_effects and mock_players[1].status_effects["flashed"] == flash_def.duration
    
    # Player1 should not be flashed (looking away)
    assert mock_players[0].id not in list(instance.affected_players), "Player 1 should not be affected by flash"
    assert "flashed" not in mock_players[0].status_effects
    
    # Player3 should not be flashed (perpendicular)
    assert mock_players[2].id not in list(instance.affected_players), "Player 3 should not be affected by flash"
    assert "flashed" not in mock_players[2].status_effects

def test_smoke_mechanics(mock_players):
    """Test smoke ability mechanics and area effects."""
    smoke_def = STANDARD_ABILITIES["smoke"]
    instance = smoke_def.create_instance("player1")
    
    # Set up player positions
    mock_players[0].location = (3, 0, 0)  # Within radius
    mock_players[1].location = (7, 0, 0)  # Within radius
    mock_players[2].location = (20, 0, 0)  # Outside radius
    
    # Place smoke between players
    instance.activate(
        current_time=0.0,
        origin=(5, 0, 0),
        direction=(0, 0, 1)
    )
    
    # Apply smoke effect directly
    instance.apply_effect(None, mock_players)
    
    # Both players within radius should be affected
    assert mock_players[0].id in instance.affected_players
    assert mock_players[1].id in instance.affected_players
    assert "smoked" in mock_players[0].status_effects and mock_players[0].status_effects["smoked"] == smoke_def.duration
    assert "smoked" in mock_players[1].status_effects and mock_players[1].status_effects["smoked"] == smoke_def.duration
    
    # Player3 should not be affected (too far)
    assert mock_players[2].id not in instance.affected_players
    assert "smoked" not in mock_players[2].status_effects

def test_molly_mechanics():
    """Test molly ability mechanics."""
    # Create molly ability instance
    molly_def = AbilityDefinition(
        name="molly",
        description="Test molly",
        ability_type=AbilityType.MOLLY,
        targeting_type=AbilityTarget.PROJECTILE,
        duration=5.0,  # 5 second duration
        effect_radius=3.0,  # 3 unit radius
        damage=10.0,  # 10 damage per tick
    )
    molly = MollyAbilityInstance(molly_def, "player1", "molly1", 1)
    
    # Create test players
    player1 = MockPlayer("player1")
    player1.location = (0, 0, 0)
    player1.health = 100
    player1.armor = 50
    
    player2 = MockPlayer("player2")
    player2.location = (2, 0, 0)  # Within radius
    player2.health = 100
    player2.armor = 0
    
    player3 = MockPlayer("player3")
    player3.location = (5, 0, 0)  # Outside radius
    player3.health = 100
    player3.armor = 0
    
    players = [player1, player2, player3]
    
    # Activate molly at origin
    molly.activate(0.0, (0, 0, 0), (1, 0, 0))
    assert molly.is_active
    
    # Apply effect and check damage
    molly.apply_effect(None, players)
    
    # Player 1 (with armor) should take reduced damage
    assert player1.health == 95  # 5 damage to health (10 total - 5 to armor)
    assert player1.armor == 45  # 5 damage to armor
    assert "burning" in player1.status_effects and player1.status_effects["burning"] == molly_def.duration
    assert "player1" in molly.affected_players
    
    # Player 2 (no armor) should take full damage
    assert player2.health == 90  # Full 10 damage
    assert player2.armor == 0
    assert "burning" in player2.status_effects and player2.status_effects["burning"] == molly_def.duration
    assert "player2" in molly.affected_players
    
    # Player 3 should be unaffected
    assert player3.health == 100
    assert player3.armor == 0
    assert "burning" not in player3.status_effects
    assert "player3" not in molly.affected_players
    
    # Update molly and check effects are removed when inactive
    molly.is_active = False
    molly.update(0.1, 5.1, None, players)  # After duration
    
    assert "burning" not in player1.status_effects
    assert "burning" not in player2.status_effects

def test_ability_duration_and_expiration():
    """Test ability duration tracking and expiration."""
    smoke_def = STANDARD_ABILITIES["smoke"]
    instance = smoke_def.create_instance("player1")
    
    # Activate smoke
    instance.activate(
        current_time=0.0,
        origin=(0, 0, 0),
        direction=(1, 0, 0)
    )
    
    # Check remaining duration
    assert instance.get_remaining_duration(current_time=0.0) == smoke_def.duration
    assert instance.get_remaining_duration(current_time=smoke_def.duration/2) == smoke_def.duration/2
    
    # Verify expiration
    assert instance.get_remaining_duration(current_time=smoke_def.duration + 1) == 0.0
    instance.update(time_step=0.1, current_time=smoke_def.duration + 1, game_map=None, players=[])
    assert not instance.is_active

def test_bounce_mechanics(mock_map):
    """Test ability bounce mechanics."""
    flash_def = STANDARD_ABILITIES["flash"]
    instance = flash_def.create_instance("player1")
    
    # Activate flash with bounce
    instance.activate(
        current_time=0.0,
        origin=(0, 0, 0),
        direction=(1, 0, 0)
    )
    
    assert instance.bounces_remaining == flash_def.properties["bounce_count"]
    
    # Update position and check bounce count
    instance.update(time_step=0.1, current_time=0.1, game_map=mock_map, players=[])
    
    # Verify position update
    assert instance.current_position3d is not None
    assert instance.current_position3d[0] > 0  # Moved in x direction 
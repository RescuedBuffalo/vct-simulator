import pytest
import math
from app.simulation.models.ability import (
    AbilityType, AbilityDefinition, AbilityInstance,
    STANDARD_ABILITIES
)

class MockPlayer:
    def __init__(self, id: str, location, view_direction):
        self.id = id
        self.location = location
        self.view_direction = view_direction
        self.health = 100
        self.armor = 50
        self.shield = True
        self.alive = True
        self.status_effects = []

class MockMap:
    def check_collision(self, start_pos, end_pos):
        # Mock collision detection
        return None

@pytest.fixture
def mock_map():
    return MockMap()

@pytest.fixture
def mock_players():
    return [
        MockPlayer("player1", (0, 0, 0), (1, 0, 0)),  # Looking right
        MockPlayer("player2", (10, 0, 0), (-1, 0, 0)),  # Looking left
        MockPlayer("player3", (0, 10, 0), (0, -1, 0)),  # Looking down
    ]

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

def test_flash_mechanics(mock_players):
    """Test flash ability mechanics and player effects."""
    flash_def = STANDARD_ABILITIES["flash"]
    instance = flash_def.create_instance("player1")
    
    # Activate flash in front of player2
    instance.activate(
        current_time=0.0,
        origin=(5, 0, 0),  # Between player1 and player2
        direction=(1, 0, 0)  # Moving right
    )
    
    assert instance.is_active
    assert instance.charges_remaining == flash_def.max_charges - 1
    
    # Update flash and check effects
    instance.update(time_step=0.1, current_time=0.1, game_map=None, players=mock_players)
    
    # Player2 should be flashed (looking at flash)
    assert "player2" in instance.affected_players
    assert "flashed" in mock_players[1].status_effects
    
    # Player1 should not be flashed (looking away)
    assert "player1" not in instance.affected_players
    assert "flashed" not in mock_players[0].status_effects

def test_smoke_mechanics(mock_players):
    """Test smoke ability mechanics and area effects."""
    smoke_def = STANDARD_ABILITIES["smoke"]
    instance = smoke_def.create_instance("player1")
    
    # Place smoke between players
    instance.activate(
        current_time=0.0,
        origin=(5, 0, 0),
        direction=(0, 0, 1)
    )
    
    # Update smoke and check effects
    instance.update(time_step=0.1, current_time=0.1, game_map=None, players=mock_players)
    
    # Both players within radius should be affected
    assert "player1" in instance.affected_players
    assert "player2" in instance.affected_players
    assert "smoked" in mock_players[0].status_effects
    assert "smoked" in mock_players[1].status_effects
    
    # Player3 should not be affected (too far)
    assert "player3" not in instance.affected_players
    assert "smoked" not in mock_players[2].status_effects

def test_molly_damage_mechanics(mock_players):
    """Test molly ability damage calculations."""
    molly_def = STANDARD_ABILITIES["molly"]
    instance = molly_def.create_instance("player1")
    
    # Place molly on player2
    instance.activate(
        current_time=0.0,
        origin=(10, 0, 0),
        direction=(0, 0, 1)
    )
    
    initial_health = mock_players[1].health
    initial_armor = mock_players[1].armor
    
    # Update molly and check damage
    instance.update(time_step=0.1, current_time=0.1, game_map=None, players=mock_players)
    
    # Verify damage application
    assert mock_players[1].health < initial_health
    assert mock_players[1].armor < initial_armor
    assert "burning" in mock_players[1].status_effects

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
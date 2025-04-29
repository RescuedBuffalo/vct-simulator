import pytest
from app.simulation.models.ability import (
    create_smoke_ability, create_flash_ability, create_molly_ability, create_recon_ability,
    SmokeAbilityInstance, FlashAbilityInstance, MollyAbilityInstance, ReconAbilityInstance
)

class MockPlayer:
    def __init__(self, id, location):
        self.id = id
        self.location = location  # (x, y, z)
        self.health = 100
        self.status_effects = []
        self.view_direction = (1, 0, 0)  # Default looking right
    def apply_damage(self, dmg):
        self.health -= dmg

@pytest.fixture
def mock_players():
    return [
        MockPlayer("p1", (0, 0, 0)),
        MockPlayer("p2", (5, 0, 0)),
        MockPlayer("p3", (20, 0, 0)),
    ]

class DummyMap:
    def cast_bullet(self, origin, direction, max_range, players):
        # Always return no hit for simplicity
        return (origin, None, None)

# Smoke ability: should not affect player state directly
def test_smoke_ability_effect(mock_players):
    smoke_def = create_smoke_ability("TestSmoke", radius=10.0)
    instance = SmokeAbilityInstance(smoke_def, "p1", "smoke1", 2)
    instance.current_position3d = (0, 0, 0)
    instance.apply_effect(DummyMap(), mock_players)
    assert instance.effect_applied
    # No player should be affected
    for p in mock_players:
        assert p.health == 100
        assert 'flashed' not in p.status_effects

# Flash ability: should apply 'flashed' to players in radius
def test_flash_ability_effect(mock_players):
    flash_def = create_flash_ability("TestFlash", duration=1.0)
    instance = FlashAbilityInstance(flash_def, "p1", "flash1", 2)
    instance.current_position3d = (0, 0, 0)
    instance.apply_effect(DummyMap(), mock_players)
    assert instance.effect_applied
    assert 'flashed' in mock_players[0].status_effects
    assert 'flashed' in mock_players[1].status_effects
    assert 'flashed' not in mock_players[2].status_effects

# Molly ability: should damage players in radius
def test_molly_ability_effect(mock_players):
    molly_def = create_molly_ability("TestMolly", radius=10.0, damage=20.0)
    instance = MollyAbilityInstance(molly_def, "p1", "molly1", 1)
    instance.current_position3d = (0, 0, 0)
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
    instance.effect_applied = True
    instance.end_time = 100.0
    instance.pulse_timer = 1.5  # trigger pulse
    instance.update(1.5, 1.5, DummyMap(), mock_players)
    assert 'revealed' in mock_players[0].status_effects
    assert 'revealed' in mock_players[1].status_effects
    assert 'revealed' not in mock_players[2].status_effects 
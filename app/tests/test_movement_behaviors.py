import pytest
from app.simulation.test_movement import create_test_map
from app.simulation.models.map import RampBoundary, StairsBoundary
from app.simulation.models.player import Player


def test_ramp_boundary_get_elevation_at_point():
    # Create a simple ramp: base elevation 1, height 5, direction north
    ramp = RampBoundary("ramp", x=0, y=0, width=10, height=20, z=1, height_z=5, direction="north")
    # At the south side (y=0) elevation == base
    assert ramp.get_elevation_at_point(5, 0) == pytest.approx(1)
    # At the north side (y=20) elevation == top (base + height_z)
    assert ramp.get_elevation_at_point(5, 20) == pytest.approx(6)
    # Outside the ramp footprint returns 0.0
    assert ramp.get_elevation_at_point(20, 20) == pytest.approx(0.0)


def test_stairs_boundary_get_elevation_at_point():
    # Create stairs: base elevation 2, total height 4, 4 steps, direction east
    stairs = StairsBoundary("stairs", x=0, y=0, width=20, height=10, z=2, height_z=4, direction="east", steps=4)
    # At the west end (x=0) elevation == base
    assert stairs.get_elevation_at_point(0, 5) == pytest.approx(2)
    # At the east end (x=20) elevation == top (base + (steps-1)*step_height)
    # step_height = height_z / steps = 1.0, max step index = steps-1 = 3 => elevation=2+3*1 = 5
    assert stairs.get_elevation_at_point(20, 5) == pytest.approx(5)
    # Outside the stairs footprint returns 0.0
    assert stairs.get_elevation_at_point(30, 5) == pytest.approx(0.0)


def test_map_elevation_and_can_move_with_ramp_and_area():
    game_map = create_test_map()
    # Heaven area: should have elevation 3 at center (19,11)
    elev_heaven = game_map.get_elevation_at_position(19, 11)
    assert elev_heaven == pytest.approx(3.0)
    # Ramp footprint: at (19,17) we expect a descending elevation from heaven
    rel_pos = (17 - 16) / 4
    expected_ramp_elev = (1 - rel_pos) * 3.0
    elev_ramp = game_map.get_elevation_at_position(19, 17)
    assert elev_ramp == pytest.approx(expected_ramp_elev)

    # Simple flat movement inside main area
    assert game_map.can_move(6.0, 6.0, 0.0, 7.0, 6.0, 0.0) is True

    # Movement up the ramp should be allowed in stages from ground (south) to heaven (north)
    # Stage 1: from ground level at y=20 to mid-ramp at y=19
    flat_ground = (19.0, 20.0, 0.0)
    mid_ramp_elev = game_map.get_elevation_at_position(19, 19)
    mid_ramp = (19.0, 19.0, mid_ramp_elev)
    assert game_map.can_move(*flat_ground, *mid_ramp) is True
    # Stage 2: from mid-ramp to near summit at y=17
    near_top_elev = game_map.get_elevation_at_position(19, 17)
    near_top = (19.0, 17.0, near_top_elev)
    assert game_map.can_move(*mid_ramp, *near_top) is True
    # Stage 3: from near summit to heaven area at y=16
    summit_elev = game_map.get_elevation_at_position(19, 16)
    summit = (19.0, 16.0, summit_elev)
    assert game_map.can_move(*near_top, *summit) is True

    # Direct movement into heaven without ramp/stairs should be blocked
    start_flat = (19.0, 9.0, 0.0)
    end_heaven = (19.0, 11.0, game_map.get_elevation_at_position(19, 11))
    assert game_map.can_move(*start_flat, *end_heaven) is False


def test_collision_with_object_blocks_movement():
    game_map = create_test_map()
    # box-1 sits at (10,10) footprint 2x2, height_z=1.0
    # A player at (10.5, 10.5, 0) should collide and be invalid
    assert game_map.is_valid_position(10.5, 10.5, 0.0) is False


def test_raycast_and_cast_bullet_against_wall():
    # Raycast should hit the left wall in the main area
    game_map = create_test_map()
    origin = (0.5, 6.0, 1.0)
    direction = (1.0, 0.0, 0.0)
    t, hit_point, hit_obj = game_map.raycast(origin, direction, max_range=100.0)
    assert hit_obj is not None and hit_obj.name == "wall-left"
    assert pytest.approx(hit_point[0], rel=1e-2) == 4.0

    # cast_bullet with no players should hit the same wall
    hit_pt_cb, hit_boundary, hit_player = game_map.cast_bullet(
        origin, direction, max_range=100.0, players=[]
    )
    assert hit_player is None
    assert hit_boundary is not None and hit_boundary.name == "wall-left"


def test_cast_bullet_hits_player_before_wall():
    # Place a player directly in the ray path before the wall
    game_map = create_test_map()
    player = Player(
        id="p1", name="P1", team_id="", role="", agent="",
        aim_rating=0.0, reaction_time=0.0, movement_accuracy=0.0,
        spray_control=0.0, clutch_iq=0.0,
        location=(2.5, 6.0, 0.5)
    )
    origin = (0.5, 6.0, 1.0)
    direction = (1.0, 0.0, 0.0)
    hit_pt, hit_boundary, hit_player = game_map.cast_bullet(
        origin, direction, max_range=100.0, players=[player]
    )
    assert hit_player is player
    assert hit_boundary is None


def test_cast_bullet_misses_everything_returns_max_range():
    # Ray directed into empty space without obstacles
    game_map = create_test_map()
    origin = (0.5, 2.0, 1.0)
    direction = (0.0, -1.0, 0.0)
    max_range = 10.0
    hit_pt, hit_boundary, hit_player = game_map.cast_bullet(
        origin, direction, max_range=max_range, players=[]
    )
    expected_pt = (origin[0], origin[1] + direction[1] * max_range, origin[2])
    assert hit_pt == pytest.approx(expected_pt)
    assert hit_boundary is None
    assert hit_player is None

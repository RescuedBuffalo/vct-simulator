import pytest
from app.simulation.models.map import Map
from app.simulation.models.map_pathfinding import NavigationMesh, CollisionDetector

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
            }
        }
    }
    test_map = Map.from_json(test_map_json)
    
    return test_map

class TestNavigationMesh:
    def test_initialization(self, mock_map):
        assert mock_map.nav_mesh.width == 100
        assert mock_map.nav_mesh.height == 100
        assert mock_map.nav_mesh.grid_width == 100
        assert mock_map.nav_mesh.grid_height == 100
        assert mock_map.nav_mesh.walkable.shape == (100, 100)
        assert mock_map.nav_mesh.elevation.shape == (100, 100)
    
    def test_add_obstacle(self, mock_map):
        # Check wall1 is marked as non-walkable
        assert not mock_map.nav_mesh.is_walkable(45, 41)  # Inside wall1
        assert mock_map.nav_mesh.is_walkable(39, 41)  # Outside wall1
    
    def test_elevation(self, mock_map):
        # Check platform elevation
        platform_elev = mock_map.nav_mesh.get_elevation(25, 25)
        ground_elev = mock_map.nav_mesh.get_elevation(15, 15)
        
        assert abs(platform_elev - 2.0) < 0.1, f"Platform elevation should be 2.0, got {platform_elev}"
        assert abs(ground_elev - 0.0) < 0.1, f"Ground elevation should be 0.0, got {ground_elev}"
        
        # Check stairs elevation at multiple points
        bottom_elev = mock_map.nav_mesh.get_elevation(30, 30)
        middle_elev = mock_map.nav_mesh.get_elevation(30, 32)
        top_elev = mock_map.nav_mesh.get_elevation(30, 34)
        
        assert abs(bottom_elev - 0.0) < 0.1, f"Stairs bottom should be 0.0, got {bottom_elev}"
        assert abs(middle_elev - 0.75) < 0.1, f"Stairs middle should be 0.75, got {middle_elev}"
        assert abs(top_elev - 1.5) < 0.1, f"Stairs top should be 1.5, got {top_elev}"

class TestPathFinder:
    def test_simple_path(self, mock_map):
        start = (0.5, 0.5, 0)  # Slightly offset from edge
        goal = (10.5, 10.5, 0)  # Slightly offset from edge
        path = mock_map.pathfinder.find_path(start, goal)
        
        assert len(path) > 0
        assert abs(path[0][0] - start[0]) < 1.0
        assert abs(path[0][1] - start[1]) < 1.0
        assert abs(path[-1][0] - goal[0]) < 1.0
        assert abs(path[-1][1] - goal[1]) < 1.0
    
    def test_path_with_obstacle(self, mock_map):
        # Path should go around wall1
        start = (35.5, 41.5, 0)  # Slightly offset from wall
        goal = (65.5, 41.5, 0)  # Slightly offset from wall
        path = mock_map.pathfinder.find_path(start, goal)
        
        assert len(path) > 0
        # Check that path goes around the wall
        wall_encountered = False
        for x, y, z in path:
            if 40 <= x <= 60:  # If in wall x-range
                if not (y < 40 or y > 42):  # If not going around wall
                    wall_encountered = True
        assert not wall_encountered, "Path should avoid the wall"
    
    def test_path_with_elevation(self, mock_map):
        # Debug: Print elevation and walkability along the stairs
        print("\nDebug information for stairs:")
        for y in range(30, 35):
            elev = mock_map.nav_mesh.get_elevation(30.0, float(y))
            walk = mock_map.nav_mesh.is_walkable(30.0, float(y))
            print(f"Position (30.0, {y:.1f}): elevation={elev:.2f}, walkable={walk}")
        
        # Path should handle elevation change via stairs
        start = (30.0, 31.0, 0.375)  # Start at first step
        goal = (30.0, 34.0, 1.5)  # End at stairs top
        path = mock_map.pathfinder.find_path(start, goal)
        
        assert len(path) > 0, "Should find a path up the stairs"
        assert len(path) >= 4, "Path should include intermediate points on stairs"
        
        # Check that path follows the stairs with gradual elevation changes
        for i in range(1, len(path)):
            prev_z = path[i-1][2]
            curr_z = path[i][2]
            assert abs(curr_z - prev_z) <= 0.5, f"Elevation change too steep between steps: {abs(curr_z - prev_z)}"
        
        # Verify start and end points
        assert abs(path[0][2] - 0.375) < 0.1, "Path should start at first step"
        assert abs(path[-1][2] - 1.5) < 0.1, "Path should end at stairs top"

class TestCollisionDetector:
    def test_collision_with_wall(self, mock_map):
        # Test collision with wall1
        assert mock_map.collision_detector.check_collision(
            (45, 41, 0),  # Inside wall
            (45, 41, 4)   # Well above wall
        )
        assert not mock_map.collision_detector.check_collision(
            (35, 41, 0),  # Outside wall
            (35, 41, 2)   # Reasonable height above ground
        )
    
    def test_collision_with_elevation(self, mock_map):
        # Test collision with platform edge
        assert mock_map.collision_detector.check_collision(
            (19.5, 20, 0),   # Below platform
            (19.5, 20, 4)    # Well above platform
        ), "Should detect collision when moving too high above platform"
        
        # Test valid vertical movement
        assert not mock_map.collision_detector.check_collision(
            (15, 15, 0),     # Ground level
            (15, 15, 2)      # Reasonable height
        ), "Should allow reasonable vertical movement"
        
        # Test stair movement
        assert not mock_map.collision_detector.check_collision(
            (30, 30, 0),     # Stairs bottom
            (30, 34, 1.5)    # Stairs top
        ), "Should allow movement along stairs"
    
    def test_ray_cast(self, mock_map):
        # Test collision between points
        assert mock_map.collision_detector.check_collision(
            (35, 41, 1),  # Before wall
            (55, 41, 1)   # After wall
        )

def test_create_navigation_mesh(mock_map):
    assert isinstance(mock_map.nav_mesh, NavigationMesh)
    assert mock_map.collision_detector is not None
    assert mock_map.pathfinder is not None
    
    # Verify elevations are set correctly
    assert abs(mock_map.nav_mesh.get_elevation(25, 25) - 2.0) < 0.1  # Platform
    assert abs(mock_map.nav_mesh.get_elevation(10, 10)) < 0.1  # Ground 
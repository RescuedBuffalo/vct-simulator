import pytest
import numpy as np
from ..simulation.models.map_pathfinding import (
    NavigationMesh, PathFinder, CollisionDetector, create_navigation_mesh
)

@pytest.fixture
def simple_map_data():
    return {
        "metadata": {
            "map-size": [100, 100]
        },
        "walls": {
            "wall1": {"x": 40, "y": 40, "w": 20, "h": 2},
            "wall2": {"x": 40, "y": 40, "w": 2, "h": 20}
        },
        "objects": {
            "box1": {"x": 60, "y": 60, "w": 5, "h": 5}
        },
        "map-areas": {
            "platform1": {
                "x": 20,
                "y": 20,
                "w": 10,
                "h": 10,
                "elevation": 2.0
            }
        },
        "elevation-points": [
            {"position": [30, 30], "elevation": 1.5}
        ]
    }

@pytest.fixture
def nav_mesh(simple_map_data):
    return create_navigation_mesh(simple_map_data)

@pytest.fixture
def pathfinder(nav_mesh):
    return PathFinder(nav_mesh)

@pytest.fixture
def collision_detector(nav_mesh):
    return CollisionDetector(nav_mesh)

class TestNavigationMesh:
    def test_initialization(self, nav_mesh):
        assert nav_mesh.width == 100
        assert nav_mesh.height == 100
        assert nav_mesh.grid_width == 100
        assert nav_mesh.grid_height == 100
        assert nav_mesh.walkable.shape == (100, 100)
        assert nav_mesh.elevation.shape == (100, 100)
    
    def test_add_obstacle(self, nav_mesh):
        # Check wall1 is marked as non-walkable
        assert not nav_mesh.is_walkable(45, 41)  # Inside wall1
        assert nav_mesh.is_walkable(39, 41)  # Outside wall1
    
    def test_elevation(self, nav_mesh):
        # Check platform elevation
        assert nav_mesh.get_elevation(25, 25) == 2.0  # Inside platform1
        assert nav_mesh.get_elevation(15, 15) == 0.0  # Outside platform1
        
        # Check elevation point
        assert nav_mesh.get_elevation(30, 30) == 1.5

class TestPathFinder:
    def test_simple_path(self, pathfinder):
        start = (0, 0, 0)
        goal = (10, 10, 0)
        path = pathfinder.find_path(start, goal)
        
        assert len(path) > 0
        assert path[0] == start
        assert path[-1][0] == goal[0]
        assert path[-1][1] == goal[1]
    
    def test_path_with_obstacle(self, pathfinder):
        # Path should go around wall1
        start = (35, 41, 0)
        goal = (45, 41, 0)
        path = pathfinder.find_path(start, goal)
        
        assert len(path) > 0
        # Check that path goes around the wall
        for x, y, z in path:
            assert not (40 <= x <= 60 and 40 <= y <= 42)
    
    def test_path_with_elevation(self, pathfinder):
        # Path should handle elevation change
        start = (15, 15, 0)
        goal = (25, 25, 2)
        path = pathfinder.find_path(start, goal)
        
        assert len(path) > 0
        # Check that path has gradual elevation change
        for i in range(1, len(path)):
            prev_z = path[i-1][2]
            curr_z = path[i][2]
            assert abs(curr_z - prev_z) <= 1.5  # Max climbable height

class TestCollisionDetector:
    def test_collision_with_wall(self, collision_detector):
        # Test collision with wall1
        assert collision_detector.check_collision((45, 41, 0), 1.0, 2.0)
        assert not collision_detector.check_collision((35, 41, 0), 1.0, 2.0)
    
    def test_collision_with_elevation(self, collision_detector):
        # Test collision with platform edge
        assert collision_detector.check_collision((19, 20, 0), 1.0, 2.0)
        assert not collision_detector.check_collision((15, 15, 0), 1.0, 2.0)
    
    def test_ray_cast(self, collision_detector):
        # Test ray hitting wall1
        hit_point = collision_detector.ray_cast(
            (35, 41, 1), (1, 0, 0), 20.0
        )
        assert hit_point is not None
        assert abs(hit_point[0] - 40) < 1.0  # Hit near wall start
        
        # Test ray missing obstacles
        hit_point = collision_detector.ray_cast(
            (0, 0, 0), (1, 1, 0), 10.0
        )
        assert hit_point is None

def test_create_navigation_mesh(simple_map_data):
    nav_mesh = create_navigation_mesh(simple_map_data)
    
    # Check walls are added
    assert not nav_mesh.is_walkable(45, 41)  # wall1
    assert not nav_mesh.is_walkable(41, 45)  # wall2
    
    # Check object is added
    assert not nav_mesh.is_walkable(62, 62)  # box1
    
    # Check elevation
    assert nav_mesh.get_elevation(25, 25) == 2.0  # platform1
    assert nav_mesh.get_elevation(30, 30) == 1.5  # elevation point 
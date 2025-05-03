#!/usr/bin/env python3
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.simulation.models.map import visualize_map_with_pygame, Map

def test_map_collision():
    """Test the collision detection in the Map class."""
    # Load the map
    map_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "maps", "ascent.map.json")
    game_map = Map.from_json(map_path)
    
    # Test some positions
    test_positions = [
        # x, y, expected_result, description
        (5, 16, True, "In T-Spawn area"),
        (10, 18, True, "In Pizza area"),
        (6, 16.5, False, "Inside t-spawn-wall-1"),
        (100, 100, False, "Outside map bounds"),
        (1, 1, False, "Outside any defined area"),
    ]
    
    print("\nMap Collision Detection Test:")
    print(f"Map: {game_map.name}, Size: {game_map.width}x{game_map.height}")
    print("-" * 50)
    
    for x, y, expected, desc in test_positions:
        result = game_map.is_valid_position(x, y)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: Position ({x}, {y}) - {desc}")
        if result:
            area = game_map.get_area_at_position(x, y)
            print(f"  Area: {area}")
            if game_map.is_within_bomb_site(x, y):
                print(f"  In bomb site: {game_map.is_within_bomb_site(x, y)}")
    
    # Test movement between areas
    test_movements = [
        # start_x, start_y, end_x, end_y, expected_result, description
        (5, 16, 6, 16, False, "Movement into wall"),
        (5, 16, 2, 16, True, "Movement within T-Spawn"),
        (8, 16, 9, 17, True, "Movement from bottom-mid-1 to pizza"),
        (1, 16, 20, 20, False, "Movement across multiple areas with obstacles"),
    ]
    
    print("\nMovement Test:")
    print("-" * 50)
    
    for sx, sy, ex, ey, expected, desc in test_movements:
        result = game_map.can_move(sx, sy, 0.0, ex, ey, 0.0)
        status = "PASS" if result == expected else "FAIL"
        start_area = game_map.get_area_at_position(sx, sy) or "None"
        end_area = game_map.get_area_at_position(ex, ey) or "None"
        print(f"{status}: Move from ({sx}, {sy}) to ({ex}, {ey}) - {desc}")
        print(f"  From: {start_area} To: {end_area}")

    # Test area and bomb-site detection
    print("\nArea & Bomb-Site Detection Test:")
    area_tests = [
        # x, y, expected_area, expected_site
        (2, 18, "t-spawn", None),           # inside t-spawn
        (10, 18, "bottom-mid-2", None),     # overlapping bottom-mid-2 vs pizza
        (10, 29, "a-site-2", "a-site"),    # inside A-site zone & bomb boundary
        (25, 13, "ct-spawn-1", None)         # inside CT spawn-1 area
    ]
    for x, y, exp_area, exp_site in area_tests:
        area = game_map.get_area_at_position(x, y)
        site = game_map.is_within_bomb_site(x, y)
        status_a = "PASS" if area == exp_area else "FAIL"
        status_s = "PASS" if site == exp_site else "FAIL"
        print(f"{status_a}: get_area_at_position({x}, {y}) expected {exp_area}, got {area}")
        print(f"{status_s}: is_within_bomb_site({x}, {y}) expected {exp_site}, got {site}")

    print("\nAll Map mechanics tested.")

def main():
    """Run tests and visualize the Ascent map using the Pygame visualizer."""
    # Run collision detection tests
    test_map_collision()
    
    # Run the visualizer
    print("\nStarting map visualizer...")
    visualize_map_with_pygame("maps/ascent.map.json", width=1200, height=900, scale=20)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import sys
import os
import math
import random
import pygame
import time
import collections
from typing import List, Tuple, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.simulation.models.player import Player
from app.simulation.models.map import Map, MapBoundary

def create_test_map():
    """Create a simple test map with walls, elevations, and ramps for collision testing."""
    game_map = Map("Test Map", 32, 32)
    
    # Add map areas
    game_map.areas["main-area"] = MapBoundary(5, 5, 22, 22, "area", "main-area")
    game_map.areas["corridor"] = MapBoundary(12, 3, 8, 2, "area", "corridor")
    game_map.areas["room-1"] = MapBoundary(2, 10, 3, 6, "area", "room-1")
    game_map.areas["room-2"] = MapBoundary(27, 10, 3, 6, "area", "room-2")
    
    # Add an elevated area
    game_map.areas["heaven"] = MapBoundary(18, 10, 6, 6, "area", "heaven", elevation=1, z=3.0)
    
    # Add walls around the main area
    game_map.walls["wall-left"] = MapBoundary(4, 5, 1, 22, "wall", "wall-left", z=0, height_z=3.0)
    game_map.walls["wall-right"] = MapBoundary(27, 5, 1, 22, "wall", "wall-right", z=0, height_z=3.0)
    game_map.walls["wall-top"] = MapBoundary(5, 4, 22, 1, "wall", "wall-top", z=0, height_z=3.0)
    game_map.walls["wall-bottom"] = MapBoundary(5, 27, 22, 1, "wall", "wall-bottom", z=0, height_z=3.0)
    
    # Add some obstacles inside
    game_map.objects["box-1"] = MapBoundary(10, 10, 2, 2, "object", "box-1", z=0, height_z=1.0)
    game_map.objects["box-2"] = MapBoundary(20, 20, 3, 3, "object", "box-2", z=0, height_z=1.5)
    game_map.objects["box-3"] = MapBoundary(15, 18, 1, 1, "object", "box-3", z=0, height_z=0.5)
    
    # Add ramps for elevation changes (lead into heaven area)
    game_map.ramps["ramp-to-heaven"] = MapBoundary(17, 16, 2, 4, "ramp", "ramp-to-heaven", z=0, height_z=3.0)
    game_map.ramps["ramp-to-heaven"].direction = "south"  # Ramp goes from north down to heaven area at y=16
    
    # Add stairs leading into heaven area
    # Position stairs along the eastern edge of heaven (y=12..16, x=22..24)
    game_map.stairs["stairs-1"] = MapBoundary(22, 12, 2, 4, "stairs", "stairs-1", z=0, height_z=3.0)
    
    # Add crouch-only underpass area (clearance 0.7, z=1.0, height_z=0.7)
    # Placed above the player spawn (centered at 15,15)
    game_map.objects["crouch-underpass"] = MapBoundary(6, 14, 4, 4, "object", "crouch-underpass", z=0.7, height_z=0.8)
    
    return game_map

# Add 3D pathfinding functions from maze test
def is_valid_position(game_map, x, y, z, max_jump_height=1.5):
    """Check if a position is valid in the 3D game map."""
    # Check if the position is within any valid area and not colliding with obstacles
    return game_map.is_valid_position(x, y, z, 0.5, 1.0)

def find_path_3d(game_map, start, goal, max_jump_height=1.5):
    """Find a path considering jumping and elevation."""
    # Extract coordinates
    start_x, start_y, start_z = start[0], start[1], start[2]
    goal_x, goal_y, goal_z = goal[0], goal[1], goal[2]
    
    # Update the goal's Z value to match the elevation at that point
    actual_goal_z = game_map.get_elevation_at_position(goal_x, goal_y)
    goal_z = actual_goal_z
    print(f"Adjusting target Z to match terrain elevation: {actual_goal_z}")
    
    # Convert to grid cells
    start_cell = (int(start_x), int(start_y), start_z)
    goal_cell = (int(goal_x), int(goal_y), goal_z)
    
    # Check if start or goal are invalid
    if not is_valid_position(game_map, start_cell[0], start_cell[1], start_cell[2]):
        print(f"Start position {start_cell} is invalid")
        return []
    
    if not is_valid_position(game_map, goal_cell[0], goal_cell[1], goal_cell[2]):
        print(f"Goal position {goal_cell} is invalid")
        # Try finding nearest valid position to goal
        for offset_x in range(-2, 3):
            for offset_y in range(-2, 3):
                test_x = goal_cell[0] + offset_x
                test_y = goal_cell[1] + offset_y
                test_z = game_map.get_elevation_at_position(test_x, test_y)
                if is_valid_position(game_map, test_x, test_y, test_z):
                    print(f"Using alternative goal at {(test_x, test_y, test_z)}")
                    goal_cell = (test_x, test_y, test_z)
                    goal_z = test_z
                    # Break both loops
                    break
            else:
                continue
            break
        else:
            # If we couldn't find any valid position near the goal
            return []
    
    # BFS with elevation consideration
    frontier = collections.deque([start_cell])
    came_from = {start_cell: None}
    
    # Track iteration count to prevent infinite loops
    iterations = 0
    max_iterations = 5000
    
    while frontier and iterations < max_iterations:
        iterations += 1
        current = frontier.popleft()
        current_x, current_y, current_z = current
        
        # Exit if we reached the goal
        if (current_x, current_y) == (goal_cell[0], goal_cell[1]) and abs(current_z - goal_cell[2]) < 0.1:
            print(f"Path found after {iterations} iterations")
            break
        
        # Get current cell elevation
        current_elev = game_map.get_elevation_at_position(current_x, current_y)
        
        # Try all eight directions (including diagonals)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            neighbor_x, neighbor_y = current_x + dx, current_y + dy
            
            # Skip invalid positions or out of bounds
            if (neighbor_x < 0 or neighbor_y < 0 or 
                neighbor_x >= game_map.width or neighbor_y >= game_map.height):
                continue
                
            # Get neighbor elevation (actual height of the terrain)
            neighbor_elev = game_map.get_elevation_at_position(neighbor_x, neighbor_y)
            
            # Check for special traversal through stairs or ramps
            is_on_stairs = False
            is_on_ramp = False
            
            # Check if current position is on stairs
            for stair in game_map.stairs.values():
                if (stair.x <= current_x <= stair.x + stair.width and 
                    stair.y <= current_y <= stair.y + stair.height):
                    is_on_stairs = True
                    break
            
            # Check if current position is on ramp
            for ramp in game_map.ramps.values():
                if (ramp.x <= current_x <= ramp.x + ramp.width and 
                    ramp.y <= current_y <= ramp.y + ramp.height):
                    is_on_ramp = True
                    break
            
            # Same level - easy transition
            if abs(neighbor_elev - current_z) < 0.1:
                neighbor_z = neighbor_elev
                neighbor = (neighbor_x, neighbor_y, neighbor_z)
                if neighbor not in came_from and is_valid_position(game_map, neighbor_x, neighbor_y, neighbor_z):
                    came_from[neighbor] = current
                    frontier.append(neighbor)
            
            # Going down is always possible
            elif neighbor_elev < current_z:
                neighbor_z = neighbor_elev
                neighbor = (neighbor_x, neighbor_y, neighbor_z)
                if neighbor not in came_from and is_valid_position(game_map, neighbor_x, neighbor_y, neighbor_z):
                    came_from[neighbor] = current
                    frontier.append(neighbor)
            
            # Going up requires a jump check or stairs/ramp
            elif neighbor_elev > current_z:
                # Allow higher climbs when on stairs or ramps
                max_climb = max_jump_height
                if is_on_stairs or is_on_ramp:
                    max_climb = 3.0  # Allow climbing full stairs height
                
                if neighbor_elev - current_z <= max_climb:
                    neighbor_z = neighbor_elev
                    neighbor = (neighbor_x, neighbor_y, neighbor_z)
                    if neighbor not in came_from and is_valid_position(game_map, neighbor_x, neighbor_y, neighbor_z):
                        came_from[neighbor] = current
                        frontier.append(neighbor)
    
    if iterations >= max_iterations:
        print(f"Pathfinding reached iteration limit ({max_iterations})")
        return []
    
    # Goal processing
    goal_grid = (goal_cell[0], goal_cell[1], goal_cell[2])
    if goal_grid not in came_from:
        print("No path found - goal not reachable")
        return []
    
    # Reconstruct path
    path = []
    current = goal_grid
    
    while current:
        path.append((current[0] + 0.5, current[1] + 0.5, current[2]))
        current = came_from[current]
    
    path.reverse()
    return path

def run_movement_test():
    """Test the player movement with physics and collision response."""
    pygame.init()
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("3D Movement Physics Test")
    clock = pygame.time.Clock()
    
    # Create a test map
    game_map = create_test_map()
    
    # Create a player
    player = Player(
        id="test-player",
        name="Test Player",
        team_id="test-team",
        role="duelist",
        agent="Jett",
        aim_rating=80.0,
        reaction_time=200.0,
        movement_accuracy=75.0,
        spray_control=65.0,
        clutch_iq=70.0,
        location=(15.0, 15.0, 0.0),
        direction=0.0,
        armor=50
    )
    
    # For AI player testing
    ai_player = Player(
        id="ai-player",
        name="AI Player",
        team_id="test-team",
        role="sentinel",
        agent="Sage",
        aim_rating=80.0,
        reaction_time=200.0,
        movement_accuracy=75.0,
        spray_control=65.0,
        clutch_iq=70.0,
        location=(10.0, 10.0, 0.0),
        direction=0.0,
        armor=50
    )
    
    # AI movement points to patrol between
    ai_patrol_points = [
        (10.0, 10.0),
        (20.0, 10.0),
        (20.0, 20.0),
        (10.0, 20.0)
    ]
    current_patrol_point = 0
    # Dynamic waypoints set by mouse clicks with pathfinding
    ai_waypoints: List[Tuple[float, float, float]] = []
    
    # Scale factor for drawing
    scale = 20
    
    # Main game loop
    running = True
    frame_count = 0
    last_fps_update = time.time()
    fps = 0
    prev_jump = False
    bullet_path = None
    bullet_timer = 0
    BULLET_LIFETIME = 15  # frames
    damage_text = None
    damage_timer = 0
    DAMAGE_LIFETIME = 30  # frames
    
    # Font for labeling objects
    label_font = pygame.font.SysFont(None, 20)
    # Variables for displaying object hit messages
    object_hit_message = None  # type: Optional[str]
    object_hit_timer = 0      # frames to display the message
    
    while running:
        # preview time step for elevation check
        dt_preview = 1.0 / 60.0
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                wx = mx / scale
                wy = (screen_height - my) / scale
                if event.button == 1:
                    # Left click: shoot
                    px, py, pz = player.location
                    # Fire from player's head
                    shooter_z = (pz + player.height - 0.25)
                    dx = wx - px
                    dy = wy - py
                    dz = 0
                    print("dx, dy, dz: ", dx, dy, dz)
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if dist == 0:
                        continue
                    # Normalize shooting direction (no aim spread)
                    norm = math.sqrt(dx*dx + dy*dy + dz*dz)
                    dx /= norm
                    dy /= norm
                    dz /= norm
                    # Raycast bullet against map and players
                    origin = (px, py, shooter_z)
                    print(f"Bullet origin: {origin}")
                    print(f"Click location: ({wx}, {wy})")
                    direction = (dx, dy, dz)
                    max_range = 50.0
                    hit_point, hit_boundary, hit_player = game_map.cast_bullet(origin, direction, max_range, [ai_player])
                    # Apply damage through the player method if we hit a player
                    if hit_player:
                        raw_damage = 40
                        actual_damage = hit_player.apply_damage(raw_damage)
                        damage_text = (actual_damage, (hit_player.location[0], hit_player.location[1], hit_player.location[2] + hit_player.height))
                        damage_timer = DAMAGE_LIFETIME
                    # Display object hit message if we hit an object
                    if hit_boundary and getattr(hit_boundary, 'boundary_type', '') == 'object' and not hit_player:
                        object_hit_message = f"{hit_boundary.name} hit"
                        object_hit_timer = 60  # show for 60 frames
                    # Determine bullet path for drawing
                    if hit_point:
                        bullet_path = ((px, py), (hit_point[0], hit_point[1]))
                    else:
                        bullet_path = ((px, py), (origin[0] + direction[0] * max_range, origin[1] + direction[1] * max_range))
                    bullet_timer = BULLET_LIFETIME
                elif event.button == 3:
                    # Right click: set AI waypoint using pathfinding
                    # Get the elevation at the target position
                    target_elevation = game_map.get_elevation_at_position(wx, wy)
                    print(f"Setting AI waypoint at ({wx}, {wy}, {target_elevation})")
                    
                    # Find path from AI's current position to the target
                    ai_path = find_path_3d(
                        game_map,
                        (ai_player.location[0], ai_player.location[1], ai_player.location[2]),
                        (wx, wy, target_elevation),
                        max_jump_height=1.5
                    )
                    
                    if ai_path:
                        print(f"Path found with {len(ai_path)} waypoints")
                        ai_waypoints = ai_path
                        current_patrol_point = 0
                    else:
                        print("No path found to target position! Using direct point instead.")
                        # Fall back to direct waypoint if no path found
                        # For direct waypoint, use surrounding patrol points to find a way there
                        # This will avoid the AI getting stuck when no direct path exists
                        nearest_patrol_point = min(
                            ai_patrol_points,
                            key=lambda p: math.sqrt((p[0] - wx)**2 + (p[1] - wy)**2)
                        )
                        ai_waypoints = [(nearest_patrol_point[0], nearest_patrol_point[1], 
                                        game_map.get_elevation_at_position(nearest_patrol_point[0], nearest_patrol_point[1]))]
                        object_hit_message = "Target unreachable - using nearest patrol point"
                        object_hit_timer = 60
        
        # Get keyboard input for player movement
        keys = pygame.key.get_pressed()
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        raw_jump = keys[pygame.K_SPACE]
        jump = raw_jump and not prev_jump
        prev_jump = raw_jump

        # Horizontal counter-strafe
        if left and right:
            movement_x = 0
            # Immediately stop horizontal motion
            player.velocity = (0.0, player.velocity[1], player.velocity[2])
        elif left:
            movement_x = -1
        elif right:
            movement_x = 1
        else:
            movement_x = 0

        # Vertical counter-strafe
        if up and down:
            movement_y = 0
            # Immediately stop vertical motion
            player.velocity = (player.velocity[0], 0.0, player.velocity[2])
        elif up:
            movement_y = 1
        elif down:
            movement_y = -1
        else:
            movement_y = 0
        
        # Set movement inputs for player
        is_walking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        is_crouching = keys[pygame.K_c]
        player.set_movement_input((movement_x, movement_y), is_walking, is_crouching, jump)
        
        # Update AI player movement (patrol or follow waypoints)
        if ai_waypoints:
            # Get current target from waypoints list
            current_waypoint = ai_waypoints[current_patrol_point]
            target_point = (current_waypoint[0], current_waypoint[1])
            target_z = current_waypoint[2]
            
            # Calculate distance to current waypoint
            distance_to_target = math.sqrt(
                (ai_player.location[0] - target_point[0])**2 + 
                (ai_player.location[1] - target_point[1])**2
            )
            
            # If AI has reached the waypoint, move to next point
            if distance_to_target < 0.5:
                current_patrol_point += 1
                if current_patrol_point >= len(ai_waypoints):
                    # Reached end of path
                    current_patrol_point = 0
                    if len(ai_waypoints) > 1:
                        # Loop through waypoints if multiple exist
                        print("Completed path, looping back to beginning")
                    else:
                        # Stop if only one waypoint
                        ai_waypoints = []
                        print("Reached destination")
                        continue
                
                # Get new target
                if ai_waypoints:
                    current_waypoint = ai_waypoints[current_patrol_point]
                    target_point = (current_waypoint[0], current_waypoint[1])
                    target_z = current_waypoint[2]
            
            # Calculate direction from AI to target
            ai_direction_x = target_point[0] - ai_player.location[0]
            ai_direction_y = target_point[1] - ai_player.location[1]
            
            # Normalize direction vector
            if ai_direction_x != 0 or ai_direction_y != 0:
                magnitude = math.sqrt(ai_direction_x**2 + ai_direction_y**2)
                ai_direction_x /= magnitude
                ai_direction_y /= magnitude
            
            # Decide if AI should jump
            current_x, current_y, current_z = ai_player.location
            desired_x = current_x + ai_direction_x
            desired_y = current_y + ai_direction_y
            
            # Get current location info
            current_elevation = game_map.get_elevation_at_position(current_x, current_y)
            next_elevation = game_map.get_elevation_at_position(desired_x, desired_y)
            
            # Check if on stairs or ramp for special movement
            is_on_stairs = False
            is_on_ramp = False
            
            # Check if current position is on stairs
            for stair in game_map.stairs.values():
                if (stair.x <= current_x <= stair.x + stair.width and 
                    stair.y <= current_y <= stair.y + stair.height):
                    is_on_stairs = True
                    break
            
            # Check if current position is on ramp
            for ramp in game_map.ramps.values():
                if (ramp.x <= current_x <= ramp.x + ramp.width and 
                    ramp.y <= current_y <= ramp.y + ramp.height):
                    is_on_ramp = True
                    break
            
            # If significant elevation difference, consider jumping
            ai_jump = False
            elevation_difference = target_z - current_z
            
            # Always jump when on stairs/ramps going up
            if is_on_stairs or is_on_ramp:
                if elevation_difference > 0.1 and ai_player.is_on_ground():
                    ai_jump = True
                    print(f"AI jumping on stairs/ramp to elevation {target_z} (current: {current_z})")
            # Normal jumping for smaller height differences
            elif elevation_difference > 0.3 and elevation_difference < 1.5 and ai_player.is_on_ground():
                ai_jump = True
                print(f"AI jumping to elevation {target_z} (current: {current_z})")
        
        else:
            # Fall back to basic patrol if no waypoints
            targets = ai_patrol_points
            target_point = targets[current_patrol_point % len(targets)]
            
            distance_to_target = math.sqrt(
                (ai_player.location[0] - target_point[0])**2 + 
                (ai_player.location[1] - target_point[1])**2
            )
            
            # If AI has reached the target, move to next point
            if distance_to_target < 0.5:
                current_patrol_point = (current_patrol_point + 1) % len(targets)
                target_point = targets[current_patrol_point]
            
            # Calculate direction from AI to target
            ai_direction_x = target_point[0] - ai_player.location[0]
            ai_direction_y = target_point[1] - ai_player.location[1]
            
            # Normalize direction vector
            if ai_direction_x != 0 or ai_direction_y != 0:
                magnitude = math.sqrt(ai_direction_x**2 + ai_direction_y**2)
                ai_direction_x /= magnitude
                ai_direction_y /= magnitude
            
            # Decide if AI should jump for patrol mode
            current_x, current_y, _ = ai_player.location
            desired_x = current_x + ai_direction_x
            desired_y = current_y + ai_direction_y
            
            # Check elevation difference
            current_elevation = game_map.get_elevation_at_position(current_x, current_y)
            target_elevation = game_map.get_elevation_at_position(desired_x, desired_y)
            
            # If significant elevation difference, consider jumping
            ai_jump = False
            elevation_difference = target_elevation - current_elevation
            if elevation_difference > 0.3 and elevation_difference < 1.5:
                # Try to jump over small obstacles
                ai_jump = random.random() < 0.7  # 70% chance
            elif random.random() < 0.02 and ai_player.is_on_ground():
                ai_jump = True  # Random jumping
        
        # Set AI movement input
        ai_player.set_movement_input((ai_direction_x, ai_direction_y), False, False, ai_jump)
        
        # Update physics for both players
        time_step = 1.0 / 60.0  # Fixed time step for physics
        player.update_movement(time_step, game_map)
        ai_player.update_movement(time_step, game_map)
        
        # Clear screen
        screen.fill((255, 255, 255))
        
        # Draw map
        for area_name, area in game_map.areas.items():
            # Draw areas with different colors based on type
            if area.elevation > 0:
                color = (180, 180, 220)  # Bluish for elevated areas
            else:
                color = (200, 200, 200)  # Default gray
            
            pygame.draw.rect(
                screen, 
                color, 
                pygame.Rect(
                    area.x * scale, 
                    screen_height - (area.y + area.height) * scale, 
                    area.width * scale, 
                    area.height * scale
                )
            )
            # Draw outline
            pygame.draw.rect(
                screen, 
                (0, 0, 0), 
                pygame.Rect(
                    area.x * scale, 
                    screen_height - (area.y + area.height) * scale, 
                    area.width * scale, 
                    area.height * scale
                ), 
                1
            )
        
        # Draw walls
        for wall_name, wall in game_map.walls.items():
            pygame.draw.rect(
                screen, 
                (100, 100, 100), 
                pygame.Rect(
                    wall.x * scale, 
                    screen_height - (wall.y + wall.height) * scale, 
                    wall.width * scale, 
                    wall.height * scale
                )
            )
        
        # Draw objects
        for obj_name, obj in game_map.objects.items():
            # Height-based color (taller = darker)
            darkness = min(255, 150 + int(obj.height_z * 30))
            pygame.draw.rect(
                screen, 
                (darkness, darkness-50, darkness-100), 
                pygame.Rect(
                    obj.x * scale, 
                    screen_height - (obj.y + obj.height) * scale, 
                    obj.width * scale, 
                    obj.height * scale
                )
            )
            # Draw labels only for boxes
            if obj_name.startswith("box"):
                label_surface = label_font.render(obj_name, True, (0, 0, 0))
                label_x = int((obj.x + obj.width / 2) * scale) - label_surface.get_width() // 2
                label_y = int(screen_height - (obj.y + obj.height / 2) * scale) - label_surface.get_height() // 2
                screen.blit(label_surface, (label_x, label_y))
        
        # Draw ramps with directional marking
        for ramp_name, ramp in game_map.ramps.items():
            pygame.draw.rect(
                screen, 
                (150, 180, 120), 
                pygame.Rect(
                    ramp.x * scale, 
                    screen_height - (ramp.y + ramp.height) * scale, 
                    ramp.width * scale, 
                    ramp.height * scale
                )
            )
            # Draw arrow showing direction
            mid_x = ramp.x * scale + (ramp.width * scale / 2)
            mid_y = screen_height - (ramp.y * scale + (ramp.height * scale / 2))
            
            # Draw direction arrow
            if ramp.direction == "north":
                pygame.draw.line(screen, (0, 0, 0), (mid_x, mid_y + 10), (mid_x, mid_y - 10), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x, mid_y - 10), (mid_x - 5, mid_y - 5), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x, mid_y - 10), (mid_x + 5, mid_y - 5), 2)
            elif ramp.direction == "south":
                pygame.draw.line(screen, (0, 0, 0), (mid_x, mid_y - 10), (mid_x, mid_y + 10), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x, mid_y + 10), (mid_x - 5, mid_y + 5), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x, mid_y + 10), (mid_x + 5, mid_y + 5), 2)
            elif ramp.direction == "east":
                pygame.draw.line(screen, (0, 0, 0), (mid_x - 10, mid_y), (mid_x + 10, mid_y), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x + 10, mid_y), (mid_x + 5, mid_y - 5), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x + 10, mid_y), (mid_x + 5, mid_y + 5), 2)
            elif ramp.direction == "west":
                pygame.draw.line(screen, (0, 0, 0), (mid_x + 10, mid_y), (mid_x - 10, mid_y), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x - 10, mid_y), (mid_x - 5, mid_y - 5), 2)
                pygame.draw.line(screen, (0, 0, 0), (mid_x - 10, mid_y), (mid_x - 5, mid_y + 5), 2)
        
        # Draw stairs
        for stair_name, stair in game_map.stairs.items():
            pygame.draw.rect(
                screen, 
                (180, 150, 120), 
                pygame.Rect(
                    stair.x * scale, 
                    screen_height - (stair.y + stair.height) * scale, 
                    stair.width * scale, 
                    stair.height * scale
                )
            )
            # Draw stair pattern
            steps = 5
            for i in range(steps):
                step_y = stair.y + (i * stair.height / steps)
                pygame.draw.line(
                    screen,
                    (0, 0, 0),
                    (stair.x * scale, screen_height - step_y * scale),
                    ((stair.x + stair.width) * scale, screen_height - step_y * scale),
                    1
                )
        
        # Draw player
        player_pos = (
            int(player.location[0] * scale), 
            int(screen_height - player.location[1] * scale)
        )
        player_radius = int(player.radius * scale)
        
        # Color player based on z-position (height above ground)
        height_color = min(255, 50 + int(player.z_position * 50))
        pygame.draw.circle(screen, (0, 0, max(0, height_color)), player_pos, player_radius)
        
        # Show height text above player
        font = pygame.font.SysFont(None, 24)
        height_text = font.render(f"z: {player.z_position:.1f}", True, (0, 0, 0))
        screen.blit(height_text, (player_pos[0] - 20, player_pos[1] - 30))
        
        # Show if player is jumping
        if player.in_air:
            jump_text = font.render("Jumping", True, (255, 0, 0))
            screen.blit(jump_text, (player_pos[0] - 30, player_pos[1] - 50))
        
        # Draw player velocity vector
        pygame.draw.line(
            screen,
            (0, 255, 0),
            player_pos,
            (
                int(player_pos[0] + player.velocity[0] * scale * 2),
                int(player_pos[1] - player.velocity[1] * scale * 2)
            ),
            2
        )
        
        # Draw AI player
        ai_pos = (
            int(ai_player.location[0] * scale), 
            int(screen_height - ai_player.location[1] * scale)
        )
        ai_radius = int(ai_player.radius * scale)
        
        # Color AI based on z-position
        ai_height_color = min(255, 50 + int(ai_player.z_position * 50))
        pygame.draw.circle(screen, (height_color, 0, 0), ai_pos, ai_radius)
        
        # Show AI height text
        ai_height_text = font.render(f"z: {ai_player.z_position:.1f}", True, (0, 0, 0))
        screen.blit(ai_height_text, (ai_pos[0] - 20, ai_pos[1] - 30))
        
        # Draw AI velocity vector
        pygame.draw.line(
            screen,
            (255, 0, 0),
            ai_pos,
            (
                int(ai_pos[0] + ai_player.velocity[0] * scale * 2),
                int(ai_pos[1] - ai_player.velocity[1] * scale * 2)
            ),
            2
        )
        
        # Display AI armor above head
        armor_text = font.render(f"A: {ai_player.armor}", True, (0, 0, 255))
        screen.blit(armor_text, (ai_pos[0] - 20, ai_pos[1] - 10))
        
        # Draw target point for AI
        pygame.draw.circle(
            screen,
            (255, 0, 0),
            (int(target_point[0] * scale), int(screen_height - target_point[1] * scale)),
            5,
            1
        )
        
        # Draw bullet path if active
        if bullet_path and bullet_timer > 0:
            start, end = bullet_path
            pygame.draw.line(
                screen, (255, 0, 0),
                (int(start[0] * scale), int(screen_height - start[1] * scale)),
                (int(end[0] * scale), int(screen_height - end[1] * scale)), 3
            )
            # Draw a marker at hit point for visibility
            hit_x, hit_y = end
            pygame.draw.circle(
                screen, (255, 255, 0),
                (int(hit_x * scale), int(screen_height - hit_y * scale)),
                5, 0  # filled circle for visibility
            )
            bullet_timer -= 1
            if bullet_timer <= 0:
                bullet_path = None
        # Draw damage text if active
        if damage_text and damage_timer > 0:
            dmg, (x, y, z) = damage_text
            font = pygame.font.SysFont(None, 32)
            dmg_surface = font.render(f"-{dmg}", True, (255, 0, 0))
            sx = int(x * scale)
            sy = int(screen_height - y * scale - z * scale - 30)
            screen.blit(dmg_surface, (sx - dmg_surface.get_width() // 2, sy))
            damage_timer -= 1
            if damage_timer <= 0:
                damage_text = None
        
        # Draw waypoints for AI
        if ai_waypoints:
            # Draw the path
            for i in range(len(ai_waypoints)):
                wp = ai_waypoints[i]
                wp_screen = (int(wp[0] * scale), int(screen_height - wp[1] * scale))
                
                # Draw different sized circles for waypoints
                size = 5 if i == current_patrol_point else 3
                color = (0, 255, 0) if i == current_patrol_point else (0, 200, 0)
                
                pygame.draw.circle(
                    screen, color,
                    wp_screen,
                    size
                )
                
                # Draw lines connecting waypoints
                if i > 0:
                    prev_wp = ai_waypoints[i-1]
                    prev_screen = (int(prev_wp[0] * scale), int(screen_height - prev_wp[1] * scale))
                    pygame.draw.line(screen, (0, 200, 0), prev_screen, wp_screen, 1)
        
        # Calculate and display FPS
        frame_count += 1
        if time.time() - last_fps_update >= 1.0:
            fps = frame_count
            frame_count = 0
            last_fps_update = time.time()
        
        fps_text = font.render(f"FPS: {fps}", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))
        
        # Draw player position text
        pos_text = font.render(f"Pos: {player.location[0]:.2f}, {player.location[1]:.2f}, {player.location[2]:.2f}", True, (0, 0, 0))
        screen.blit(pos_text, (10, 30))
        
        # Draw object hit message if active
        if object_hit_timer > 0 and object_hit_message:
            msg_surface = font.render(object_hit_message, True, (255, 0, 0))
            screen.blit(msg_surface, (10, 50))
            object_hit_timer -= 1
        
        # Update display
        pygame.display.flip()
        
        # Cap frame rate
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    run_movement_test() 
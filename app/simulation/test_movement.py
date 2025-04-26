#!/usr/bin/env python3
import sys
import os
import math
import random
import pygame
import time
from typing import List, Tuple

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
    game_map.objects["crouch-underpass"] = MapBoundary(6, 14, 4, 4, "object", "crouch-underpass", z=0.7, height_z=0.7)
    
    return game_map

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
        direction=0.0
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
        direction=0.0
    )
    
    # AI movement points to patrol between
    ai_patrol_points = [
        (10.0, 10.0),
        (20.0, 10.0),
        (20.0, 20.0),
        (10.0, 20.0)
    ]
    current_patrol_point = 0
    # Dynamic waypoints set by mouse clicks
    ai_waypoints: List[Tuple[float,float]] = []
    
    # Scale factor for drawing
    scale = 20
    
    # Main game loop
    running = True
    frame_count = 0
    last_fps_update = time.time()
    fps = 0
    prev_jump = False
    
    while running:
        # preview time step for elevation check
        dt_preview = 1.0 / 60.0
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Convert screen to world coords
                wx = mx / scale
                wy = (screen_height - my) / scale
                ai_waypoints = [(wx, wy)]
                current_patrol_point = 0
        
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
        
        # Update AI player movement (patrol or user waypoint)
        # Choose between dynamic waypoints or patrol list
        targets = ai_waypoints if ai_waypoints else ai_patrol_points
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
        
        # Decide if AI should jump
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
        
        # Draw target point for AI
        pygame.draw.circle(
            screen,
            (255, 0, 0),
            (int(target_point[0] * scale), int(screen_height - target_point[1] * scale)),
            5,
            1
        )
        
        # Calculate and display FPS
        frame_count += 1
        if time.time() - last_fps_update >= 1.0:
            fps = frame_count
            frame_count = 0
            last_fps_update = time.time()
        
        fps_text = font.render(f"FPS: {fps}", True, (0, 0, 0))
        screen.blit(fps_text, (10, 10))
        
        # Update display
        pygame.display.flip()
        
        # Cap frame rate
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    run_movement_test() 
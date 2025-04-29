import pygame
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
import math
import colorsys

class MapVisualizer:
    """Enhanced map visualization system with debugging and analysis features."""
    
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.scale = 20
        self.offset_x = 0
        self.offset_y = 0
        self.zoom = 1.0
        
        # Visualization modes
        self.show_grid = True
        self.show_elevation = True
        self.show_heatmap = False
        self.show_paths = False
        self.show_los = False  # Line of sight
        self.show_debug = False
        
        # Colors
        self.colors = {
            'background': (240, 240, 240),
            'grid': (200, 200, 200),
            'wall': (80, 80, 80),
            'object': (120, 120, 120),
            'site_a': (255, 200, 200),
            'site_b': (200, 200, 255),
            'site_c': (200, 255, 200),
            'spawn_t': (255, 220, 180),
            'spawn_ct': (180, 220, 255),
            'elevation': (150, 150, 150),
            'path': (100, 200, 100),
            'los': (255, 100, 100),
        }
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 12)
        self.title_font = pygame.font.SysFont('Arial', 24)
        
        # Analysis data
        self.heatmap_data = None
        self.path_data = []
        self.los_points = []
        self.debug_info = {}
        
    def load_map(self, map_data: Dict):
        """Load map data for visualization."""
        self.map_data = map_data
        self.map_size = map_data.get("metadata", {}).get("map-size", [100, 100])
        
        # Calculate initial scale and offset to fit map
        map_width = self.map_size[0] * self.scale
        map_height = self.map_size[1] * self.scale
        self.offset_x = (self.width - map_width) // 2
        self.offset_y = (self.height - map_height) // 2
        
        # Initialize heatmap if needed
        if self.show_heatmap:
            self.heatmap_data = np.zeros((self.map_size[0], self.map_size[1]))
    
    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        screen_x = int(x * self.scale * self.zoom + self.offset_x)
        screen_y = int(y * self.scale * self.zoom + self.offset_y)
        return (screen_x, screen_y)
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        world_x = (screen_x - self.offset_x) / (self.scale * self.zoom)
        world_y = (screen_y - self.offset_y) / (self.scale * self.zoom)
        return (world_x, world_y)
    
    def draw_grid(self):
        """Draw coordinate grid."""
        if not self.show_grid:
            return
            
        grid_size = 5  # World units between grid lines
        
        # Calculate visible grid range
        start_x = int(self.screen_to_world(0, 0)[0] // grid_size) * grid_size
        end_x = int(self.screen_to_world(self.width, 0)[0] // grid_size + 1) * grid_size
        start_y = int(self.screen_to_world(0, 0)[1] // grid_size) * grid_size
        end_y = int(self.screen_to_world(0, self.height)[1] // grid_size + 1) * grid_size
        
        # Draw vertical lines
        for x in range(start_x, end_x, grid_size):
            start = self.world_to_screen(x, start_y)
            end = self.world_to_screen(x, end_y)
            pygame.draw.line(self.screen, self.colors['grid'], start, end, 1)
            
        # Draw horizontal lines
        for y in range(start_y, end_y, grid_size):
            start = self.world_to_screen(start_x, y)
            end = self.world_to_screen(end_x, y)
            pygame.draw.line(self.screen, self.colors['grid'], start, end, 1)
    
    def draw_elevation(self):
        """Draw elevation contours and heights."""
        if not self.show_elevation or 'elevation' not in self.map_data:
            return
            
        for area in self.map_data.get('map-areas', {}).values():
            if 'elevation' in area:
                # Draw area with elevation-based color
                elev = area['elevation']
                color = self.get_elevation_color(elev)
                rect = pygame.Rect(
                    *self.world_to_screen(area['x'], area['y']),
                    int(area['w'] * self.scale * self.zoom),
                    int(area['h'] * self.scale * self.zoom)
                )
                pygame.draw.rect(self.screen, color, rect)
                
                # Draw elevation text
                text = self.font.render(f"{elev}u", True, (0, 0, 0))
                text_pos = self.world_to_screen(
                    area['x'] + area['w']/2,
                    area['y'] + area['h']/2
                )
                self.screen.blit(text, (text_pos[0] - text.get_width()/2,
                                      text_pos[1] - text.get_height()/2))
    
    def get_elevation_color(self, elevation: float) -> Tuple[int, int, int]:
        """Get color for elevation visualization."""
        # Use HSV color space for better elevation visualization
        hue = (elevation % 360) / 360.0  # Cycle through hues
        rgb = colorsys.hsv_to_rgb(hue, 0.3, 0.9)  # Light, slightly saturated colors
        return tuple(int(x * 255) for x in rgb)
    
    def draw_heatmap(self):
        """Draw activity/position heatmap overlay."""
        if not self.show_heatmap or self.heatmap_data is None:
            return
            
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Normalize heatmap data
        if np.max(self.heatmap_data) > 0:
            normalized = self.heatmap_data / np.max(self.heatmap_data)
            
            # Draw heatmap points
            for y in range(self.heatmap_data.shape[0]):
                for x in range(self.heatmap_data.shape[1]):
                    if normalized[y, x] > 0:
                        pos = self.world_to_screen(x, y)
                        radius = int(2 * self.scale * self.zoom)
                        alpha = int(normalized[y, x] * 128)
                        pygame.draw.circle(surface, (255, 0, 0, alpha), pos, radius)
        
        self.screen.blit(surface, (0, 0))
    
    def draw_paths(self):
        """Draw pathfinding visualization."""
        if not self.show_paths:
            return
            
        for path in self.path_data:
            if len(path) < 2:
                continue
                
            # Draw path lines
            points = [self.world_to_screen(x, y) for x, y in path]
            pygame.draw.lines(self.screen, self.colors['path'], False, points, 2)
            
            # Draw waypoints
            for point in points:
                pygame.draw.circle(self.screen, self.colors['path'], point, 3)
    
    def draw_line_of_sight(self):
        """Draw line of sight visualization."""
        if not self.show_los or not self.los_points:
            return
            
        for start, end, has_los in self.los_points:
            start_pos = self.world_to_screen(*start)
            end_pos = self.world_to_screen(*end)
            color = (0, 255, 0) if has_los else (255, 0, 0)
            pygame.draw.line(self.screen, color, start_pos, end_pos, 1)
    
    def draw_debug_info(self):
        """Draw debug information overlay."""
        if not self.show_debug:
            return
            
        y = 10
        for key, value in self.debug_info.items():
            text = self.font.render(f"{key}: {value}", True, (0, 0, 0))
            self.screen.blit(text, (10, y))
            y += 20
    
    def update_heatmap(self, x: float, y: float, value: float = 1.0):
        """Update heatmap with new position data."""
        if self.heatmap_data is not None:
            ix, iy = int(x), int(y)
            if 0 <= ix < self.heatmap_data.shape[1] and 0 <= iy < self.heatmap_data.shape[0]:
                self.heatmap_data[iy, ix] += value
    
    def add_path(self, path: List[Tuple[float, float]]):
        """Add a path for visualization."""
        self.path_data.append(path)
    
    def add_los_check(self, start: Tuple[float, float], end: Tuple[float, float], has_los: bool):
        """Add a line of sight check result."""
        self.los_points.append((start, end, has_los))
    
    def set_debug_info(self, info: Dict):
        """Update debug information."""
        self.debug_info = info
    
    def handle_input(self):
        """Handle user input for pan/zoom/toggles."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_e:
                    self.show_elevation = not self.show_elevation
                elif event.key == pygame.K_h:
                    self.show_heatmap = not self.show_heatmap
                elif event.key == pygame.K_p:
                    self.show_paths = not self.show_paths
                elif event.key == pygame.K_l:
                    self.show_los = not self.show_los
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Mouse wheel up
                    self.zoom *= 1.1
                elif event.button == 5:  # Mouse wheel down
                    self.zoom /= 1.1
        
        # Pan with arrow keys
        keys = pygame.key.get_pressed()
        pan_speed = 10
        if keys[pygame.K_LEFT]:
            self.offset_x += pan_speed
        if keys[pygame.K_RIGHT]:
            self.offset_x -= pan_speed
        if keys[pygame.K_UP]:
            self.offset_y += pan_speed
        if keys[pygame.K_DOWN]:
            self.offset_y -= pan_speed
        
        return True
    
    def draw_map(self):
        """Draw the base map geometry."""
        # Draw areas
        for area in self.map_data.get('map-areas', {}).values():
            rect = pygame.Rect(
                *self.world_to_screen(area['x'], area['y']),
                int(area['w'] * self.scale * self.zoom),
                int(area['h'] * self.scale * self.zoom)
            )
            color = self.colors.get(area.get('type', 'default'), (200, 200, 200))
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (0, 0, 0), rect, 1)
        
        # Draw walls
        for wall in self.map_data.get('walls', {}).values():
            rect = pygame.Rect(
                *self.world_to_screen(wall['x'], wall['y']),
                int(wall['w'] * self.scale * self.zoom),
                int(wall['h'] * self.scale * self.zoom)
            )
            pygame.draw.rect(self.screen, self.colors['wall'], rect)
        
        # Draw objects
        for obj in self.map_data.get('objects', {}).values():
            if isinstance(obj, dict):  # Skip non-dict entries like 'instructions'
                rect = pygame.Rect(
                    *self.world_to_screen(obj['x'], obj['y']),
                    int(obj['w'] * self.scale * self.zoom),
                    int(obj['h'] * self.scale * self.zoom)
                )
                pygame.draw.rect(self.screen, self.colors['object'], rect)
    
    def run(self):
        """Main visualization loop."""
        running = True
        while running:
            running = self.handle_input()
            
            # Clear screen
            self.screen.fill(self.colors['background'])
            
            # Draw visualization layers
            self.draw_grid()
            self.draw_elevation()
            self.draw_map()
            self.draw_heatmap()
            self.draw_paths()
            self.draw_line_of_sight()
            self.draw_debug_info()
            
            # Draw UI elements
            self.draw_ui()
            
            pygame.display.flip()
            self.clock.tick(60)
    
    def draw_ui(self):
        """Draw UI elements and controls help."""
        # Draw controls help
        help_text = [
            "Controls:",
            "G - Toggle Grid",
            "E - Toggle Elevation",
            "H - Toggle Heatmap",
            "P - Toggle Paths",
            "L - Toggle Line of Sight",
            "D - Toggle Debug Info",
            "Arrow Keys - Pan",
            "Mouse Wheel - Zoom",
            "ESC - Exit"
        ]
        
        y = 10
        for line in help_text:
            text = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(text, (self.width - text.get_width() - 10, y))
            y += 20
        
        # Draw current mode indicators
        modes = [
            ("Grid", self.show_grid),
            ("Elevation", self.show_elevation),
            ("Heatmap", self.show_heatmap),
            ("Paths", self.show_paths),
            ("LoS", self.show_los),
            ("Debug", self.show_debug)
        ]
        
        x = 10
        y = self.height - 30
        for mode, active in modes:
            color = (0, 255, 0) if active else (255, 0, 0)
            text = self.font.render(mode, True, color)
            self.screen.blit(text, (x, y))
            x += text.get_width() + 20

def visualize_map(map_data: Dict):
    """Create and run a map visualizer."""
    visualizer = MapVisualizer()
    visualizer.load_map(map_data)
    visualizer.run()

if __name__ == "__main__":
    # Example usage
    with open("example_map.json", "r") as f:
        map_data = json.load(f)
    visualize_map(map_data) 
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
import json
import random
import math
from app.simulation.models.map_pathfinding import NavigationMesh, PathFinder, CollisionDetector
try:
    import pygame
except ImportError:
    pygame = None

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.simulation.models.player import Player

@dataclass
class MapArea:
    """Represents an area in the game map with specific properties."""
    name: str             # Unique identifier for the area
    x: float              # X-coordinate of the area
    y: float              # Y-coordinate of the area
    width: float          # Width of the area
    height: float         # Height of the area
    elevation: float = 0  # Base elevation of the area
    area_type: str = ""   # Type of area (e.g., "site", "spawn", "mid")
    center: Tuple[float, float] = None  # Center coordinates, computed if not provided
    neighbors: List[str] = field(default_factory=list)  # Adjacent areas (by name) for pathfinding
    radius: float = 0.0   # Radius for circular representation
    is_plant_site: bool = False  # Whether spike can be planted here
    
    def __post_init__(self):
        """Initialize computed fields after constructor."""
        if self.center is None:
            self.center = (self.x + self.width / 2, self.y + self.height / 2)
    
    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if the area contains a point."""
        return (self.x <= x < self.x + self.width and 
                self.y <= y < self.y + self.height)

@dataclass
class MapLayout:
    name: str                   # Map name (often influenced by theme)
    theme: str                  # Thematic preset name (environment style)
    areas: List[MapArea] = field(default_factory=list)         # All zones/areas in the map
    walls: List[Dict[str, Tuple[float, float]]] = field(default_factory=list)  # Wall segments for occlusion
    attacker_spawns: List[Tuple[float, float]] = field(default_factory=list)   # Spawn points for attackers
    defender_spawns: List[Tuple[float, float]] = field(default_factory=list)   # Spawn points for defenders
    decorative_elements: List[Dict] = field(default_factory=list)   # Thematic props (type and position)
    default_plant_spots: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)  # Common plant positions
    orbs: List[Tuple[float, float]] = field(default_factory=list)   # Ultimate orb positions

    def to_dict(self) -> Dict:
        """Serialize map layout to a dictionary (for JSON saving or Round consumption)."""
        data = {
            "name": self.name,
            "theme": self.theme,
            "attacker_spawns": self.attacker_spawns,
            "defender_spawns": self.defender_spawns,
            "plant_sites": {},
            "walls": self.walls,
            "decorative_elements": self.decorative_elements,
            "zones": {},
            "default_plant_spots": self.default_plant_spots,
            "orbs": self.orbs
        }
        # Include each area's info. Mark bomb sites with center and radius.
        for area in self.areas:
            # Populate bomb site info for quick lookup
            if area.is_plant_site:
                site_key = area.name[0]  # e.g. "A Site" -> "A"
                data["plant_sites"][site_key] = {
                    "center": area.center, 
                    "radius": area.radius, 
                    "name": area.name
                }
            # Record general zone info (type and neighbors) for potential use in AI or debugging
            data["zones"][area.name] = {
                "type": area.area_type,
                "center": area.center,
                "neighbors": list(area.neighbors),
                "elevation": area.elevation,
                "cover_objects": area.cover_objects,
                "one_way_connections": area.one_way_connections
            }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'MapLayout':
        """Deserialize a MapLayout from a saved dictionary (reverse of to_dict)."""
        layout = cls(
            name=data.get("name", "Unknown"), 
            theme=data.get("theme", "Unknown"),
            default_plant_spots=data.get("default_plant_spots", {}),
            orbs=data.get("orbs", [])
        )
        # Reconstruct MapArea objects
        zones_info = data.get("zones", {})
        area_objs: Dict[str, MapArea] = {}
        for name, info in zones_info.items():
            area_objs[name] = MapArea(
                name=name,
                area_type=info.get("type", ""),
                center=tuple(info.get("center", (0.0, 0.0))),
                radius=info.get("radius", 0.0),
                is_plant_site=(info.get("type") == "site"),
                elevation=info.get("elevation", 0),
                cover_objects=info.get("cover_objects", []),
                one_way_connections=info.get("one_way_connections", [])
            )
        # Set up neighbors once all areas are created
        for name, info in zones_info.items():
            area = area_objs[name]
            for neigh_name in info.get("neighbors", []):
                if neigh_name in area_objs:
                    area.neighbors.append(neigh_name)
            layout.areas.append(area)
        # Restore spawns, walls, and decorations
        layout.attacker_spawns = [tuple(pt) for pt in data.get("attacker_spawns", [])]
        layout.defender_spawns = [tuple(pt) for pt in data.get("defender_spawns", [])]
        layout.walls = data.get("walls", [])
        layout.decorative_elements = data.get("decorative_elements", [])
        return layout

    def save_to_json(self, filepath: str) -> None:
        """Save this map layout to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load_from_json(cls, filepath: str) -> 'MapLayout':
        """Load a map layout from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def find_path(self, start_area: str, goal_area: str) -> List[str]:
        """Find a path between two zone names using BFS."""
        if start_area == goal_area:
            return [start_area]
        # Standard BFS traversal
        queue = [start_area]
        came_from: Dict[str, Optional[str]] = {start_area: None}
        while queue:
            current = queue.pop(0)
            if current == goal_area:
                break
            for neighbor in self.get_neighbors(current):
                if neighbor not in came_from:       # not visited
                    came_from[neighbor] = current
                    queue.append(neighbor)
        # Reconstruct path if target reached
        if goal_area not in came_from:
            return []  # no path found
        path = []
        node = goal_area
        while node is not None:
            path.append(node)
            node = came_from[node]
        return path[::-1]  # reverse to get start->...->goal

    def get_neighbors(self, area_name: str) -> List[str]:
        """Safe getter for neighbors of a zone by name."""
        for area in self.areas:
            if area.name == area_name:
                return area.neighbors
        return []
    
    def line_of_sight(self, p1: Tuple[float,float], p2: Tuple[float,float], smokes: Optional[List[Dict]] = None) -> bool:
        """Check if the line from p1 to p2 is clear (no walls or smoke blocking)."""
        # Check static walls
        for wall in self.walls:
            if self._line_segments_intersect(p1, p2, wall["start"], wall["end"]):
                return False
        # Check dynamic vision blockers (smokes)
        if smokes:
            for smoke in smokes:
                center = smoke.get("center");  rad = smoke.get("radius", 0)
                if center and rad:
                    if self._distance_point_to_line(center, p1, p2) <= rad:
                        return False
        return True

    def _line_segments_intersect(self, p1: Tuple[float,float], p2: Tuple[float,float], 
                               q1: Tuple[float,float], q2: Tuple[float,float]) -> bool:
        """Check if line segments p1p2 and q1q2 intersect."""
        # Calculate the orientation of three points
        def orientation(p: Tuple[float,float], q: Tuple[float,float], r: Tuple[float,float]) -> int:
            val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
            if val == 0:
                return 0  # Collinear
            return 1 if val > 0 else 2  # Clockwise or counterclockwise

        # Check if point q lies on segment pr
        def on_segment(p: Tuple[float,float], q: Tuple[float,float], r: Tuple[float,float]) -> bool:
            return (q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and
                    q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1]))

        # Find the four orientations needed for general and special cases
        o1 = orientation(p1, p2, q1)
        o2 = orientation(p1, p2, q2)
        o3 = orientation(q1, q2, p1)
        o4 = orientation(q1, q2, p2)

        # General case: different orientations
        if o1 != o2 and o3 != o4:
            return True

        # Special Cases: points are collinear
        if o1 == 0 and on_segment(p1, q1, p2): return True
        if o2 == 0 and on_segment(p1, q2, p2): return True
        if o3 == 0 and on_segment(q1, p1, q2): return True
        if o4 == 0 and on_segment(q1, p2, q2): return True

        return False

    def _distance_point_to_line(self, point: Tuple[float,float], a: Tuple[float,float], b: Tuple[float,float]) -> float:
        """Calculate shortest distance from point to line segment ab."""
        # Vector from a to b
        ab_x = b[0] - a[0]
        ab_y = b[1] - a[1]
        
        # Vector from a to point
        ap_x = point[0] - a[0]
        ap_y = point[1] - a[1]
        
        # Length of ab squared
        ab_sq = ab_x * ab_x + ab_y * ab_y
        
        # If the line segment has zero length, return distance to point a
        if ab_sq == 0:
            return math.sqrt(ap_x * ap_x + ap_y * ap_y)
        
        # Consider the line extending the segment, parameterized as a + t (b - a)
        # Project point onto the line by computing t
        t = (ap_x * ab_x + ap_y * ab_y) / ab_sq
        
        # If outside segment bounds, return distance to nearest endpoint
        if t < 0.0:
            return math.sqrt(ap_x * ap_x + ap_y * ap_y)
        elif t > 1.0:
            return math.sqrt((point[0] - b[0])**2 + (point[1] - b[1])**2)
        
        # Projection falls on the segment
        proj_x = a[0] + t * ab_x
        proj_y = a[1] + t * ab_y
        return math.sqrt((point[0] - proj_x)**2 + (point[1] - proj_y)**2)

    def visualize(self, save_path: Optional[str] = None) -> None:
        """Create a simple visualization of the map layout using matplotlib."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
        except ImportError:
            print("Matplotlib is required for visualization. Please install it with: pip install matplotlib")
            return

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Draw areas as circles with labels
        for area in self.areas:
            # Draw circle for area
            circle = plt.Circle(area.center, area.radius or 3.0, 
                              fill=False if not area.is_plant_site else True,
                              alpha=0.3 if area.is_plant_site else 1.0)
            ax.add_patch(circle)
            
            # Add area label
            plt.text(area.center[0], area.center[1], area.name,
                    horizontalalignment='center', verticalalignment='center')
            
            # Draw connections to neighbors
            for neighbor_name in area.neighbors:
                neighbor = next((a for a in self.areas if a.name == neighbor_name), None)
                if neighbor:
                    plt.plot([area.center[0], neighbor.center[0]],
                            [area.center[1], neighbor.center[1]], 'k--', alpha=0.3)

        # Draw walls
        for wall in self.walls:
            plt.plot([wall["start"][0], wall["end"][0]],
                    [wall["start"][1], wall["end"][1]], 'k-', linewidth=2)

        # Draw spawn points
        for spawn in self.attacker_spawns:
            plt.plot(spawn[0], spawn[1], 'ro', label='Attacker Spawn')
        for spawn in self.defender_spawns:
            plt.plot(spawn[0], spawn[1], 'bo', label='Defender Spawn')

        # Draw decorative elements
        for element in self.decorative_elements:
            plt.plot(element["position"][0], element["position"][1], 'g^',
                    label=f'Decoration ({element["type"]})')

        # Set equal aspect ratio and add title
        ax.set_aspect('equal')
        plt.title(f"{self.name} ({self.theme})")
        
        # Add legend (only once for each type)
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())

        # Set reasonable axis limits based on map dimensions
        all_x = [area.center[0] for area in self.areas]
        all_y = [area.center[1] for area in self.areas]
        margin = 20.0
        plt.xlim(min(all_x) - margin, max(all_x) + margin)
        plt.ylim(min(all_y) - margin, max(all_y) + margin)

        # Save or show
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()

class MapBoundary:
    """Represents a boundary in the map for collision detection."""
    
    def __init__(self, x: float, y: float, width: float, height: float, 
                 boundary_type: str = "wall", name: str = "", elevation: int = 0,
                 z: float = 0.0, height_z: float = 0.0):
        """Initialize a map boundary with position, size and type."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.boundary_type = boundary_type  # wall, object, stairs, etc.
        self.name = name
        self.elevation = elevation
        
        # Z-axis properties
        self.z = z                # Base z-coordinate (height from ground)
        self.height_z = height_z  # Height of the object in z-direction
    
    def as_rect(self, scale: float = 1.0) -> pygame.Rect:
        """Get this boundary as a Pygame rectangle for collision detection."""
        return pygame.Rect(
            self.x * scale, 
            self.y * scale, 
            self.width * scale, 
            self.height * scale
        )
    
    def contains_point(self, point_x: float, point_y: float, point_z: float = 0.0) -> bool:
        """Check if this boundary contains the given 3D point."""
        # Check x-y plane
        xy_contains = (self.x <= point_x <= self.x + self.width and
                       self.y <= point_y <= self.y + self.height)
        
        # Special-case: area boundaries enforce elevation
        if self.boundary_type == "area":
            # require the point to be at or above the base height
            return xy_contains and point_z >= self.z

        # If no height, only check x-y plane
        if self.height_z == 0:
            return xy_contains
        
        # Check z-axis
        z_contains = self.z <= point_z <= self.z + self.height_z
        
        return xy_contains and z_contains
    
    def collides_with_circle(self, center_x: float, center_y: float, radius: float, 
                             center_z: float = 0.0, is_3d_check: bool = False) -> bool:
        """
        Check if this boundary collides with a circle (player).
        For 3D collision, use is_3d_check=True and provide center_z.
        """
        # Find the closest point on the rectangle to the circle center
        closest_x = max(self.x, min(center_x, self.x + self.width))
        closest_y = max(self.y, min(center_y, self.y + self.height))
        
        # Calculate the distance from the closest point to the circle center in the XY plane
        distance_x = center_x - closest_x
        distance_y = center_y - closest_y
        
        # For 2D collision check (backward compatibility)
        if not is_3d_check:
            return (distance_x * distance_x + distance_y * distance_y) < (radius * radius)
        
        # For 3D collision, we need to check z-axis too
        # If the object has no height, we only check if player's bottom is below or touching the object's z
        if self.height_z == 0:
            # Special case: if boundary is the floor (z=0), player is always touching or above
            if self.z == 0:
                return (distance_x * distance_x + distance_y * distance_y) < (radius * radius)
            
            # Other flat surfaces: check if player is at the same z-level
            z_collision = abs(center_z - self.z) < radius
            return z_collision and (distance_x * distance_x + distance_y * distance_y) < (radius * radius)
        
        # For 3D objects with height
        # Find closest z-point
        closest_z = max(self.z, min(center_z, self.z + self.height_z))
        distance_z = center_z - closest_z
        
        # Check if 3D distance is less than the radius
        return (distance_x * distance_x + distance_y * distance_y + distance_z * distance_z) < (radius * radius)

class RampBoundary(MapBoundary):
    """Represents a ramp boundary with elevation change in a specific direction."""
    def __init__(self, name: str, x: float, y: float, width: float, height: float, 
                 z: float, height_z: float, direction: str):
        """
        Initialize a ramp boundary.
        
        Args:
            name: Unique identifier for the boundary
            x, y: Position coordinates
            width, height: Size of the boundary
            z: Base elevation
            height_z: Height of the ramp (z + height_z = top elevation)
            direction: Direction of the ramp ("north", "south", "east", "west")
                       Indicates which side is higher: north = north side is higher
        """
        super().__init__(x, y, width, height, "ramp", name, 0, z, height_z)
        self.direction = direction
        
    def get_elevation_at_point(self, x: float, y: float) -> float:
        """Get the elevation at a specific point on the ramp."""
        if not (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height):
            return 0.0
            
        # Calculate relative position on the ramp (0 to 1)
        if self.direction == "north":
            # North side is higher
            rel_pos = (y - self.y) / self.height
            return self.z + rel_pos * self.height_z
        elif self.direction == "south":
            # South side is higher
            rel_pos = (y - self.y) / self.height
            return self.z + (1 - rel_pos) * self.height_z
        elif self.direction == "east":
            # East side is higher
            rel_pos = (x - self.x) / self.width
            return self.z + rel_pos * self.height_z
        elif self.direction == "west":
            # West side is higher
            rel_pos = (x - self.x) / self.width
            return self.z + (1 - rel_pos) * self.height_z
        
        return self.z

class StairsBoundary(MapBoundary):
    """Represents a stairs boundary with discrete elevation changes."""
    def __init__(self, name: str, x: float, y: float, width: float, height: float, 
                 z: float, height_z: float, direction: str, steps: int = 5):
        """
        Initialize a stairs boundary.
        
        Args:
            name: Unique identifier for the boundary
            x, y: Position coordinates
            width, height: Size of the boundary
            z: Base elevation
            height_z: Total height of the stairs
            direction: Direction of the stairs ("north", "south", "east", "west")
            steps: Number of steps in the staircase
        """
        super().__init__(x, y, width, height, "stairs", name, 0, z, height_z)
        self.direction = direction
        self.steps = max(2, steps)  # Minimum 2 steps
        self.step_height = height_z / self.steps
        
    def get_elevation_at_point(self, x: float, y: float) -> float:
        """Get the elevation at a specific point on the stairs."""
        if not (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height):
            return 0.0
            
        # Calculate which step the point is on
        if self.direction in ["north", "south"]:
            # Steps run along y-axis
            length = self.height
            pos = y - self.y
            if self.direction == "north":
                pos = length - pos  # Flip for north direction
        else:
            # Steps run along x-axis
            length = self.width
            pos = x - self.x
            if self.direction == "west":
                pos = length - pos  # Flip for west direction
                
        # Calculate step number
        step_length = length / self.steps
        step_num = min(self.steps - 1, int(pos / step_length))
        
        # Return elevation for this step
        return self.z + step_num * self.step_height

class Map:
    """Represents a game map with boundaries and areas."""
    
    def __init__(self, name: str = "", width: int = 100, height: int = 100):
        """
        Initialize a new map.
        
        Args:
            name: Name of the map
            width: Width of the map in game units
            height: Height of the map in game units
        """
        self.name = name
        self.width = width
        self.height = height
        self.areas = {}               # Areas by name
        self.boundaries = {}          # All boundaries (walls, objects, ramps, stairs, etc.)
        self.walls = {}               # Walls by name
        self.objects = {}             # Objects (boxes, etc.) by name
        self.ramps = {}               # Ramps by name
        self.stairs = {}              # Stairs by name
        self.plant_locations = {}     # Bomb plant locations by site name (A, B, C)
        self.bomb_sites = {}          # Bomb sites by name (A, B, C)
        self.attacker_spawns = []     # List of attacker spawn points
        self.defender_spawns = []     # List of defender spawn points
        # Dynamic effects currently active on this map
        self._active_effects: List[Dict] = []

        self.nav_mesh = None
        self.pathfinder = None
        self.collision_detector = None
    
    @classmethod
    def from_json(cls, data) -> 'Map':
        """Load a map from a dictionary or a file path."""
        import os
        import json
        if isinstance(data, str):
            # Assume it's a file path
            if not os.path.exists(data):
                raise FileNotFoundError(f"Map file not found: {data}")
            with open(data, 'r') as f:
                data = json.load(f)
        # Now data is a dict
        metadata = data.get("metadata", {})
        map_size = metadata.get("map-size", [32, 32])
        name = metadata.get("name", "Unknown Map")
        game_map = cls(name, map_size[0], map_size[1])
        # Load map areas
        for name, area_data in data.get("map-areas", {}).items():
            game_map.areas[name] = MapBoundary(
                area_data["x"], area_data["y"], 
                area_data["w"], area_data["h"],
                "area", name, area_data.get("elevation", 0),
                area_data.get("z", 0), area_data.get("height_z", 0)
            )
        # Load walls
        for name, wall_data in data.get("walls", {}).items():
            game_map.walls[name] = MapBoundary(
                wall_data["x"], wall_data["y"], 
                wall_data["w"], wall_data["h"],
                "wall", name, wall_data.get("elevation", 0),
                wall_data.get("z", 0), wall_data.get("height_z", 10.0)
            )
        # Load objects
        for name, obj_data in data.get("objects", {}).items():
            if name != "instructions":
                game_map.objects[name] = MapBoundary(
                    obj_data["x"], obj_data["y"], 
                    obj_data["w"], obj_data["h"],
                    "object", name, obj_data.get("elevation", 0),
                    obj_data.get("z", 0), obj_data.get("height_z", 2.0)
                )
        # Load stairs
        for name, stair_data in data.get("stairs", {}).items():
            game_map.stairs[name] = StairsBoundary(name, stair_data["x"], stair_data["y"], stair_data["w"], stair_data["h"]
                                                   , stair_data["z"], stair_data["height_z"], stair_data["direction"], stair_data["steps"])
        # Load ramps
        for name, ramp_data in data.get("ramps", {}).items():
            game_map.ramps[name] = RampBoundary(name, ramp_data["x"], ramp_data["y"], ramp_data["w"], ramp_data["h"]
                                                , ramp_data["z_start"], ramp_data["z_end"], ramp_data["direction"])
        # Load bomb sites
        bomb_sites_data = data.get("bomb-sites", {})
        if isinstance(bomb_sites_data, dict):
            for name, site_data in bomb_sites_data.items():
                game_map.bomb_sites[name] = MapBoundary(
                    site_data["x"], site_data["y"], 
                    site_data["w"], site_data["h"],
                    "bomb-site", name, site_data.get("elevation", 0),
                    site_data.get("z", 0), site_data.get("height_z", 0.0)
                )
        # If bomb-sites is a list (legacy), do nothing (handled elsewhere)

        game_map.nav_mesh = cls.create_navigation_mesh(game_map)
        game_map.collision_detector = CollisionDetector(game_map.nav_mesh)
        game_map.pathfinder = PathFinder(game_map.nav_mesh)
    
        return game_map

    def create_navigation_mesh(self) -> NavigationMesh:
        """Create a navigation mesh for this map."""
        nav_mesh = NavigationMesh(self.width, self.height)
        
        # Add walls as obstacles
        for wall in self.walls.values():
            nav_mesh.add_obstacle(
                wall.x, wall.y, wall.width, wall.height,
                wall.z, wall.height_z
            )
        
        # Add objects as obstacles
        for obj in self.objects.values():
            nav_mesh.add_obstacle(
                obj.x, obj.y, obj.width, obj.height,
                obj.z, obj.height_z
            )
        
        # Set area elevations
        for area in self.areas.values():
            nav_mesh.set_elevation(
                area.x, area.y, area.width, area.height,
                area.elevation
            )
        
        # Set stairs elevations
        for stair in self.stairs.values():
            nav_mesh.set_stairs_elevation(
                stair.x, stair.y, stair.width, stair.height,
                stair.z, stair.z + stair.height_z,
                stair.direction
            )
        
        return nav_mesh
            
    
    def get_area_at_position(self, x: float, y: float, z: float = 0.0) -> Optional[str]:
        """Get the name of the area at the given position, preferring higher-elevation areas first."""
        # Sort areas by their base z (elevation) descending so elevated zones take precedence
        for name, area in sorted(self.areas.items(), key=lambda item: item[1].z, reverse=True):
            if area.contains_point(x, y, z):
                return name
        return None
    
    def get_elevation_at_position(self, x: float, y: float) -> float:
        """
        Get the elevation (z-coordinate) at a given position on the map.
        Takes into account areas, ramps, and stairs.
        
        Args:
            x: X-coordinate of the position
            y: Y-coordinate of the position
            
        Returns:
            float: The elevation value at the position
        """
        # Start with default elevation 0
        elevation = 0.0
        
        # Check areas first (consider elevated areas first)
        for area in sorted(self.areas.values(), key=lambda a: a.elevation, reverse=True):
            if area.x <= x < area.x + area.width and area.y <= y < area.y + area.height:
                elevation = area.elevation
                break
        
        # Check for ramps directly in the ramps collection
        for ramp in self.ramps.values():
            if ramp.x <= x < ramp.x + ramp.width and ramp.y <= y < ramp.y + ramp.height:
                return ramp.get_elevation_at_point(x, y)
        # Check for stairs directly in the stairs collection
        for stair in self.stairs.values():
            if stair.x <= x < stair.x + stair.width and stair.y <= y < stair.y + stair.height:
                return stair.get_elevation_at_point(x, y)
        # Override with walls/objects elevation if higher
        for boundary in list(self.walls.values()) + list(self.objects.values()):
            if (boundary.x <= x < boundary.x + boundary.width and 
                boundary.y <= y < boundary.y + boundary.height and 
                boundary.z > elevation):
                elevation = boundary.z
        return elevation
    
    def is_within_bomb_site(self, x: float, y: float, z: float = 0.0) -> Optional[str]:
        """Check if a position is within a bomb site."""
        for name, site in self.bomb_sites.items():
            if site.contains_point(x, y, z):
                return name
        return None
    
    def is_valid_position(self, x: float, y: float, z: float = 0.0, radius: float = 0.5, height: float = 1.0) -> bool:
        """Check if a position is valid (within map and not colliding with obstacles)."""
        # Check if position is within map bounds
        if x - radius < 0 or x + radius > self.width or y - radius < 0 or y + radius > self.height:
            return False
        
        # Prevent walking under elevated areas: if xy is in an area's footprint but below its base height
        for area in self.areas.values():
            if (area.x <= x <= area.x + area.width and
                area.y <= y <= area.y + area.height and
                z < area.elevation):
                # allow if on a ramp or stair surface at this position
                on_surface = any(ramp.contains_point(x, y, z) for ramp in self.ramps.values())
                if on_surface:
                    continue
                on_surface = any(stair.contains_point(x, y, z) for stair in self.stairs.values())
                if on_surface:
                    continue
                return False
        
        # Check if position is within any valid area by elevation
        if not any(area.contains_point(x, y, z) for area in self.areas.values()):
            return False
        
        # Check collision with walls
        for wall in self.walls.values():
            if wall.collides_with_circle(x, y, radius, z, is_3d_check=True):
                return False
        
        # Check collision with objects (enforce 3D clearance for underpasses)
        for obj in self.objects.values():
            # If the object has height, check if player's body (from z to z+height) overlaps with the object
            if obj.height_z > 0:
                player_bottom = z
                player_top = z + height
                obj_bottom = obj.z
                obj_top = obj.z + obj.height_z
                # If XY overlaps and vertical ranges overlap, collision
                xy_overlap = (obj.x <= x <= obj.x + obj.width and obj.y <= y <= obj.y + obj.height)
                z_overlap = not (player_top <= obj_bottom or player_bottom >= obj_top)
                if xy_overlap and z_overlap:
                    return False
            else:
                if obj.collides_with_circle(x, y, radius, z, is_3d_check=True):
                    return False
        
        return True
    
    def can_move(self, start_x: float, start_y: float, start_z: float, 
                end_x: float, end_y: float, end_z: float, 
                radius: float = 0.5) -> bool:
        """Check if a player can move from start to end position in 3D space."""
        # Get starting and ending areas
        start_area = self.get_area_at_position(start_x, start_y, start_z)
        end_area = self.get_area_at_position(end_x, end_y, end_z)
        # Must be in a valid area or on a ramp/stair surface
        if not start_area or not end_area:
            # allow if moving onto or off of a ramp or stair
            on_surface = any(ramp.contains_point(start_x, start_y, start_z) or ramp.contains_point(end_x, end_y, end_z)
                              for ramp in self.ramps.values())
            if not on_surface:
                on_surface = any(stair.contains_point(start_x, start_y, start_z) or stair.contains_point(end_x, end_y, end_z)
                                  for stair in self.stairs.values())
            if not on_surface:
                return False
        
        # Block walking onto higher-elevation areas unless on a ramp or stair
        start_map_elev = self.get_elevation_at_position(start_x, start_y)
        end_map_elev = self.get_elevation_at_position(end_x, end_y)
        if end_map_elev > start_map_elev:
            # Allow elevation change if on ramp or stair (entering or exiting), or if elevations match
            on_surface = False
            for ramp in self.ramps.values():
                if ramp.contains_point(start_x, start_y, start_map_elev) or \
                   ramp.contains_point(end_x, end_y, end_map_elev):
                    on_surface = True
                    break
            if not on_surface:
                for stair in self.stairs.values():
                    if stair.contains_point(start_x, start_y, start_map_elev) or \
                       stair.contains_point(end_x, end_y, end_map_elev):
                        on_surface = True
                        break
            # Also allow if elevations match exactly (e.g. ramp to area)
            if not on_surface and abs(end_map_elev - start_map_elev) > 1e-4:
                return False
        
        # Check if path crosses any obstacles
        # For simplicity, we'll just check several points along the path
        steps = 10
        for i in range(0, steps + 1):
            t = i / steps
            check_x = start_x + t * (end_x - start_x)
            check_y = start_y + t * (end_y - start_y)
            check_z = start_z + t * (end_z - start_z)
            
            if not self.is_valid_position(check_x, check_y, check_z, radius):
                return False
        
        return True

    def raycast(self, origin: Tuple[float, float, float], direction: Tuple[float, float, float], max_range: float = 50.0) -> Tuple[Optional[float], Optional[Tuple[float, float, float]], Optional[MapBoundary]]:
        """
        Perform an exact 3D raycast against walls and objects.
        Returns (t, hit_point, hit_object) where t is the distance along the ray, hit_point is the 3D point, and hit_object is a MapBoundary or None if miss.
        """
        # Unpack origin and direction
        ox, oy, oz = origin
        dx, dy, dz = direction
        nearest_t = max_range
        hit_obj = None
        hit_point = None
        # Check AABB intersections for walls and objects
        for boundary in list(self.walls.values()) + list(self.objects.values()):
            # AABB bounds
            mn_x, mn_y, mn_z = boundary.x, boundary.y, boundary.z
            mx_x, mx_y, mx_z = boundary.x + boundary.width, boundary.y + boundary.height, boundary.z + boundary.height_z
            tmin, tmax = 0.0, max_range
            # X slab
            if abs(dx) < 1e-10:
                # Ray is parallel to slab. No hit if origin not within slab
                if ox < mn_x or ox > mx_x:
                    continue
            else:
                # Compute intersection t value of ray with near and far plane of slab
                t1 = (mn_x - ox) / dx
                t2 = (mx_x - ox) / dx
                if t1 > t2:
                    t1, t2 = t2, t1  # Swap so t1 is intersection with near plane
                
                # Update tmin and tmax
                tmin = max(tmin, t1)
                tmax = min(tmax, t2)
                if tmin > tmax:
                    continue  # No intersection with this boundary
            
            # Y slab
            if abs(dy) < 1e-10:
                # Ray is parallel to slab. No hit if origin not within slab
                if oy < mn_y or oy > mx_y:
                    continue
            else:
                # Compute intersection t value of ray with near and far plane of slab
                t1 = (mn_y - oy) / dy
                t2 = (mx_y - oy) / dy
                if t1 > t2:
                    t1, t2 = t2, t1  # Swap so t1 is intersection with near plane
                
                # Update tmin and tmax
                tmin = max(tmin, t1)
                tmax = min(tmax, t2)
                if tmin > tmax:
                    continue  # No intersection with this boundary
            
            # Z slab
            if abs(dz) < 1e-10:
                # Ray is parallel to slab. No hit if origin not within slab
                if oz < mn_z or oz > mx_z:
                    continue
            else:
                # Compute intersection t value of ray with near and far plane of slab
                t1 = (mn_z - oz) / dz
                t2 = (mx_z - oz) / dz
                if t1 > t2:
                    t1, t2 = t2, t1  # Swap so t1 is intersection with near plane
                
                # Update tmin and tmax
                tmin = max(tmin, t1)
                tmax = min(tmax, t2)
                if tmin > tmax:
                    continue  # No intersection with this boundary
            
            # If we reach here, ray intersects all 3 slabs. If t is valid, we have a hit.
            if 0.0 <= tmin < nearest_t:
                nearest_t = tmin
                hit_obj = boundary
                hit_point = (ox + dx * tmin, oy + dy * tmin, oz + dz * tmin)
        # Return the nearest hit time, point, and object
        if hit_point is None:
            return None, None, None
        return nearest_t, hit_point, hit_obj

    def cast_bullet(self, origin: Tuple[float, float, float], direction: Tuple[float, float, float], max_range: float, players: List[Player]):
        """
        Raycast against environment and a list of players. Returns (hit_point, hit_boundary, hit_player).
        """
        # Environment hit
        t_env, point_env, obj_env = self.raycast(origin, direction, max_range)
        nearest_t = t_env if t_env is not None else max_range
        hit_player = None
        # Check players
        for player in players:
            t_player = player.intersect_ray(origin, direction)
            if t_player is not None and t_player < nearest_t:
                nearest_t = t_player
                hit_player = player
        # Compute hit point
        hit_point = (origin[0] + direction[0] * nearest_t,
                     origin[1] + direction[1] * nearest_t,
                     origin[2] + direction[2] * nearest_t)
        # Return hit info
        if hit_player:
            return hit_point, None, hit_player
        if point_env is not None:
            return hit_point, obj_env, None
        # Miss
        return hit_point, None, None

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float], radius: float = 0.5, height: float = 1.0) -> List[Tuple[float, float]]:
        """Find a path on the map grid from start to goal using BFS."""
        import collections
        start_cell = (int(start[0]), int(start[1]))
        end_cell = (int(goal[0]), int(goal[1]))
        frontier = collections.deque([start_cell])
        came_from = {start_cell: None}
        while frontier:
            current = frontier.popleft()
            if current == end_cell:
                break
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                x, y = neighbor
                if 0 <= x < self.width and 0 <= y < self.height and neighbor not in came_from:
                    # Check if this cell is passable
                    if self.is_valid_position(x + 0.5, y + 0.5, 0.0, radius, height):
                        came_from[neighbor] = current
                        frontier.append(neighbor)
        # Reconstruct path if found
        if end_cell not in came_from:
            return []
        path = []
        curr = end_cell
        while curr is not None:
            path.append((curr[0] + 0.5, curr[1] + 0.5))
            curr = came_from[curr]
        path.reverse()
        return path

    def find_path_3d(self, start: Tuple[float, float, float], goal: Tuple[float, float, float], max_jump_height: float = 1.5, radius: float = 0.5, height: float = 1.0) -> List[Tuple[float, float, float]]:
        """Find a path considering jumping and elevation changes in 3D using BFS."""
        import collections
        # Extract start and goal coordinates
        start_x, start_y, start_z = start
        goal_x, goal_y, goal_z = goal
        # Adjust goal Z to match actual terrain elevation
        actual_goal_z = self.get_elevation_at_position(goal_x, goal_y)
        goal_z = actual_goal_z
        # Convert to discrete grid cells
        start_cell = (int(start_x), int(start_y), start_z)
        goal_cell = (int(goal_x), int(goal_y), goal_z)
        # Early exit if start invalid
        if not self.is_valid_position(start_cell[0], start_cell[1], start_cell[2], radius, height):
            return []
        # Validate or adjust goal position
        if not self.is_valid_position(goal_cell[0], goal_cell[1], goal_cell[2], radius, height):
            found_alt = False
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    tx = goal_cell[0] + dx
                    ty = goal_cell[1] + dy
                    tz = self.get_elevation_at_position(tx, ty)
                    if self.is_valid_position(tx, ty, tz, radius, height):
                        goal_cell = (tx, ty, tz)
                        goal_z = tz
                        found_alt = True
                        break
                if found_alt:
                    break
            if not found_alt:
                return []
        # BFS setup
        frontier = collections.deque([start_cell])
        came_from = {start_cell: None}
        iterations = 0
        max_iterations = 5000
        # Perform BFS
        while frontier and iterations < max_iterations:
            iterations += 1
            cx, cy, cz = frontier.popleft()
            # Goal reached?
            if (cx, cy) == (goal_cell[0], goal_cell[1]) and abs(cz - goal_z) < 0.1:
                break
            # Current elevation
            current_elev = self.get_elevation_at_position(cx, cy)
            # Explore neighbors
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)]:
                nx, ny = cx + dx, cy + dy
                # Bounds check
                if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                    continue
                nelev = self.get_elevation_at_position(nx, ny)
                # Check if standing on stairs or ramp at current
                on_stairs = any(st.x <= cx <= st.x + st.width and st.y <= cy <= st.y + st.height for st in self.stairs.values())
                on_ramp   = any(rp.x <= cx <= rp.x + rp.width and rp.y <= cy <= rp.y + rp.height for rp in self.ramps.values())
                # Determine neighbor z
                if abs(nelev - cz) < 0.1:
                    nz = nelev
                elif nelev < cz:
                    nz = nelev  # always allow going down
                else:
                    # going up
                    climb = max_jump_height
                    if on_stairs or on_ramp:
                        climb = 3.0
                    if nelev - cz > climb:
                        continue
                    nz = nelev
                neighbor = (nx, ny, nz)
                # Validate and enqueue
                if neighbor not in came_from and self.is_valid_position(nx, ny, nz, radius, height):
                    came_from[neighbor] = (cx, cy, cz)
                    frontier.append(neighbor)
        # Check for failure
        finish_key = (goal_cell[0], goal_cell[1], goal_cell[2])
        if iterations >= max_iterations or finish_key not in came_from:
            return []
        # Reconstruct the path
        path = []
        node = finish_key
        while node is not None:
            path.append((node[0] + 0.5, node[1] + 0.5, node[2]))
            node = came_from[node]
        path.reverse()
        return path

    # Add these methods to the Map class
    def add_area(self, area: MapArea) -> None:
        """Add an area to the map."""
        self.areas[area.name] = area
    
    def add_boundary(self, boundary) -> None:
        """
        Add a boundary to the map.
        
        This method handles different boundary types including:
        - Regular MapBoundary objects
        - RampBoundary objects
        - StairsBoundary objects
        """
        self.boundaries[boundary.name] = boundary
        
        # Update specific collections based on boundary type
        if boundary.boundary_type == "wall":
            self.walls[boundary.name] = boundary
        elif boundary.boundary_type == "object":
            self.objects[boundary.name] = boundary
        elif boundary.boundary_type == "ramp" or isinstance(boundary, RampBoundary):
            self.ramps[boundary.name] = boundary
        elif boundary.boundary_type == "stairs" or isinstance(boundary, StairsBoundary):
            self.stairs[boundary.name] = boundary

    def set_elevation_at_position(self, x: float, y: float, elevation: float) -> None:
        """
        Set the elevation at a specific x,y position on the map.
        
        This is primarily used for initialization and special terrain features.
        
        Args:
            x: X-coordinate of the position
            y: Y-coordinate of the position
            elevation: The elevation value to set
        """
        # Currently we don't store a full elevation grid
        # This is used for initialization by special map creation functions
        
        # Create a small invisible area to mark this elevation
        area_name = f"elevation_{x}_{y}"
        
        # Check if this position is already within an area
        for area in self.areas.values():
            if (area.x <= x < area.x + area.width and 
                area.y <= y < area.y + area.height):
                # Update the existing area's elevation
                area.elevation = elevation
                return
        
        # If no existing area, create a small marker area
        marker_area = MapArea(area_name, x, y, 1, 1, elevation)
        self.add_area(marker_area)

    def calculate_player_fov(self, source, all_players: List['Player'], 
                           fov_angle: float = 110.0, max_distance: float = 50.0) -> List['Player']:
        """
        Calculate which players are visible within a source's field of vision.
        Args:
            source: The object whose FOV we're calculating (must have .location, may have .direction)
            all_players: List of all players in the game
            fov_angle: The field of view angle in degrees (default 110°)
            max_distance: Maximum distance a player can see
        Returns:
            List of players visible to the given source
        """
        visible_players = []
        
        # Skip calculation if source is not alive (if it has that attribute)
        if hasattr(source, 'alive') and not getattr(source, 'alive', True):
            return visible_players
        
        # Use direction if present, else default to 0 (facing right)
        direction_deg = getattr(source, 'direction', 0)
        direction_rad = math.radians(direction_deg)
        facing_dir = (math.cos(direction_rad), math.sin(direction_rad), 0)
        half_fov_rad = math.radians(fov_angle / 2)
        px, py, pz = source.location
        
        for other in all_players:
            # Skip self or dead players
            if hasattr(source, 'id') and hasattr(other, 'id') and other.id == source.id:
                continue
            if hasattr(other, 'alive') and not other.alive:
                continue
            
            ox, oy, oz = other.location
            to_other = (ox - px, oy - py, oz - pz)
            distance = math.sqrt(to_other[0]**2 + to_other[1]**2 + to_other[2]**2)
            if distance > max_distance:
                continue
            if distance > 0:
                to_other_normalized = (to_other[0]/distance, to_other[1]/distance, to_other[2]/distance)
            else:
                continue
            dot_product = (facing_dir[0] * to_other_normalized[0] + 
                           facing_dir[1] * to_other_normalized[1] + 
                           facing_dir[2] * to_other_normalized[2])
            cos_half_fov = math.cos(half_fov_rad)
            if dot_product >= cos_half_fov:
                hit_distance, hit_point, hit_object = self.raycast(
                    source.location, 
                    to_other_normalized, 
                    distance
                )
                vision_blocked_by_smoke = False
                utility_active = getattr(source, 'utility_active', [])
                _active_effects = getattr(self, '_active_effects', [])
                for effect in utility_active + _active_effects:
                    if effect.get("type") == "smoke":
                        smoke_center = effect.get("position")
                        smoke_radius = effect.get("radius", 3.0)
                        if smoke_center:
                            sx, sy = smoke_center[0], smoke_center[1]
                            ax, ay = source.location[0], source.location[1]
                            bx, by = other.location[0], other.location[1]
                            dx_line = bx - ax
                            dy_line = by - ay
                            if dx_line == 0 and dy_line == 0:
                                dist = math.hypot(sx - ax, sy - ay)
                            else:
                                t = ((sx - ax) * dx_line + (sy - ay) * dy_line) / (dx_line*dx_line + dy_line*dy_line)
                                t = max(0.0, min(1.0, t))
                                proj_x = ax + t * dx_line
                                proj_y = ay + t * dy_line
                                dist = math.hypot(sx - proj_x, sy - proj_y)
                            if dist <= smoke_radius:
                                vision_blocked_by_smoke = True
                                break
                if (hit_distance is None or hit_distance >= distance) and not vision_blocked_by_smoke:
                    visible_players.append(other)
                    # Check if other player is looking back (for flash effects)
                    other_direction_rad = math.radians(getattr(other, 'direction', 0))
                    other_facing = (math.cos(other_direction_rad), math.sin(other_direction_rad), 0)
                    to_player = (-to_other[0], -to_other[1], -to_other[2])
                    if distance > 0:
                        to_player_normalized = (to_player[0]/distance, to_player[1]/distance, to_player[2]/distance)
                        looking_back_dot = (other_facing[0] * to_player_normalized[0] +
                                           other_facing[1] * to_player_normalized[1] +
                                           other_facing[2] * to_player_normalized[2])
                        other.is_looking_at_player = (looking_back_dot >= cos_half_fov)
        return visible_players

    def update_player_visibility(self, players: List['Player']):
        """
        Clear and update each player's visible_enemies based on FOV calculations.
        """
        # First, clear all players' visible_enemies
        for player in players:
            player.visible_enemies.clear()

        # Then compute and append visible enemies for each player
        for player in players:
            visible = self.calculate_player_fov(player, players)
            for other in visible:
                if other.team_id != player.team_id:
                    player.visible_enemies.append(other.id)

    def add_effect(self, effect_type: str, position: Tuple[float, float, float], 
                 radius: float, duration: float, owner_id: str = None):
        """
        Add a dynamic effect to the map (smoke, molly, etc.)
        
        Args:
            effect_type: Type of effect ("smoke", "molly", etc.)
            position: 3D position of effect
            radius: Radius of effect
            duration: How long effect lasts (seconds)
            owner_id: ID of player who created the effect
        """
        self._active_effects.append({
            "type": effect_type,
            "position": position,
            "radius": radius,
            "duration": duration,
            "start_time": 0,  # Will be set by simulation
            "owner_id": owner_id
        })
        
    def update_effects(self, current_time: float):
        """
        Update active effects, removing expired ones.
        
        Args:
            current_time: Current simulation time
        """
        self._active_effects = [
            effect for effect in self._active_effects
            if effect.get("start_time", 0) + effect.get("duration", 0) > current_time
        ]

class MapVisualizer:
    """Interactive map visualizer using Pygame library."""
    
    def __init__(self, map_file: str, width: int = 1200, height: int = 900, scale: float = 20):
        """Initialize the visualizer with a map JSON file."""
        # Load map data from JSON
        with open(map_file, 'r') as f:
            self.map_data = json.load(f)
        
        self.width = width
        self.height = height
        self.scale = scale
        
        # Extract map properties
        self.map_size = self.map_data["metadata"]["map-size"]
        self.map_width = self.map_size[0] * scale
        self.map_height = self.map_size[1] * scale
        
        # Color schemes for different area types
        self.colors = {
            "default": (200, 200, 200),      # Gray for default areas
            "t-spawn": (200, 255, 200),      # Light green for attacker spawn
            "ct-spawn": (200, 200, 255),     # Light blue for defender spawn
            "a-site": (255, 200, 200),       # Light red for A site
            "b-site": (255, 255, 200),       # Light yellow for B site
            "mid": (220, 220, 255),          # Light purple for mid
            "wall": (80, 80, 80),            # Dark gray for walls
            "object": (150, 120, 100),       # Brown for objects
            "stairs": (180, 180, 220),       # Light blue-gray for stairs
            "catwalk": (200, 255, 255),      # Light cyan for elevated areas
            "bomb-site": (0, 0, 0),          # Black for bomb sites
            "border": (50, 50, 50),          # Dark gray for border
        }
        
        # Setup collision meshes
        self.setup_collision_meshes()
    
    def setup_collision_meshes(self):
        """Setup collision detection meshes for map boundaries and objects."""
        self.area_boundaries = {}
        self.wall_boundaries = {}
        self.object_boundaries = {}
        self.stair_boundaries = {}
        self.bomb_site_boundaries = {}
        
        # Process map areas
        for name, area in self.map_data.get("map-areas", {}).items():
            self.area_boundaries[name] = pygame.Rect(
                area["x"] * self.scale, 
                area["y"] * self.scale, 
                area["w"] * self.scale, 
                area["h"] * self.scale
            )
        
        # Process walls
        for name, wall in self.map_data.get("walls", {}).items():
            self.wall_boundaries[name] = pygame.Rect(
                wall["x"] * self.scale, 
                wall["y"] * self.scale, 
                wall["w"] * self.scale, 
                wall["h"] * self.scale
            )
        
        # Process objects
        for name, obj in self.map_data.get("objects", {}).items():
            if name != "instructions":  # Skip instruction entries
                self.object_boundaries[name] = pygame.Rect(
                    obj["x"] * self.scale, 
                    obj["y"] * self.scale, 
                    obj["w"] * self.scale, 
                    obj["h"] * self.scale
                )
        
        # Process stairs
        for name, stair in self.map_data.get("stairs", {}).items():
            self.stair_boundaries[name] = pygame.Rect(
                stair["x"] * self.scale, 
                stair["y"] * self.scale, 
                stair["w"] * self.scale, 
                stair["h"] * self.scale
            )
            
        # Process bomb sites
        for name, site in self.map_data.get("bomb-sites", {}).items():
            self.bomb_site_boundaries[name] = pygame.Rect(
                site["x"] * self.scale, 
                site["y"] * self.scale, 
                site["w"] * self.scale, 
                site["h"] * self.scale
            )
        
        # Also create a Map object for collision detection
        map_size = self.map_data["metadata"]["map-size"]
        self.game_map = Map(self.map_data["metadata"]["name"], map_size[0], map_size[1])
        
        # Add boundaries to the Map
        for name, area in self.map_data.get("map-areas", {}).items():
            self.game_map.areas[name] = MapBoundary(
                area["x"], area["y"], area["w"], area["h"], "area", name, area.get("elevation", 0),
                area.get("z", 0), area.get("height_z", 0)
            )
        
        for name, wall in self.map_data.get("walls", {}).items():
            self.game_map.walls[name] = MapBoundary(
                wall["x"], wall["y"], wall["w"], wall["h"], "wall", name, wall.get("elevation", 0),
                wall.get("z", 0), wall.get("height_z", 3.0)  # Default wall height
            )
        
        for name, obj in self.map_data.get("objects", {}).items():
            if name != "instructions":
                self.game_map.objects[name] = MapBoundary(
                    obj["x"], obj["y"], obj["w"], obj["h"], "object", name, obj.get("elevation", 0),
                    obj.get("z", 0), obj.get("height_z", 1.0)  # Default object height
                )
        
        for name, stair in self.map_data.get("stairs", {}).items():
            self.game_map.stairs[name] = MapBoundary(
                stair["x"], stair["y"], stair["w"], stair["h"], "stairs", name, stair.get("elevation", 0),
                stair.get("z", 0), stair.get("height_z", 0.5)  # Default stair height
            )
        
        for name, site in self.map_data.get("bomb-sites", {}).items():
            self.game_map.bomb_sites[name] = MapBoundary(
                site["x"], site["y"], site["w"], site["h"], "bomb-site", name, site.get("elevation", 0),
                site.get("z", 0), site.get("height_z", 0.0)
            )
    
    def is_valid_position(self, x: float, y: float, player_radius: float = 0.5) -> bool:
        """Check if a position is valid using the Map object with correct elevation."""
        # determine the z coordinate based on ramps, stairs, objects, and areas
        z = self.game_map.get_elevation_at_position(x, y)
        return self.game_map.is_valid_position(x, y, z, player_radius)
    
    def get_current_area(self, x: float, y: float) -> Optional[str]:
        """Get the name of the map area at the given position using the Map object with proper elevation."""
        # determine elevation for correct area lookup
        z = self.game_map.get_elevation_at_position(x, y)
        return self.game_map.get_area_at_position(x, y, z)
    
    def is_within_bomb_site(self, x: float, y: float) -> Optional[str]:
        """Check if a position is within a bomb site using the Map object with proper elevation."""
        # determine elevation for correct bomb-site detection
        z = self.game_map.get_elevation_at_position(x, y)
        return self.game_map.is_within_bomb_site(x, y, z)
    
    def run(self):
        """Initialize and run the pygame visualization."""
        if pygame:
            import pygame
        pygame.init()
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(f"VCT Map: {self.map_data['metadata']['name']}")
        
        # Setup font
        font = pygame.font.SysFont("Arial", 12)
        title_font = pygame.font.SysFont("Arial", 20)
        
        # Camera offset for panning
        offset_x = (self.width - self.map_width) // 2
        offset_y = (self.height - self.map_height) // 2
        
        # Precompute bottom of the map for Y-axis inversion
        map_bottom = offset_y + self.map_height
        
        # Virtual player for testing
        player_pos = [self.map_size[0] // 2, self.map_size[1] // 2]
        player_speed = 0.2
        player_radius = 0.5
        
        running = True
        clock = pygame.time.Clock()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Player movement with collision detection
            keys = pygame.key.get_pressed()
            proposed_x, proposed_y = player_pos[0], player_pos[1]
            
            if keys[pygame.K_LEFT]:
                proposed_x -= player_speed
            if keys[pygame.K_RIGHT]:
                proposed_x += player_speed
            if keys[pygame.K_UP]:
                proposed_y += player_speed
            if keys[pygame.K_DOWN]:
                proposed_y -= player_speed
            
            # Check if the proposed position is valid
            if self.is_valid_position(proposed_x, player_pos[1], player_radius):
                player_pos[0] = proposed_x
            if self.is_valid_position(player_pos[0], proposed_y, player_radius):
                player_pos[1] = proposed_y
            
            # Clear screen
            screen.fill((255, 255, 255))
            
            # Draw map areas
            for name, area in self.area_boundaries.items():
                # Determine color based on area type
                color = self.colors["default"]
                for area_type in self.colors.keys():
                    if area_type in name:
                        color = self.colors[area_type]
                        break
                
                # Compute screen coordinates with inverted Y
                draw_x = area.x + offset_x
                draw_y = map_bottom - (area.y + area.height)
                pygame.draw.rect(screen, color, (draw_x, draw_y, area.width, area.height))
                pygame.draw.rect(screen, (0, 0, 0), (draw_x, draw_y, area.width, area.height), 1)
                
                # Draw area name near bottom-left
                name_text = font.render(name, True, (0, 0, 0))
                screen.blit(name_text, (draw_x + 5, draw_y + 5))
            
            # Draw walls
            for wall in self.wall_boundaries.values():
                wx = wall.x + offset_x
                wy = map_bottom - (wall.y + wall.height)
                pygame.draw.rect(screen, self.colors["wall"], (wx, wy, wall.width, wall.height))
            
            # Draw objects
            for obj in self.object_boundaries.values():
                ox = obj.x + offset_x
                oy = map_bottom - (obj.y + obj.height)
                pygame.draw.rect(screen, self.colors["object"], (ox, oy, obj.width, obj.height))
            
            # Draw stairs
            for stair in self.stair_boundaries.values():
                sx = stair.x + offset_x
                sy = map_bottom - (stair.y + stair.height)
                pygame.draw.rect(screen, self.colors["stairs"], (sx, sy, stair.width, stair.height))
            
            # Draw bomb sites
            for site in self.bomb_site_boundaries.values():
                bx = site.x + offset_x
                by = map_bottom - (site.y + site.height)
                pygame.draw.rect(screen, self.colors["bomb-site"], (bx, by, site.width, site.height), 2)
            
            # Draw player with Y-axis inversion
            px = player_pos[0] * self.scale + offset_x
            py = map_bottom - (player_pos[1] * self.scale)
            pygame.draw.circle(screen, (255, 0, 0), (int(px), int(py)), int(player_radius * self.scale))
            
            # Draw map info
            current_area = self.get_current_area(player_pos[0], player_pos[1])
            bomb_site = self.is_within_bomb_site(player_pos[0], player_pos[1])
            
            info_text = [
                f"Map: {self.map_data['metadata']['name']}",
                f"Position: ({player_pos[0]:.1f}, {player_pos[1]:.1f})",
                f"Current Area: {current_area or 'None'}",
                f"Bomb Site: {bomb_site or 'None'}"
            ]
            
            for i, text in enumerate(info_text):
                info_surface = font.render(text, True, (0, 0, 0))
                screen.blit(info_surface, (10, 10 + i * 20))
            
            # Draw title
            title_surface = title_font.render(self.map_data["metadata"]["name"], True, (0, 0, 0))
            screen.blit(title_surface, (self.width // 2 - title_surface.get_width() // 2, 10))
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

def load_map_from_json(filepath: str) -> Dict:
    """Load a map from JSON file in the Ascent map format."""
    with open(filepath, 'r') as f:
        return json.load(f)

def visualize_map_with_pygame(map_filepath: str, width: int = 1200, height: int = 900, scale: float = 20) -> None:
    """Visualize a map using the Pygame-based visualizer."""
    visualizer = MapVisualizer(map_filepath, width, height, scale)
    visualizer.run()

# Add the function to MapLayout for backward compatibility
def visualize_with_pygame(self, width: int = 1200, height: int = 900) -> None:
    """Visualize this map using the Pygame-based visualizer."""
    print("This map format is not compatible with the Pygame visualizer.")
    print("Please use the new Ascent map format and visualize_map_with_pygame() function.")

# Add the method to MapLayout class
MapLayout.visualize_with_pygame = visualize_with_pygame

def generate_random_map(seed: Optional[int] = None) -> MapLayout:
    """Generate a random Valorant-style tactical map with realistic features."""
    if seed: 
        random.seed(seed)
    
    # 1. Choose a random theme and number of sites
    themes = ["Venice", "Moroccan City", "Underground Facility", "Cyberpunk City", 
              "Space Station", "Jungle Temple", "Desert Ruins", "Industrial Port",
              "Snowy Outpost", "Mountain Monastery", "Futuristic City", "Medieval Castle"]
    theme = random.choice(themes)
    num_sites = random.choice([2, 3])
    map_name = f"{theme} Map"
    layout = MapLayout(name=map_name, theme=theme)

    # 2. Define map size and key coordinates 
    width, height = (120.0, 100.0) if num_sites == 3 else (100.0, 100.0)
    
    # Place spawns at opposite ends
    attacker_spawn_pos = (10.0, height/2)
    defender_spawn_pos = (width - 10.0, height/2)
    
    # Create spawn areas
    layout.areas.append(MapArea("Attacker Spawn", "spawn", attacker_spawn_pos, radius=8.0))
    layout.areas.append(MapArea("Defender Spawn", "spawn", defender_spawn_pos, radius=8.0))
    layout.attacker_spawns = [attacker_spawn_pos]
    layout.defender_spawns = [defender_spawn_pos]

    # 3. Create the site areas and intermediate areas based on number of sites
    if num_sites == 2:
        # Create a more complex 2-site map like Ascent or Bind
        a_site_pos = (width - 25.0, height * 0.3)  # A Site 
        b_site_pos = (width - 25.0, height * 0.7)  # B Site
        
        # Main approaches to each site
        a_main_pos = (width * 0.6, height * 0.3)  # A Main
        b_main_pos = (width * 0.6, height * 0.7)  # B Main
        
        # Mid area and connectors
        mid_pos = (width * 0.5, height * 0.5)      # Mid
        a_link_pos = (width * 0.65, height * 0.4)  # A-Mid connector
        b_link_pos = (width * 0.65, height * 0.6)  # B-Mid connector
        
        # Secondary paths and tactical positions
        a_lobby_pos = (width * 0.3, height * 0.3)  # Entry to A Main
        b_lobby_pos = (width * 0.3, height * 0.7)  # Entry to B Main
        mid_entrance_pos = (width * 0.3, height * 0.5)  # Entry to Mid
        
        # Special positions
        a_heaven_pos = (width - 20.0, height * 0.35)  # Elevated position overlooking A
        b_cubby_pos = (width - 30.0, height * 0.65)   # Hiding spot near B

        # Create all the areas
        layout.areas += [
            MapArea("A Site", "site", a_site_pos, radius=12.0, is_plant_site=True),
            MapArea("B Site", "site", b_site_pos, radius=12.0, is_plant_site=True),
            MapArea("A Main", "choke", a_main_pos),
            MapArea("B Main", "choke", b_main_pos),
            MapArea("Mid", "mid", mid_pos),
            MapArea("A Link", "connector", a_link_pos),
            MapArea("B Link", "connector", b_link_pos),
            MapArea("A Lobby", "connector", a_lobby_pos),
            MapArea("B Lobby", "connector", b_lobby_pos),
            MapArea("Mid Entrance", "choke", mid_entrance_pos),
            MapArea("A Heaven", "heaven", a_heaven_pos, elevation=1),
            MapArea("B Cubby", "cubby", b_cubby_pos)
        ]
        
        # Set up neighbors (more complex graph with multiple paths)
        _neighbors = {
            "Attacker Spawn": ["A Lobby", "Mid Entrance", "B Lobby"],
            "Defender Spawn": ["A Site", "B Site"],
            "A Lobby": ["Attacker Spawn", "A Main"],
            "A Main": ["A Lobby", "A Site", "A Link"],
            "A Link": ["A Main", "Mid", "A Site"],
            "A Site": ["A Main", "A Link", "Defender Spawn", "A Heaven"],
            "A Heaven": ["A Site"],
            "Mid Entrance": ["Attacker Spawn", "Mid"],
            "Mid": ["Mid Entrance", "A Link", "B Link"],
            "B Link": ["Mid", "B Site", "B Main"],
            "B Main": ["B Lobby", "B Site", "B Link", "B Cubby"],
            "B Lobby": ["Attacker Spawn", "B Main"],
            "B Site": ["B Main", "B Link", "Defender Spawn", "B Cubby"],
            "B Cubby": ["B Site", "B Main"]
        }
        
        # Add cover objects to sites and choke points
        for area in layout.areas:
            if area.name == "A Site":
                area.cover_objects = [
                    {"type": "box", "position": (a_site_pos[0] - 5, a_site_pos[1] - 3), "size": (3, 3)},
                    {"type": "box", "position": (a_site_pos[0] + 3, a_site_pos[1] + 4), "size": (4, 2)},
                    {"type": "wall_gap", "position": (a_site_pos[0] - 2, a_site_pos[1] + 5), "size": (1, 4)}
                ]
                layout.default_plant_spots["A"] = [
                    (a_site_pos[0] - 4, a_site_pos[1]), 
                    (a_site_pos[0] + 3, a_site_pos[1] - 3)
                ]
            elif area.name == "B Site":
                area.cover_objects = [
                    {"type": "crate", "position": (b_site_pos[0] - 3, b_site_pos[1] + 4), "size": (4, 4)},
                    {"type": "wall_corner", "position": (b_site_pos[0] + 5, b_site_pos[1] - 2), "size": (3, 3)}
                ]
                layout.default_plant_spots["B"] = [
                    (b_site_pos[0] - 2, b_site_pos[1] - 2), 
                    (b_site_pos[0] + 4, b_site_pos[1])
                ]
            elif area.name == "Mid":
                area.cover_objects = [
                    {"type": "box", "position": (mid_pos[0], mid_pos[1] - 3), "size": (2, 2)},
                    {"type": "column", "position": (mid_pos[0] + 3, mid_pos[1] + 3), "size": (1, 1)}
                ]
            elif area.name == "A Main" or area.name == "B Main":
                area.cover_objects = [
                    {"type": "box", "position": (
                        a_main_pos[0] if area.name == "A Main" else b_main_pos[0], 
                        a_main_pos[1] - 2 if area.name == "A Main" else b_main_pos[1] + 2
                    ), "size": (3, 2)}
                ]
        
        # Add one-way connections (drops)
        for area in layout.areas:
            if area.name == "A Heaven":
                area.one_way_connections = ["A Site"]
        
        # Place ultimate orbs
        layout.orbs = [(mid_pos[0], mid_pos[1] - 8), (mid_pos[0], mid_pos[1] + 8)]
                
    else:
        # Three-site map (like Haven)
        a_site_pos = (width - 30.0, height * 0.25)  # A Site (top)
        b_site_pos = (width - 25.0, height * 0.5)   # B Site (middle)
        c_site_pos = (width - 30.0, height * 0.75)  # C Site (bottom)
        
        # Main approaches
        a_main_pos = (width * 0.5, height * 0.25)   # A Main
        c_main_pos = (width * 0.5, height * 0.75)   # C Main
        
        # Mid and connectors
        b_main_pos = (width * 0.5, height * 0.5)    # B Main (middle entrance)
        a_link_pos = (width * 0.7, height * 0.35)   # A-B connector
        c_link_pos = (width * 0.7, height * 0.65)   # B-C connector
        
        # Lobby/entrance areas
        a_lobby_pos = (width * 0.3, height * 0.25)  # A entrance
        b_lobby_pos = (width * 0.3, height * 0.5)   # B entrance
        c_lobby_pos = (width * 0.3, height * 0.75)  # C entrance
        
        # Special positions
        b_heaven_pos = (width - 20.0, height * 0.45)  # Elevated overlooking B
        c_long_pos = (width * 0.4, height * 0.75)     # Long corridor to C
        
        # Create areas
        layout.areas += [
            MapArea("A Site", "site", a_site_pos, radius=12.0, is_plant_site=True),
            MapArea("B Site", "site", b_site_pos, radius=12.0, is_plant_site=True),
            MapArea("C Site", "site", c_site_pos, radius=12.0, is_plant_site=True),
            MapArea("A Main", "choke", a_main_pos),
            MapArea("B Main", "choke", b_main_pos),
            MapArea("C Main", "choke", c_main_pos),
            MapArea("A Link", "connector", a_link_pos),
            MapArea("C Link", "connector", c_link_pos),
            MapArea("A Lobby", "connector", a_lobby_pos),
            MapArea("B Lobby", "connector", b_lobby_pos),
            MapArea("C Lobby", "connector", c_lobby_pos),
            MapArea("B Heaven", "heaven", b_heaven_pos, elevation=1),
            MapArea("C Long", "corridor", c_long_pos)
        ]
        
        # Set up neighbors
        _neighbors = {
            "Attacker Spawn": ["A Lobby", "B Lobby", "C Lobby"],
            "Defender Spawn": ["A Site", "B Site", "C Site"],
            "A Lobby": ["Attacker Spawn", "A Main"],
            "A Main": ["A Lobby", "A Site", "A Link"],
            "A Link": ["A Main", "B Site", "A Site"],
            "A Site": ["A Main", "A Link", "Defender Spawn"],
            "B Lobby": ["Attacker Spawn", "B Main"],
            "B Main": ["B Lobby", "B Site"],
            "B Site": ["B Main", "A Link", "C Link", "Defender Spawn", "B Heaven"],
            "B Heaven": ["B Site"],
            "C Lobby": ["Attacker Spawn", "C Long"],
            "C Long": ["C Lobby", "C Main"],
            "C Main": ["C Long", "C Site"],
            "C Link": ["B Site", "C Site"],
            "C Site": ["C Main", "C Link", "Defender Spawn"]
        }
        
        # Add cover objects
        for area in layout.areas:
            if area.area_type == "site":
                # Add default covers to sites
                site_center = area.center
                area.cover_objects = [
                    {"type": "box", "position": (site_center[0] - 4, site_center[1] - 2), "size": (3, 3)},
                    {"type": "crate", "position": (site_center[0] + 3, site_center[1] + 3), "size": (2, 2)}
                ]
                # Add default plant spots
                site_key = area.name[0]  # A, B, or C
                layout.default_plant_spots[site_key] = [
                    (site_center[0] - 3, site_center[1]), 
                    (site_center[0] + 3, site_center[1] - 2)
                ]
            elif area.area_type == "choke":
                # Add cover in chokepoints
                area.cover_objects = [
                    {"type": "box", "position": (area.center[0] - 2, area.center[1]), "size": (2, 2)}
                ]
        
        # Add one-way connections
        for area in layout.areas:
            if area.name == "B Heaven":
                area.one_way_connections = ["B Site"]
        
        # Place ultimate orbs
        layout.orbs = [(a_lobby_pos[0] - 5, a_lobby_pos[1]), (c_lobby_pos[0] - 5, c_lobby_pos[1])]

    # Apply neighbor relations to MapArea objects
    for area in layout.areas:
        if area.name in _neighbors:
            area.neighbors = _neighbors[area.name]

    # 4. Place walls to shape the map geometry
    # Basic outer walls
    layout.walls.append({"start": (0, 0), "end": (width, 0)})  # Top border
    layout.walls.append({"start": (width, 0), "end": (width, height)})  # Right border
    layout.walls.append({"start": (width, height), "end": (0, height)})  # Bottom border
    layout.walls.append({"start": (0, height), "end": (0, 0)})  # Left border
    
    if num_sites == 2:
        # Walls for a 2-site map
        # Main walls dividing areas
        layout.walls.append({"start": (width*0.4, height*0.4), "end": (width*0.4, height*0.0)})  # Top-mid divider
        layout.walls.append({"start": (width*0.4, height*0.6), "end": (width*0.4, height*1.0)})  # Bottom-mid divider
        layout.walls.append({"start": (width*0.55, height*0.4), "end": (width*0.55, height*0.6)})  # Mid connector
        
        # A site walls
        layout.walls.append({"start": (width*0.7, height*0.2), "end": (width*0.9, height*0.2)})  # A site top
        layout.walls.append({"start": (width*0.7, height*0.4), "end": (width*0.9, height*0.4)})  # A site bottom
        
        # B site walls
        layout.walls.append({"start": (width*0.7, height*0.6), "end": (width*0.9, height*0.6)})  # B site top
        layout.walls.append({"start": (width*0.7, height*0.8), "end": (width*0.9, height*0.8)})  # B site bottom
        
        # Chokepoint walls
        layout.walls.append({"start": (width*0.35, height*0.25), "end": (width*0.45, height*0.25)})  # A main top
        layout.walls.append({"start": (width*0.35, height*0.35), "end": (width*0.45, height*0.35)})  # A main bottom
        layout.walls.append({"start": (width*0.35, height*0.65), "end": (width*0.45, height*0.65)})  # B main top
        layout.walls.append({"start": (width*0.35, height*0.75), "end": (width*0.45, height*0.75)})  # B main bottom
        
    else:
        # Walls for a 3-site map
        # Dividers between sites
        layout.walls.append({"start": (width*0.4, height*0.35), "end": (width*0.8, height*0.35)})  # A-B divider
        layout.walls.append({"start": (width*0.4, height*0.65), "end": (width*0.8, height*0.65)})  # B-C divider
        
        # Site enclosures
        layout.walls.append({"start": (width*0.6, height*0.15), "end": (width*0.9, height*0.15)})  # A site top
        layout.walls.append({"start": (width*0.6, height*0.45), "end": (width*0.9, height*0.45)})  # B site top
        layout.walls.append({"start": (width*0.6, height*0.55), "end": (width*0.9, height*0.55)})  # B site bottom
        layout.walls.append({"start": (width*0.6, height*0.85), "end": (width*0.9, height*0.85)})  # C site bottom
        
        # Chokepoint walls
        layout.walls.append({"start": (width*0.35, height*0.2), "end": (width*0.45, height*0.2)})   # A entrance top
        layout.walls.append({"start": (width*0.35, height*0.3), "end": (width*0.45, height*0.3)})   # A entrance bottom
        layout.walls.append({"start": (width*0.35, height*0.45), "end": (width*0.45, height*0.45)})  # B entrance top
        layout.walls.append({"start": (width*0.35, height*0.55), "end": (width*0.45, height*0.55)})  # B entrance bottom
        layout.walls.append({"start": (width*0.35, height*0.7), "end": (width*0.45, height*0.7)})   # C entrance top
        layout.walls.append({"start": (width*0.35, height*0.8), "end": (width*0.45, height*0.8)})   # C entrance bottom

    # 5. Apply theme-specific changes (renaming areas, adding decorations)
    rename_map = {}  # Areas to rename based on theme
    
    if theme == "Venice":
        rename_map = {
            "Mid": "Courtyard",
            "A Link": "Wine Cellar",
            "B Link": "Market"
        }
        layout.decorative_elements.append({"type": "gondola", "position": (width*0.5 - 5, height*0.5)})
        layout.decorative_elements.append({"type": "fountain", "position": (width*0.5 + 5, height*0.5)})
    elif theme == "Moroccan City":
        rename_map = {
            "Mid": "Bazaar",
            "A Main": "Palace",
            "B Main": "Garden"
        }
        layout.decorative_elements.append({"type": "archway", "position": (width*0.5, height*0.5)})
        layout.decorative_elements.append({"type": "carpet", "position": (width*0.7, height*0.7)})
    elif theme == "Underground Facility":
        rename_map = {
            "Mid": "Lab",
            "A Main": "Server",
            "B Main": "Reactor",
            "A Link": "Vent",
            "B Link": "Duct"
        }
        layout.decorative_elements.append({"type": "computer", "position": (width*0.6, height*0.3)})
        layout.decorative_elements.append({"type": "console", "position": (width*0.6, height*0.7)})
    elif theme == "Jungle Temple":
        rename_map = {
            "Mid": "Ruins",
            "A Main": "Shrine",
            "B Main": "Altar",
            "A Link": "Tunnel",
            "B Link": "Passage"
        }
        layout.decorative_elements.append({"type": "statue", "position": (width*0.5, height*0.5)})
        layout.decorative_elements.append({"type": "vines", "position": (width*0.2, height*0.2)})

    # Apply renaming to areas
    for area in layout.areas:
        if area.name in rename_map:
            area.name = rename_map[area.name]

    # Update neighbor references to reflect renamed areas
    new_neighbors = {}
    for old_name, new_name in rename_map.items():
        if old_name in _neighbors:
            new_neighbors[new_name] = _neighbors[old_name]

    # Update neighbor lists in each area
    for area in layout.areas:
        area.neighbors = [new_neighbors.get(n, n) for n in area.neighbors]

    return layout

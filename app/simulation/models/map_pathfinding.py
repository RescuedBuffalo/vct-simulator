import numpy as np
from typing import List, Tuple, Optional, Dict
import heapq
import math

class Node:
    """A node in the pathfinding graph."""
    def __init__(self, position: Tuple[float, float, float], g_cost: float = 0, 
                 h_cost: float = 0, parent: Optional['Node'] = None):
        self.position = position
        self.g_cost = g_cost  # Cost from start to this node
        self.h_cost = h_cost  # Estimated cost from this node to goal
        self.f_cost = g_cost + h_cost  # Total estimated cost
        self.parent = parent
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost

class NavigationMesh:
    """A navigation mesh for pathfinding."""
    def __init__(self, width: float, height: float, cell_size: float = 1.0):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        
        # Calculate grid dimensions
        self.grid_width = int(width / cell_size)
        self.grid_height = int(height / cell_size)
        
        # Initialize walkable grid
        self.walkable = np.ones((self.grid_height, self.grid_width), dtype=bool)
        
        # Store elevation data
        self.elevation = np.zeros((self.grid_height, self.grid_width))
        
        # Store areas for lookup
        self.areas: Dict[str, Dict] = {}
        
    def add_obstacle(self, x: float, y: float, w: float, h: float):
        """Mark an area as non-walkable."""
        # Convert to grid coordinates
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        grid_w = max(1, int(w / self.cell_size))
        grid_h = max(1, int(h / self.cell_size))
        
        # Ensure within bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        grid_w = min(grid_w, self.grid_width - grid_x)
        grid_h = min(grid_h, self.grid_height - grid_y)
        
        # Mark as non-walkable
        self.walkable[grid_y:grid_y+grid_h, grid_x:grid_x+grid_w] = False
    
    def set_elevation(self, x: float, y: float, elevation: float):
        """Set elevation at a point."""
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            self.elevation[grid_y, grid_x] = elevation
    
    def add_area(self, name: str, area_data: Dict):
        """Add an area to the navigation mesh."""
        self.areas[name] = area_data
        
        # Update elevation if area has elevation
        if "elevation" in area_data:
            x = int(area_data["x"] / self.cell_size)
            y = int(area_data["y"] / self.cell_size)
            w = int(area_data["w"] / self.cell_size)
            h = int(area_data["h"] / self.cell_size)
            
            # Ensure within bounds
            x = max(0, min(x, self.grid_width - 1))
            y = max(0, min(y, self.grid_height - 1))
            w = min(w, self.grid_width - x)
            h = min(h, self.grid_height - y)
            
            self.elevation[y:y+h, x:x+w] = area_data["elevation"]
    
    def is_walkable(self, x: float, y: float) -> bool:
        """Check if a position is walkable."""
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            return self.walkable[grid_y, grid_x]
        return False
    
    def get_elevation(self, x: float, y: float) -> float:
        """Get elevation at a position."""
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            return self.elevation[grid_y, grid_x]
        return 0.0
    
    def get_neighbors(self, node: Node) -> List[Tuple[float, float, float]]:
        """Get walkable neighboring positions."""
        x, y, z = node.position
        neighbors = []
        
        # Convert to grid coordinates
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        
        # Check 8 surrounding cells
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,1), (1,-1), (-1,-1)]:
            new_grid_x = grid_x + dx
            new_grid_y = grid_y + dy
            
            # Skip if out of bounds
            if (new_grid_x < 0 or new_grid_x >= self.grid_width or
                new_grid_y < 0 or new_grid_y >= self.grid_height):
                continue
            
            # Skip if not walkable
            if not self.walkable[new_grid_y, new_grid_x]:
                continue
            
            # Convert back to world coordinates (center of cell)
            new_x = (new_grid_x + 0.5) * self.cell_size
            new_y = (new_grid_y + 0.5) * self.cell_size
            new_z = self.elevation[new_grid_y, new_grid_x]
            
            # Check if elevation change is traversable
            if abs(new_z - z) <= 1.5:  # Max climbable height
                neighbors.append((new_x, new_y, new_z))
        
        return neighbors

class PathFinder:
    """A* pathfinding implementation."""
    def __init__(self, nav_mesh: NavigationMesh):
        self.nav_mesh = nav_mesh
    
    def find_path(self, start: Tuple[float, float, float], 
                  goal: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        """Find a path from start to goal."""
        # Convert to grid coordinates
        start_x = int(start[0] / self.nav_mesh.cell_size)
        start_y = int(start[1] / self.nav_mesh.cell_size)
        goal_x = int(goal[0] / self.nav_mesh.cell_size)
        goal_y = int(goal[1] / self.nav_mesh.cell_size)
        
        # Check if start or goal is out of bounds or not walkable
        if (not (0 <= start_x < self.nav_mesh.grid_width and 0 <= start_y < self.nav_mesh.grid_height) or
            not (0 <= goal_x < self.nav_mesh.grid_width and 0 <= goal_y < self.nav_mesh.grid_height) or
            not self.nav_mesh.walkable[start_y, start_x] or
            not self.nav_mesh.walkable[goal_y, goal_x]):
            return []
        
        # Create start and goal nodes
        start_node = Node((start_x * self.nav_mesh.cell_size, start_y * self.nav_mesh.cell_size, start[2]))
        goal_node = Node((goal_x * self.nav_mesh.cell_size, goal_y * self.nav_mesh.cell_size, goal[2]))
        
        # Initialize open and closed sets
        open_set = []
        closed_set = set()
        open_dict = {}  # For faster lookup
        
        # Add start node to open set
        heapq.heappush(open_set, start_node)
        open_dict[start_node.position] = start_node
        
        while open_set:
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            open_dict.pop(current.position)
            closed_set.add(current.position)
            
            # Check if reached goal
            if self._distance_to(current.position, goal) < self.nav_mesh.cell_size * 1.5:
                path = self._reconstruct_path(current)
                # Convert back to world coordinates and ensure goal is reached
                path = [(x, y, z) for x, y, z in path]
                if path:
                    path[-1] = goal  # Force last point to be exactly the goal
                return path
            
            # Check neighbors
            for neighbor_pos in self.nav_mesh.get_neighbors(current):
                if neighbor_pos in closed_set:
                    continue
                
                # Calculate costs
                g_cost = current.g_cost + self._distance_to(current.position, neighbor_pos)
                h_cost = self._distance_to(neighbor_pos, goal)
                
                # Create neighbor node
                neighbor = Node(neighbor_pos, g_cost, h_cost, current)
                
                # Check if already in open set with better path
                if neighbor_pos in open_dict:
                    existing = open_dict[neighbor_pos]
                    if neighbor.g_cost < existing.g_cost:
                        # Update existing node
                        existing.g_cost = neighbor.g_cost
                        existing.f_cost = existing.g_cost + existing.h_cost
                        existing.parent = current
                        # Reheapify
                        heapq.heapify(open_set)
                else:
                    heapq.heappush(open_set, neighbor)
                    open_dict[neighbor_pos] = neighbor
        
        # No path found
        return []
    
    def _distance_to(self, pos1: Tuple[float, float, float], 
                    pos2: Tuple[float, float, float]) -> float:
        """Calculate 3D distance between positions."""
        return math.sqrt(
            (pos2[0] - pos1[0])**2 + 
            (pos2[1] - pos1[1])**2 + 
            (pos2[2] - pos1[2])**2
        )
    
    def _reconstruct_path(self, end_node: Node) -> List[Tuple[float, float, float]]:
        """Reconstruct path from end node to start."""
        path = []
        current = end_node
        
        while current is not None:
            path.append(current.position)
            current = current.parent
        
        return list(reversed(path))

class CollisionDetector:
    """Handles collision detection between objects."""
    def __init__(self, nav_mesh: NavigationMesh):
        self.nav_mesh = nav_mesh
    
    def check_collision(self, position: Tuple[float, float, float], 
                       radius: float, height: float) -> bool:
        """Check if an object collides with any obstacles."""
        x, y, z = position
        
        # Convert to grid coordinates
        grid_x = int(x / self.nav_mesh.cell_size)
        grid_y = int(y / self.nav_mesh.cell_size)
        
        # Calculate grid cells to check based on radius
        radius_cells = max(1, int((radius * 2) / self.nav_mesh.cell_size))
        
        # Check surrounding cells
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                check_x = grid_x + dx
                check_y = grid_y + dy
                
                # Skip if out of bounds
                if (check_x < 0 or check_x >= self.nav_mesh.grid_width or
                    check_y < 0 or check_y >= self.nav_mesh.grid_height):
                    continue
                
                # Check if cell is non-walkable
                if not self.nav_mesh.walkable[check_y, check_x]:
                    # Check cell center
                    cell_center_x = (check_x + 0.5) * self.nav_mesh.cell_size
                    cell_center_y = (check_y + 0.5) * self.nav_mesh.cell_size
                    dx = cell_center_x - x
                    dy = cell_center_y - y
                    dist = math.sqrt(dx*dx + dy*dy)
                    
                    # Check elevation
                    cell_z = self.nav_mesh.elevation[check_y, check_x]
                    if dist <= radius and abs(cell_z - z) < height:
                        return True
                    
                    # Check corners
                    corners = [
                        (check_x * self.nav_mesh.cell_size, check_y * self.nav_mesh.cell_size),
                        ((check_x + 1) * self.nav_mesh.cell_size, check_y * self.nav_mesh.cell_size),
                        (check_x * self.nav_mesh.cell_size, (check_y + 1) * self.nav_mesh.cell_size),
                        ((check_x + 1) * self.nav_mesh.cell_size, (check_y + 1) * self.nav_mesh.cell_size)
                    ]
                    
                    for corner_x, corner_y in corners:
                        dx = corner_x - x
                        dy = corner_y - y
                        dist = math.sqrt(dx*dx + dy*dy)
                        if dist <= radius:
                            return True
                    
                    # Check edges
                    for i in range(len(corners)):
                        x1, y1 = corners[i]
                        x2, y2 = corners[(i + 1) % len(corners)]
                        # Calculate closest point on line segment
                        dx = x2 - x1
                        dy = y2 - y1
                        length_sq = dx*dx + dy*dy
                        if length_sq > 0:
                            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / length_sq))
                            closest_x = x1 + t * dx
                            closest_y = y1 + t * dy
                            dx = closest_x - x
                            dy = closest_y - y
                            dist = math.sqrt(dx*dx + dy*dy)
                            if dist <= radius:
                                return True
                    
                    # Check if cell is elevated platform
                    if cell_z > z and abs(cell_z - z) < height:
                        # Check if close to platform edge
                        edge_dist = min(
                            abs(x - check_x * self.nav_mesh.cell_size),
                            abs(x - (check_x + 1) * self.nav_mesh.cell_size),
                            abs(y - check_y * self.nav_mesh.cell_size),
                            abs(y - (check_y + 1) * self.nav_mesh.cell_size)
                        )
                        if edge_dist <= radius:
                            return True
        
        return False
    
    def ray_cast(self, start: Tuple[float, float, float], 
                 direction: Tuple[float, float, float], 
                 max_distance: float) -> Optional[Tuple[float, float, float]]:
        """Cast a ray and return the first hit point."""
        # Normalize direction
        length = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
        if length == 0:
            return None
        
        dx = direction[0] / length
        dy = direction[1] / length
        dz = direction[2] / length
        
        # Current position
        x, y, z = start
        
        # Step through grid cells
        step_size = self.nav_mesh.cell_size * 0.5
        distance = 0
        
        while distance < max_distance:
            # Check current cell
            grid_x = int(x / self.nav_mesh.cell_size)
            grid_y = int(y / self.nav_mesh.cell_size)
            
            if 0 <= grid_x < self.nav_mesh.grid_width and 0 <= grid_y < self.nav_mesh.grid_height:
                if not self.nav_mesh.walkable[grid_y, grid_x]:
                    return (x, y, z)
                
                # Check elevation
                cell_z = self.nav_mesh.elevation[grid_y, grid_x]
                if z < cell_z or z > cell_z + 3.0:
                    return (x, y, z)
            
            # Step forward
            x += dx * step_size
            y += dy * step_size
            z += dz * step_size
            distance += step_size
        
        return None

def create_navigation_mesh(map_data: Dict) -> NavigationMesh:
    """Create a navigation mesh from map data."""
    # Get map dimensions
    width = map_data["metadata"]["map-size"][0]
    height = map_data["metadata"]["map-size"][1]
    
    # Create navigation mesh
    nav_mesh = NavigationMesh(width, height)
    
    # Add walls
    for wall in map_data["walls"].values():
        nav_mesh.add_obstacle(wall["x"], wall["y"], wall["w"], wall["h"])
    
    # Add objects
    for obj in map_data["objects"].values():
        nav_mesh.add_obstacle(obj["x"], obj["y"], obj["w"], obj["h"])
    
    # Add areas
    for area in map_data["map-areas"].values():
        nav_mesh.add_area(area["name"], area)
        # Set elevation for area
        if "elevation" in area:
            x = int(area["x"] / nav_mesh.cell_size)
            y = int(area["y"] / nav_mesh.cell_size)
            w = int(area["w"] / nav_mesh.cell_size)
            h = int(area["h"] / nav_mesh.cell_size)
            nav_mesh.elevation[y:y+h, x:x+w] = area["elevation"]
    
    # Add elevation points
    for point in map_data["elevation-points"]:
        x = int(point["position"][0] / nav_mesh.cell_size)
        y = int(point["position"][1] / nav_mesh.cell_size)
        nav_mesh.elevation[y, x] = point["elevation"]
    
    return nav_mesh 
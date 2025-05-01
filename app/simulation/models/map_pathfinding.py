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
        
        # Initialize walkable grid and elevation
        self.walkable = np.ones((self.grid_height, self.grid_width), dtype=bool)
        self.elevation = np.zeros((self.grid_height, self.grid_width))
        
        # Store areas for lookup
        self.areas: Dict[str, Dict] = {}

        self.collision_detector = None
        
    def add_obstacle(self, x: float, y: float, w: float, h: float, z: float = 0.0, height_z: float = 0.0):
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
        
        # Mark as non-walkable and set elevation
        self.walkable[grid_y:grid_y+grid_h, grid_x:grid_x+grid_w] = False
        if height_z > 0:
            self.elevation[grid_y:grid_y+grid_h, grid_x:grid_x+grid_w] = z + height_z
    
    def set_elevation(self, x: float, y: float, w: float, h: float, z: float):
        """Set elevation for an area."""
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        grid_w = max(1, int(w / self.cell_size))
        grid_h = max(1, int(h / self.cell_size))
        
        # Ensure within bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        grid_w = min(grid_w, self.grid_width - grid_x)
        grid_h = min(grid_h, self.grid_height - grid_y)
        
        self.elevation[grid_y:grid_y+grid_h, grid_x:grid_x+grid_w] = z

    def set_stairs_elevation(self, x: float, y: float, w: float, h: float, start_z: float, end_z: float, direction: str):
        """Set elevation gradient for stairs."""
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        grid_w = max(1, int(w / self.cell_size))
        grid_h = max(1, int(h / self.cell_size))
        
        # Ensure within bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        grid_w = min(grid_w, self.grid_width - grid_x)
        grid_h = min(grid_h, self.grid_height - grid_y)
        
        # Create elevation gradient
        for dy in range(grid_h):
            for dx in range(grid_w):
                if direction == "north":
                    progress = float(dy) / (grid_h - 1) if grid_h > 1 else 1.0
                elif direction == "south":
                    progress = 1.0 - (float(dy) / (grid_h - 1)) if grid_h > 1 else 0.0
                elif direction == "east":
                    progress = float(dx) / (grid_w - 1) if grid_w > 1 else 1.0
                else:  # west
                    progress = 1.0 - (float(dx) / (grid_w - 1)) if grid_w > 1 else 0.0
                
                elevation = start_z + (end_z - start_z) * progress
                if 0 <= grid_y + dy < self.grid_height and 0 <= grid_x + dx < self.grid_width:
                    self.elevation[grid_y + dy, grid_x + dx] = elevation
                    self.walkable[grid_y + dy, grid_x + dx] = True

    def add_area(self, name: str, area_data: Dict):
        """Add an area to the navigation mesh."""
        self.areas[name] = area_data
        
        # Set area elevation
        x = area_data["x"]
        y = area_data["y"]
        w = area_data["w"]
        h = area_data["h"]
        z = area_data.get("z", 0)  # Use z instead of elevation
        
        self.set_elevation(x, y, w, h, z)
    
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
            return float(self.elevation[grid_y, grid_x])
        return 0.0
    
    def get_neighbors(self, node: Node) -> List[Tuple[float, float, float]]:
        """Get valid neighboring positions."""
        x, y, z = node.position
        neighbors = []
        
        # Convert to grid coordinates
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        
        # Check all 8 directions
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,1), (1,-1), (-1,-1)]:
            new_grid_x = grid_x + dx
            new_grid_y = grid_y + dy
            
            # Check bounds
            if not (0 <= new_grid_x < self.grid_width and 0 <= new_grid_y < self.grid_height):
                continue
                
            # Check if walkable
            if not self.walkable[new_grid_y, new_grid_x]:
                continue
            
            # Get world coordinates
            new_x = new_grid_x * self.cell_size
            new_y = new_grid_y * self.cell_size
            new_z = self.get_elevation(new_x, new_y)
            
            # Check elevation difference
            if abs(new_z - z) > 1.5:  # Max climbable height
                continue
                
            # Check for collisions along the path
            if self.collision_detector.check_collision((x,y,z), (new_x, new_y, new_z)):
                continue
                
            neighbors.append((new_x, new_y, new_z))
        return neighbors

class PathFinder:
    """A* pathfinding implementation."""
    def __init__(self, nav_mesh: NavigationMesh):
        self.nav_mesh = nav_mesh
    
    def _distance_to(self, pos1: Tuple[float, float, float], 
                    pos2: Tuple[float, float, float]) -> float:
        """Calculate 3D distance between positions with extra weight for elevation difference."""
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        # Give more weight to elevation difference to encourage exploring different heights
        return math.sqrt(dx*dx + dy*dy + 3.0*dz*dz)
    
    def find_path(self, start: Tuple[float, float, float], 
                  goal: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        """Find a path from start to goal."""
        print(f"\nPathfinding debug:")
        print(f"Start: {start}")
        print(f"Goal: {goal}")
        
        # Convert to grid coordinates
        start_x = int(start[0] / self.nav_mesh.cell_size)
        start_y = int(start[1] / self.nav_mesh.cell_size)
        goal_x = int(goal[0] / self.nav_mesh.cell_size)
        goal_y = int(goal[1] / self.nav_mesh.cell_size)
        
        # Check if start or goal is out of bounds or not walkable
        if not (0 <= start_x < self.nav_mesh.grid_width and 0 <= start_y < self.nav_mesh.grid_height):
            print("Start position out of bounds")
            return []
        if not (0 <= goal_x < self.nav_mesh.grid_width and 0 <= goal_y < self.nav_mesh.grid_height):
            print("Goal position out of bounds")
            return []
        if not self.nav_mesh.walkable[start_y, start_x]:
            print("Start position not walkable")
            return []
        if not self.nav_mesh.walkable[goal_y, goal_x]:
            print("Goal position not walkable")
            return []
        
        # Create start and goal nodes
        start_node = Node(start, g_cost=0, h_cost=self._distance_to(start, goal))
        goal_pos = goal
        
        # Initialize open and closed sets
        open_set = []
        closed_set = set()
        open_dict = {}  # For faster lookup
        
        # Add start node to open set
        heapq.heappush(open_set, start_node)
        open_dict[start_node.position] = start_node
        
        iterations = 0
        max_iterations = 1000
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            open_dict.pop(current.position)
            
            # Check if reached goal - more lenient distance check
            dist_to_goal = self._distance_to(current.position, goal)
            if dist_to_goal < self.nav_mesh.cell_size * 1.5:
                print(f"Found path after {iterations} iterations")
                path = self._reconstruct_path(current)
                if path:
                    if dist_to_goal > 0.1:
                        path.append(goal)
                    print(f"Path found: {path}")
                    return path
                print("Failed to reconstruct path")
                return []
            
            # Get and check neighbors
            neighbors = self._get_neighbors(current, goal)
            print(f"Iteration {iterations}: Current={current.position}, Found {len(neighbors)} neighbors")
            
            # Add current to closed set AFTER getting neighbors
            # This allows revisiting nodes if we find a better path
            closed_set.add(current.position)
            
            for neighbor_pos in neighbors:
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
        
        if iterations >= max_iterations:
            print("Reached maximum iterations")
        else:
            print("No more nodes to explore")
        return []
    
    def _reconstruct_path(self, end_node: Node) -> List[Tuple[float, float, float]]:
        """Reconstruct path from end node to start."""
        path = []
        current = end_node
        
        while current is not None:
            path.append(current.position)
            current = current.parent
        
        return list(reversed(path))

    def _get_neighbors(self, node: Node, goal: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        """Get valid neighboring positions with improved obstacle avoidance."""
        x, y, z = node.position
        neighbors = []
        
        # Calculate grid coordinates for current position
        curr_grid_x = int(x / self.nav_mesh.cell_size)
        curr_grid_y = int(y / self.nav_mesh.cell_size)
        
        # Check if current position is on stairs
        curr_elev = self.nav_mesh.elevation[curr_grid_y, curr_grid_x]
        on_stairs = curr_elev > 0.01
        print(f"\nChecking neighbors for position ({x:.1f}, {y:.1f}, {z:.1f})")
        print(f"Current elevation: {curr_elev:.2f}, on_stairs: {on_stairs}")
        
        # Determine step sizes based on context
        if on_stairs:
            # Smaller steps on stairs for finer control
            step_sizes = [0.25]  # Single small step size for more precise control
        else:
            step_sizes = [1.0]  # Normal step size
        
        # Check all 8 directions
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),  # Cardinal directions
            (1, 1), (-1, 1), (1, -1), (-1, -1)  # Diagonals
        ]
        
        # Get goal elevation for smarter pathfinding
        goal_x = int(goal[0] / self.nav_mesh.cell_size)
        goal_y = int(goal[1] / self.nav_mesh.cell_size)
        goal_elev = self.nav_mesh.elevation[goal_y, goal_x]
        
        for step_size in step_sizes:
            for dx, dy in directions:
                new_x = x + dx * self.nav_mesh.cell_size * step_size
                new_y = y + dy * self.nav_mesh.cell_size * step_size
                
                # Skip if out of bounds
                if not (0 <= new_x < self.nav_mesh.width and 0 <= new_y < self.nav_mesh.height):
                    continue
                
                # Get elevation at new position
                new_grid_x = int(new_x / self.nav_mesh.cell_size)
                new_grid_y = int(new_y / self.nav_mesh.cell_size)
                new_elev = self.nav_mesh.elevation[new_grid_y, new_grid_x]
                
                # Skip if not walkable
                if not self.nav_mesh.is_walkable(new_x, new_y):
                    print(f"Position ({new_x:.1f}, {new_y:.1f}) not walkable")
                    continue
                
                # Use grid elevation for z-coordinate when on stairs
                if on_stairs:
                    new_z = new_elev
                else:
                    new_z = self.nav_mesh.get_elevation(new_x, new_y)
                
                # Check elevation difference
                elev_diff = abs(new_z - z)
                
                # More lenient elevation checks on stairs
                if on_stairs:
                    # Allow larger steps when moving towards goal elevation
                    if goal_elev > z and new_z > z:  # Going up
                        max_step = 0.5
                    elif goal_elev < z and new_z < z:  # Going down
                        max_step = 0.5
                    else:
                        max_step = 0.3
                else:
                    max_step = 0.3
                
                if elev_diff > max_step:
                    print(f"Elevation difference too large: {elev_diff:.2f} > {max_step:.2f} at ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")
                    continue
                
                # Check for collisions
                if self.nav_mesh.collision_detector and self.nav_mesh.collision_detector.check_collision(
                    node.position, (new_x, new_y, new_z)
                ):
                    print(f"Collision detected at ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")
                    continue
                
                # Add valid neighbor
                neighbors.append((new_x, new_y, new_z))
                print(f"Added neighbor: ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")
        
        return neighbors

class CollisionDetector:
    """Handles collision detection between objects."""
    def __init__(self, nav_mesh: NavigationMesh):
        self.nav_mesh = nav_mesh
    
    def check_collision(self, start: Tuple[float, float, float], 
                       end: Tuple[float, float, float]) -> bool:
        """Check if there is a collision between start and end points."""
        x1, y1, z1 = start
        x2, y2, z2 = end
        
        # Get direction vector
        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance == 0:
            return False
            
        # Normalize direction
        dx /= distance
        dy /= distance
        dz /= distance
        
        # Check points along the path
        steps = int(distance / (self.nav_mesh.cell_size * 0.5))
        steps = max(steps, 1)  # At least 1 step
        
        for i in range(steps + 1):
            t = i * distance / steps
            x = x1 + dx * t
            y = y1 + dy * t
            z = z1 + dz * t
            
            # Convert to grid coordinates
            grid_x = int(x / self.nav_mesh.cell_size)
            grid_y = int(y / self.nav_mesh.cell_size)
            
            # Check bounds
            if not (0 <= grid_x < self.nav_mesh.grid_width and 0 <= grid_y < self.nav_mesh.grid_height):
                return True
                
            # Check if walkable
            if not self.nav_mesh.walkable[grid_y, grid_x]:
                return True
                
            # Get ground elevation at this point
            ground_z = self.nav_mesh.get_elevation(x, y)
            
            # Allow movement along stairs/ramps
            if abs(z - ground_z) <= 2.0:  # More lenient for stairs/ramps
                continue
                
            # Prevent moving too far above or below ground
            if z < ground_z - 0.1 or z > ground_z + 3.0:
                return True
                
        return False
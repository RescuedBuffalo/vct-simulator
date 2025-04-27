from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math
import random


@dataclass
class Player:
    # Identity & Role
    id: str
    name: str
    team_id: str
    role: str  # duelist, controller, sentinel, initiator
    agent: str

    # Combat Stats
    aim_rating: float  # 0-100
    reaction_time: float  # in ms
    movement_accuracy: float  # affects shooting while moving
    spray_control: float  # affects rifle performance
    clutch_iq: float  # affects decision-making under pressure

    # Status
    location: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))  # 3D map coordinates (x, y, z)
    direction: float = 0.0  # degrees
    health: int = 100
    armor: int = 0
    alive: bool = True
    is_planting: bool = False
    is_defusing: bool = False
    plant_progress: float = 0.0  # Time spent planting so far
    defuse_progress: float = 0.0  # Time spent defusing so far
    is_looking_at_player: bool = False  # Whether player is currently looking at another player (for flash effects)
    
    # Movement physics
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (vx, vy, vz) in units per second
    acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (ax, ay, az) in units per second²
    max_speed: float = 5.5  # Maximum movement speed when running
    walk_speed: float = 3.5  # Slower movement when walking (Shift)
    crouch_speed: float = 2.0  # Speed when crouched (Ctrl)
    friction: float = 8.0  # Deceleration when not providing input
    acceleration_rate: float = 60.0  # How quickly player accelerates to max speed
    is_walking: bool = False  # Shift key pressed
    is_crouching: bool = False  # Ctrl key pressed
    is_moving: bool = False  # Any movement input active
    is_jumping: bool = False  # Jump in progress
    is_falling: bool = False  # Falling after a jump or from a height
    jump_height: float = 0.5  # Maximum height of jump in units
    jump_speed: float = 7.0  # Initial vertical velocity when jumping
    gravity: float = 20.0  # Gravitational acceleration
    movement_direction: Optional[Tuple[float, float]] = None  # Normalized direction vector (horizontal only)
    radius: float = 0.5  # Player collision radius
    height: float = 1.0  # Player height for vertical collision
    ground_contact: bool = True  # Whether player is touching the ground
    last_ground_z: float = 0.0  # Z coordinate when player was last on ground
    
    status_effects: List[str] = field(default_factory=list)  # "flashed", "slowed", "vulnerable", etc.

    # Utility Stats
    utility_knowledge: Dict[str, float] = field(default_factory=dict)  # e.g. {"smoke": 0.8, "flash": 0.6}
    utility_charges: Dict[str, int] = field(default_factory=dict)  # remaining uses per ability
    utility_cooldowns: Dict[str, float] = field(default_factory=dict)  # per ability (in seconds)
    utility_active: List[Dict] = field(default_factory=list)  # current deployed utility effects

    # Inventory
    creds: int = 800
    weapon: Optional[str] = None  # current main gun
    secondary: Optional[str] = "Classic"
    shield: Optional[str] = None  # "light", "heavy", or None
    spike: bool = False  # True if player has spike

    # Perception & Communication
    visible_enemies: List[str] = field(default_factory=list)
    heard_sounds: List[Dict] = field(default_factory=list)  # {"type": "footstep", "location": (x,y)}
    known_enemy_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # based on comms
    known_spike_location: Optional[Tuple[float, float]] = None
    comms_buffer: List[str] = field(default_factory=list)  # last 5-10 comms received

    # Performance
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    damage_dealt: int = 0
    damage_received: int = 0
    plants: int = 0
    defuses: int = 0
    ult_points: int = 0
    confidence: float = 0.5  # modifies behavior during duels

    # Kill Types
    # Headshot, Wallbang, First Blood, Clutch, etc.
    kill_types: Dict[str, int] = field(default_factory=dict)  # e.g. {"headshot": 10, "wallbang": 5, "first_blood": 1, "clutch": 20, "2k": 10, "3k": 5, "4k": 2, "5k": 1, "eco": 10}
    kill_streaks: Dict[str, int] = field(default_factory=dict)  # e.g. {"streak": 3, "longest_streak": 5}
    # Death Types
    # Killed by, Killed with, etc.
    death_types: Dict[str, int] = field(default_factory=dict)  # e.g. {"killed_by": 10, "killed_with": 5, "first_blood": 1, "clutch": 20, "2k": 10, "3k": 5, "4k": 2, "5k": 1, "eco": 10}
    death_streaks: Dict[str, int] = field(default_factory=dict)  # e.g. {"streak": 3, "longest_streak": 5}

    # Map Knowledge
    map_knowledge: Dict[str, float] = field(default_factory=dict)  # e.g. {"A": 0.8, "B": 0.6}
    map_strategic_points: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # e.g. {"A": (0.2, 0.3)}
    map_callouts: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # e.g. {"A": (0.2, 0.3)}

    # Team Knowledge
    team_knowledge: Dict[str, float] = field(default_factory=dict)  # e.g. {"A": 0.8, "B": 0.6}
    team_strategic_points: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # e.g. {"A": (0.2, 0.3)}
    team_callouts: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # e.g. {"A": (0.2, 0.3)}
    
    # Round Knowledge
    round_knowledge: Dict[str, float] = field(default_factory=dict)  # e.g. {"A": 0.8, "B": 0.6}
    round_strategic_points: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # e.g. {"A": (0.2, 0.3)}
    round_callouts: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # e.g. {"A": (0.2, 0.3)}    
    
    def reset_movement(self):
        """Reset player movement state."""
        self.velocity = (0.0, 0.0, 0.0)
        self.acceleration = (0.0, 0.0, 0.0)
        self.is_moving = False
        self.is_walking = False
        self.is_crouching = False
        self.is_jumping = False
        self.is_falling = False
        self.ground_contact = True
        self.movement_direction = None
    
    def get_current_max_speed(self) -> float:
        """Get the current maximum speed based on player state."""
        # Check for status effects that modify speed
        if "slowed" in self.status_effects:
            return self.max_speed * 0.6  # 60% of normal speed when slowed
        
        # In air movement is slightly slower
        if self.is_jumping or self.is_falling:
            return self.max_speed * 0.85  # 85% of normal speed when in air
            
        if self.is_crouching:
            return self.crouch_speed
        elif self.is_walking:
            return self.walk_speed
        else:
            return self.max_speed
    
    def set_movement_input(self, direction: Tuple[float, float], is_walking: bool = False, 
                          is_crouching: bool = False, is_jump_pressed: bool = False):
        """
        Set the player's movement input.
        
        Args:
            direction: A 2D vector (x, y) indicating the direction the player wants to move
            is_walking: Whether the player is holding the walk key (Shift)
            is_crouching: Whether the player is holding the crouch key (Ctrl)
            is_jump_pressed: Whether the player is pressing the jump key (Space)
        """
        # Normalize the direction vector if it's not zero
        if direction[0] != 0 or direction[1] != 0:
            magnitude = math.sqrt(direction[0]**2 + direction[1]**2)
            self.movement_direction = (direction[0] / magnitude, direction[1] / magnitude)
            self.is_moving = True
        else:
            self.movement_direction = None
            self.is_moving = False
            
        self.is_walking = is_walking
        self.is_crouching = is_crouching
        
        # Handle jump input
        if is_jump_pressed and self.ground_contact and not self.is_jumping and not self.is_falling:
            self.start_jump()
        
    def start_jump(self):
        """Start a jump by applying an initial upward velocity."""
        self.is_jumping = True
        self.ground_contact = False
        self.velocity = (self.velocity[0], self.velocity[1], self.jump_speed)
        self.last_ground_z = self.location[2]
        
    def update_movement(self, time_step: float, game_map):
        """
        Update player movement based on inputs, physics, and collisions.
        
        Args:
            time_step: Time since last update in seconds
            game_map: The Map object for collision detection
        """
        # Store the old position for collision resolution
        old_position = self.location
        
        # Get current max speed based on player state
        current_max_speed = self.get_current_max_speed()
        
        # Apply horizontal acceleration based on movement input
        if self.movement_direction and self.is_moving:
            # Calculate target velocity based on movement direction and max speed
            target_vx = self.movement_direction[0] * current_max_speed
            target_vy = self.movement_direction[1] * current_max_speed
            
            # Apply acceleration towards target velocity
            self.acceleration = (
                (target_vx - self.velocity[0]) * self.acceleration_rate,
                (target_vy - self.velocity[1]) * self.acceleration_rate,
                self.acceleration[2]
            )
        else:
            # Apply friction to slow down horizontal movement when not moving
            # Create a friction force opposite to velocity direction
            speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            if speed > 0:
                self.acceleration = (
                    -self.velocity[0] / speed * self.friction,
                    -self.velocity[1] / speed * self.friction,
                    self.acceleration[2]
                )
            else:
                self.acceleration = (0.0, 0.0, self.acceleration[2])
        
        # Apply gravity if not on ground
        if not self.ground_contact:
            self.acceleration = (
                self.acceleration[0],
                self.acceleration[1],
                -self.gravity
            )
        else:
            # Zero out vertical velocity and acceleration when on ground
            self.velocity = (self.velocity[0], self.velocity[1], 0.0)
            self.acceleration = (self.acceleration[0], self.acceleration[1], 0.0)
        
        # Update velocity based on acceleration
        new_vx = self.velocity[0] + self.acceleration[0] * time_step
        new_vy = self.velocity[1] + self.acceleration[1] * time_step
        new_vz = self.velocity[2] + self.acceleration[2] * time_step
        
        # Clamp horizontal velocity to max speed
        horiz_speed = math.sqrt(new_vx**2 + new_vy**2)
        if horiz_speed > current_max_speed:
            scale_factor = current_max_speed / horiz_speed
            new_vx *= scale_factor
            new_vy *= scale_factor
        
        # Store the new velocity
        self.velocity = (new_vx, new_vy, new_vz)
        
        # Calculate new position based on velocity
        new_x = self.location[0] + self.velocity[0] * time_step
        new_y = self.location[1] + self.velocity[1] * time_step
        new_z = self.location[2] + self.velocity[2] * time_step
        
        # If not jumping or falling, attempt to snap to ground/ramps/stairs elevation
        if not self.is_jumping and not self.is_falling:
            desired_elev = game_map.get_elevation_at_position(new_x, new_y)
            # allow elevation change only via ramp or stair
            if game_map.can_move(self.location[0], self.location[1], self.location[2],
                                 new_x, new_y, desired_elev):
                new_z = desired_elev
            else:
                # remain at current elevation when moving horizontally
                new_z = self.location[2]
        
        # Perform collision detection and resolution
        final_position = self._resolve_collisions(game_map, (new_x, new_y, new_z))
        
        # Update player position
        self.location = final_position
        
        # Determine if player is on ground
        old_ground_contact = self.ground_contact
        self.ground_contact = self._check_ground_contact(game_map)
        
        # If player wasn't on ground and now is, they've landed
        if not old_ground_contact and self.ground_contact:
            self._handle_landing()
        
        # If player is falling and not jumping, update state
        if not self.ground_contact and self.velocity[2] < 0:
            self.is_jumping = False
            self.is_falling = True
        
        # If player is on ground, they're not jumping or falling
        if self.ground_contact:
            self.is_jumping = False
            self.is_falling = False
        
        # If player didn't move to the expected position horizontally, they hit a wall
        # Adjust velocity to allow sliding along walls
        if final_position[0] != new_x or final_position[1] != new_y:
            self._adjust_velocity_for_wall_slide()
        
        # After crouch logic, set player height based on crouch state
        if self.is_crouching:
            self.height = 0.5
        else:
            self.height = 1.0
        
        # After updating self.location:
        # Force crouch if under a low-clearance object
        x, y, z = self.location
        forced_crouch = False
        for obj in game_map.objects.values():
            if obj.contains_point(x, y, z):
                clearance = obj.height_z
                # If clearance is >0.5 and <1.0, force crouch
                if 0.5 < clearance < 1.0:
                    forced_crouch = True
                    break
        if forced_crouch:
            self.is_crouching = True
        # Prevent uncrouching if not enough clearance above
        if self.is_crouching:
            for obj in game_map.objects.values():
                if obj.contains_point(x, y, z):
                    clearance = obj.height_z
                    if clearance < self.height:
                        self.is_crouching = True
                        break
    
    def _check_ground_contact(self, game_map) -> bool:
        """
        Check if player is on the ground or on a surface.
        
        Args:
            game_map: The Map object for collision detection
            
        Returns:
            True if player is on ground, False otherwise
        """
        # Check if player is at z=0 (ground level)
        if self.location[2] <= 0.0:
            return True
        
        # Check if player is on an elevated surface
        # Lookup platform or surface at player's position by checking the map
        position_x, position_y = self.location[0], self.location[1]
        for boundary in game_map.walls.values():
            # If player is directly above a platform and within a small distance
            if (boundary.contains_point(position_x, position_y) and 
                abs(self.location[2] - boundary.elevation) < 0.1):
                return True
                
        # Check stairs and ramps
        for stair in game_map.stairs.values():
            if stair.contains_point(position_x, position_y):
                # For stairs, interpolate the height based on position
                return True
        # Also consider ramps and objects and general elevation as ground
        # If player's z is near map surface elevation, count as on ground
        surface_elev = game_map.get_elevation_at_position(position_x, position_y)
        if abs(self.location[2] - surface_elev) < 0.1:
            return True
        
        return False
    
    def _handle_landing(self):
        """Handle the effects of landing after a jump or fall."""
        # Calculate fall distance
        fall_distance = self.last_ground_z - self.location[2]
        
        # Check for fall damage (if falling more than 1.5 units)
        if fall_distance > 1.5:
            damage = int((fall_distance - 1.5) * 25)  # 25 damage per unit after 1.5
            self.health -= min(damage, self.health)  # Don't go below 0 health
            
            # Check if player died from fall damage
            if self.health <= 0:
                self.alive = False
                self.deaths += 1
                
        # Reset vertical velocity
        self.velocity = (self.velocity[0], self.velocity[1], 0.0)
    
    def _resolve_collisions(self, game_map, new_position: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Detect and resolve collisions with the map.
        
        Args:
            game_map: The Map object for collision detection
            new_position: The desired new position (x, y, z)
            
        Returns:
            The final position after collision resolution
        """
        # Extract components
        new_x, new_y, new_z = new_position
        
        # Prevent falling below ground level
        if new_z < 0:
            new_z = 0
            self.ground_contact = True
            
        # Check if the new horizontal position is valid
        if game_map.is_valid_position(new_x, new_y, new_z, self.radius, self.height):
            # Check for vertical obstacles (ceilings, etc.)
            if self._check_vertical_clearance(game_map, new_x, new_y, new_z):
                return (new_x, new_y, new_z)
            else:
                # Hit ceiling, stop upward movement
                if self.velocity[2] > 0:
                    self.velocity = (self.velocity[0], self.velocity[1], 0)
                return (new_x, new_y, self.location[2])
        
        # If not valid horizontally, try to slide along walls
        
        # First, try moving only in X direction
        if game_map.is_valid_position(new_x, self.location[1], new_z, self.radius, self.height):
            # Check vertical clearance
            if self._check_vertical_clearance(game_map, new_x, self.location[1], new_z):
                return (new_x, self.location[1], new_z)
            else:
                return (new_x, self.location[1], self.location[2])
        
        # If X fails, try moving only in Y direction
        if game_map.is_valid_position(self.location[0], new_y, new_z, self.radius, self.height):
            # Check vertical clearance
            if self._check_vertical_clearance(game_map, self.location[0], new_y, new_z):
                return (self.location[0], new_y, new_z)
            else:
                return (self.location[0], new_y, self.location[2])
        
        # If both fail, we're stuck in a corner - stay at current position for x,y
        # But still allow vertical movement if there's clearance
        if self._check_vertical_clearance(game_map, self.location[0], self.location[1], new_z):
            return (self.location[0], self.location[1], new_z)
        else:
            return self.location
    
    def _check_vertical_clearance(self, game_map, x: float, y: float, z: float) -> bool:
        """
        Check if there's enough vertical clearance at the given position.
        
        Args:
            game_map: The Map object
            x, y, z: The position to check
            
        Returns:
            True if there's enough clearance, False otherwise
        """
        # Check for ceiling collisions
        # For each wall or object that could be above the player
        for obj in list(game_map.walls.values()) + list(game_map.objects.values()):
            # If this object is above the player position and player's head would hit it
            if (obj.contains_point(x, y) and 
                obj.elevation > 0 and 
                z + self.height > obj.elevation):
                return False
                
        # No ceiling collisions found
        return True
    
    def _adjust_velocity_for_wall_slide(self):
        """Adjust velocity for wall sliding when a collision occurs."""
        # Check if we're moving in X direction
        if abs(self.velocity[0]) > 0.01 and self.location[0] != self.location[0] + self.velocity[0]:
            # We hit a wall in X direction, zero out X velocity
            self.velocity = (0.0, self.velocity[1], self.velocity[2])
        
        # Check if we're moving in Y direction
        if abs(self.velocity[1]) > 0.01 and self.location[1] != self.location[1] + self.velocity[1]:
            # We hit a wall in Y direction, zero out Y velocity
            self.velocity = (self.velocity[0], 0.0, self.velocity[2])
    
    def can_climb_to(self, game_map, position: Tuple[float, float, float]) -> bool:
        """
        Check if player can climb/jump to a position.
        
        Args:
            game_map: The Map object
            position: The target position (x, y, z)
            
        Returns:
            True if player can reach the position, False otherwise
        """
        # Check if the height difference is within jump range
        z_diff = position[2] - self.location[2]
        
        # Can't jump higher than jump_height
        if z_diff > self.jump_height:
            return False
            
        # Check if horizontal position is reachable
        horizontal_dist = math.sqrt(
            (position[0] - self.location[0])**2 + 
            (position[1] - self.location[1])**2
        )
        
        # Simple approximation: max horizontal distance decreases as jump height increases
        max_horizontal_dist = 2.0 * (1.0 - (z_diff / self.jump_height))
        
        return horizontal_dist <= max_horizontal_dist

    @property
    def z_position(self) -> float:
        """Get the current z-coordinate of the player."""
        return self.location[2]

    @property
    def in_air(self) -> bool:
        """Return True if the player is currently in the air (jumping or falling)."""
        return not self.ground_contact

    def is_on_ground(self) -> bool:
        """Return True if the player is on the ground."""
        return self.ground_contact

    def intersect_ray(self, origin: Tuple[float, float, float], direction: Tuple[float, float, float]) -> Optional[float]:
        """Return the distance t along the ray at which it intersects this player's sphere, or None if no intersection."""
        ox, oy, oz = origin
        dx, dy, dz = direction
        cx, cy, cz0 = self.location
        czc = cz0 + self.height * 0.5  # Use center of player for sphere center
        r = self.radius
        
        # Vector from ray origin to sphere center
        ocx, ocy, ocz = ox - cx, oy - cy, oz - czc
        
        # Compute coefficients for quadratic equation
        # a = dot(direction, direction)
        a = dx*dx + dy*dy + dz*dz
        if a < 1e-10:  # Direction vector is too small
            return None
            
        # b = 2 * dot(direction, origin-center)
        b = 2.0 * (dx*ocx + dy*ocy + dz*ocz)
        
        # c = dot(origin-center, origin-center) - r^2
        c = ocx*ocx + ocy*ocy + ocz*ocz - r*r
         
        # Compute discriminant
        disc = b*b - 4*a*c
        
        # No real solutions (ray misses sphere)
        if disc < 1e-10:
            return None
            
        # Compute the square root of the discriminant
        sqrt_disc = math.sqrt(disc)
        
        # Compute the two solutions
        t1 = (-b - sqrt_disc) / (2.0 * a)
        t2 = (-b + sqrt_disc) / (2.0 * a)
        
        # Return the nearest non-negative intersection
        if t1 >= 0.0001:  # Small epsilon to avoid numerical issues
            return t1
        elif t2 >= 0.0001:
            return t2
        else:
            return None

    def apply_damage(self, raw: int) -> int:
        """Apply raw damage to this player, considering armor, return actual damage inflicted."""
        damage = raw
        if self.armor > 0:
            absorbed = min(self.armor, damage)
            self.armor -= absorbed
            damage -= absorbed
        if damage > 0:
            self.health -= damage
        if self.health <= 0 and self.alive:
            self.alive = False
            self.deaths += 1
        return damage

    def reset_ability_charges(self):
        """Reset all ability charges to max (should be called at round start)."""
        if hasattr(self, 'abilities') and hasattr(self.abilities, 'reset_charges'):
            self.abilities.reset_charges()
        else:
            # Fallback: reset utility_charges to some default if available
            for k in self.utility_charges:
                self.utility_charges[k] = 1  # or set to max if known

    def increment_ult_points(self, amount: int = 1, max_ult: int = 7):
        """Increment ult points, up to a max (default 7)."""
        self.ult_points = min(self.ult_points + amount, max_ult)

    def spend_ult_point(self, amount: int = 1):
        """Spend ult points if available."""
        if self.ult_points >= amount:
            self.ult_points -= amount
            return True
        return False

    def add_orb_pickup(self, max_ult: int = 7):
        """Handle orb pickup (increment ult points)."""
        self.increment_ult_points(1, max_ult)

def map_orm_player_to_sim_player(orm_player: 'OrmPlayer') -> Player:
    """
    Convert a SQLAlchemy Player model into the simulation Player dataclass.
    Only populates fields available in the ORM model.
    """
    return Player(
        id=orm_player.id,
        name=orm_player.gamer_tag,
        team_id=orm_player.team_id or "",
        role=orm_player.primary_role,
        agent="",  # Will be assigned later
        aim_rating=orm_player.aim,
        reaction_time=200.0,  # Default value in ms
        movement_accuracy=orm_player.movement,
        spray_control=orm_player.aim * 0.8,  # Derived from aim
        clutch_iq=orm_player.clutch,
        location=(0.0, 0.0, 0.0),  # Starting position with z-coordinate
        direction=0.0,  # Starting direction
    )
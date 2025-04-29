from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Type
from enum import Enum
import math
import uuid
import time
import random

class AbilityType(Enum):
    """Types of abilities in Valorant."""
    FLASH = "flash"
    SMOKE = "smoke"
    MOLLY = "molly"
    RECON = "recon"
    TRAP = "trap"
    HEAL = "heal"
    MOVEMENT = "movement"
    COMBAT = "combat"

class AbilityTarget(Enum):
    """How an ability is targeted."""
    POINT = "point"  # Direct point target (e.g., Brimstone smokes)
    PROJECTILE = "projectile"  # Thrown/shot (e.g., Phoenix flash)
    SELF = "self"  # Self-cast (e.g., Jett dash)
    AREA = "area"  # Area selection (e.g., Viper wall)
    INSTANT = "instant"  # No targeting needed (e.g., Reyna dismiss)

@dataclass
class AbilityDefinition:
    """
    Defines the base characteristics of an ability.
    This is the template for what an ability can do.
    """
    # Basic Info
    name: str
    description: str
    ability_type: AbilityType
    targeting_type: AbilityTarget
    is_ultimate: bool = False
    
    # Costs and Charges
    credit_cost: int = 0
    max_charges: int = 1
    ult_points_required: int = 0  # Only for ultimates
    
    # Timing
    cast_time: float = 0.0  # Time to activate in seconds
    duration: float = 0.0  # How long effect lasts (0 for instant)
    cooldown: float = 0.0  # Time between uses
    
    # Effect Range
    effect_radius: float = 0.0  # Radius of effect
    max_range: float = 0.0  # Maximum cast/throw range
    
    # Effect Values
    damage: float = 0.0  # Damage per second for damaging abilities
    healing: float = 0.0  # Healing amount for healing abilities
    
    # Special Effects
    status_effects: List[str] = field(default_factory=list)  # e.g., "flashed", "slowed", "vulnerable"
    blocks_vision: bool = False
    reveals_enemies: bool = False
    destroyable: bool = False
    
    # Sound
    sound_range: float = 35.0  # Default from game constants
    
    # Visual
    color: Optional[Tuple[int, int, int]] = None  # RGB color for ability visualization
    
    # Special Properties (for unique ability behaviors)
    properties: Dict[str, any] = field(default_factory=dict)
    # Instance subclass for this ability
    instance_class: Optional[Type['AbilityInstance']] = None
    # Effect geometry: 'circle' or 'rect'
    shape: str = 'circle'
    shape_params: Tuple[float, ...] = field(default_factory=tuple)  # e.g. (radius,) or (width, height)
    # Vertical extent of the effect (units)
    height: float = 0.0

    def __post_init__(self):
        # Choose default instance class based on targeting type if not provided
        if self.instance_class is None:
            if self.targeting_type == AbilityTarget.PROJECTILE:
                self.instance_class = ProjectileAbilityInstance
            else:
                self.instance_class = AreaAbilityInstance
        # Default geometry parameters for circle
        if self.shape == 'circle' and not self.shape_params:
            self.shape_params = (self.effect_radius,)
        if not self.status_effects:
            # Set default status effects based on type
            if self.ability_type == AbilityType.FLASH:
                self.status_effects = ["flashed"]
            elif self.ability_type == AbilityType.SMOKE:
                self.status_effects = ["smoked"]
            elif self.ability_type == AbilityType.MOLLY:
                self.status_effects = ["burning"]
            elif self.ability_type == AbilityType.TRAP:
                self.status_effects = ["revealed"]

    def create_instance(self, owner_id: str) -> 'AbilityInstance':
        """Factory to create a fresh ability instance for a given owner."""
        return self.instance_class(
            definition=self,
            owner_id=owner_id,
            instance_id=str(uuid.uuid4()),
            charges_remaining=self.max_charges
        )

    def __repr__(self) -> str:
        return (f"AbilityDefinition(name={self.name!r}, type={self.ability_type}, "
                f"target={self.targeting_type}, shape={self.shape}, params={self.shape_params}, height={self.height})")

@dataclass
class AbilityInstance:
    """
    An instance of an ability being used in the game.
    This represents an actual ability usage with its current state.
    """
    # Reference to definition
    definition: AbilityDefinition
    
    # Instance state
    owner_id: str
    instance_id: str
    charges_remaining: int
    is_active: bool = False
    cooldown_remaining: float = 0.0
    
    # Current projectile position (3D) and state
    origin: Optional[Tuple[float, float, float]] = None
    direction3d: Optional[Tuple[float, float, float]] = None
    velocity3d: Optional[Tuple[float, float, float]] = None
    current_position3d: Optional[Tuple[float, float, float]] = None
    range_traveled: float = 0.0                  # distance traveled so far
    effect_applied: bool = False                 # area effect deployed
    # Current effect
    current_position: Optional[Tuple[float, float]] = None
    affected_players: Set[str] = field(default_factory=set)
    start_time: float = 0.0
    end_time: Optional[float] = None
    
    # For projectile-based abilities
    trajectory: List[Tuple[float, float]] = field(default_factory=list)
    velocity: Optional[Tuple[float, float]] = None

    def __post_init__(self):
        """Initialize base ability state."""
        pass

    def activate(self, current_time: float, origin: Tuple[float, float, float], direction: Tuple[float, float, float]):
        """Activate this ability: handle cast/formation, projectile launch, or immediate area effect."""
        self.is_active = True
        # Account for any cast_time (formation_time)
        cast_delay = self.definition.cast_time or self.definition.properties.get('formation_time', 0.0)
        self.start_time = current_time
        # End of ability effect
        self.end_time = current_time + self.definition.duration
        # Store origin and direction in 3D
        self.origin = origin
        self.direction3d = direction
        # Initialize projectile if needed
        speed = self.definition.properties.get('projectile_speed', 0.0)
        vx = direction[0] * speed
        vy = direction[1] * speed
        vz = direction[2] * speed
        self.velocity3d = (vx, vy, vz)
        # Initialize position and trajectory
        self.current_position3d = origin
        self.trajectory = [origin]
        # Reset range and effect flag
        self.range_traveled = 0.0
        self.effect_applied = False
        # Consume a charge and set cooldown
        self.charges_remaining = max(0, self.charges_remaining - 1)
        self.cooldown_remaining = self.definition.cooldown

    def apply_effect(self, game_map: Any, players: List[Any]):
        """Deploy the ability's effect (damage, status, vision_block, etc.) at current position."""
        if not self.current_position3d:
            return
        x, y, z = self.current_position3d
        # Area effect
        affected = False
        for p in players:
            px, py, pz = p.location
            dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
            if dist <= self.definition.effect_radius:
                # Damage
                if self.definition.damage > 0:
                    p.apply_damage(int(self.definition.damage))
                # Healing
                if self.definition.healing > 0:
                    p.health = min(p.health + int(self.definition.healing), 100)
                # Status effects
                for status in self.definition.status_effects:
                    if status not in p.status_effects:
                        p.status_effects.append(status)
                self.affected_players.add(p.id)
                affected = True
        # Set effect_applied if any player was affected or if it's a non-player-affecting ability
        self.effect_applied = affected or self.definition.blocks_vision

    def is_available(self) -> bool:
        """Check if ability can be used."""
        return (
            self.charges_remaining > 0 and
            self.cooldown_remaining <= 0 and
            not self.is_active
        )
    
    def get_remaining_duration(self, current_time: float) -> float:
        """Get remaining duration of active ability."""
        if not self.is_active or not self.end_time:
            return 0.0
        return max(0.0, self.end_time - current_time)

    def update(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        """Progress cooldown, scheduling and delegate simulation to tick() hook."""
        # Cooldown countdown
        if self.cooldown_remaining > 0:
            self.cooldown_remaining = max(0.0, self.cooldown_remaining - time_step)
        # Not yet time to start
        if current_time < self.start_time:
            return
        # Delegate to subclass
        self.tick(time_step, current_time, game_map, players)
        # Expire if duration passed
        if current_time >= self.end_time:
            self.is_active = False

    def tick(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        """Subclass hook to implement per-frame behavior."""
        pass

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(def={self.definition.name}, active={self.is_active}, "
                f"pos={self.current_position3d or self.origin}, charges={self.charges_remaining})")

# Helper functions to create common ability definitions
def create_smoke_ability(name: str, radius: float = 5.0, duration: float = 15.0) -> AbilityDefinition:
    """Create a smoke ability definition."""
    return AbilityDefinition(
        name=name,
        description=f"Creates a smoke cloud with radius {radius}m that lasts {duration}s",
        ability_type=AbilityType.SMOKE,
        targeting_type=AbilityTarget.POINT,
        duration=duration,
        effect_radius=radius,
        blocks_vision=True,
        shape='circle',
        shape_params=(radius,),
        height=4.0,  # Standard smoke height
        instance_class=SmokeAbilityInstance,
        cast_time=0.5  # Add formation time
    )

def create_flash_ability(name: str, duration: float = 1.0) -> AbilityDefinition:
    """Create a flash ability definition."""
    return AbilityDefinition(
        name=name,
        description=f"Creates a flash that blinds players for {duration}s",
        ability_type=AbilityType.FLASH,
        targeting_type=AbilityTarget.PROJECTILE,
        duration=duration,
        effect_radius=10.0,  # Flash radius
        max_range=30.0,  # Maximum throw distance
        instance_class=FlashAbilityInstance,
        properties={
            'projectile_speed': 15.0,
            'affected_by_gravity': True,
            'gravity_strength': 9.8,
            'bounce_count': 1,
            'bounce_efficiency': 0.6
        }
    )

def create_molly_ability(name: str, radius: float = 5.0, duration: float = 7.0, damage: float = 8.0) -> AbilityDefinition:
    """Create a molly ability definition."""
    return AbilityDefinition(
        name=name,
        description=f"Creates a damaging area with radius {radius}m that deals {damage} damage per second for {duration}s",
        ability_type=AbilityType.MOLLY,
        targeting_type=AbilityTarget.PROJECTILE,
        duration=duration,
        effect_radius=radius,
        damage=damage,
        max_range=30.0,  # Maximum throw distance
        instance_class=MollyAbilityInstance,
        properties={
            'projectile_speed': 15.0,
            'affected_by_gravity': True,
            'gravity_strength': 9.8,
            'bounce_count': 1,
            'bounce_efficiency': 0.6
        }
    )

def create_recon_ability(name: str, radius: float = 10.0, duration: float = 8.0) -> AbilityDefinition:
    ad = AbilityDefinition(
        name=name,
        description="Reveals enemies in its radius",
        ability_type=AbilityType.RECON,
        targeting_type=AbilityTarget.PROJECTILE,
        duration=duration,
        effect_radius=radius,
        cooldown=45.0,
        max_charges=1,
        reveals_enemies=True,
        properties={
            "projectile_speed": 20.0,
            "affected_by_gravity": False,
            "pulse_interval": 1.5,
            "reveal_duration": 3.0
        }
    )
    ad.instance_class = ReconAbilityInstance
    return ad

def create_heal_ability(name: str, radius: float = 3.0, duration: float = 5.0, healing: float = 5.0) -> AbilityDefinition:
    ad = AbilityDefinition(
        name=name,
        description="Heals allies in the area",
        ability_type=AbilityType.HEAL,
        targeting_type=AbilityTarget.AREA,
        duration=duration,
        effect_radius=radius,
        cooldown=45.0,
        max_charges=1,
        healing=healing,
        properties={}
    )
    ad.instance_class = AreaAbilityInstance
    return ad

@dataclass
class ProjectileAbilityInstance(AbilityInstance):
    """Handles abilities that launch a projectile (thrown or shot)."""
    bounces_remaining: int = 0
    
    def __post_init__(self):
        """Initialize projectile-specific state."""
        super().__post_init__()
        self.bounces_remaining = self.definition.properties.get('bounce_count', 0)
    
    def tick(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        """Update projectile position and check for collisions."""
        # Skip if not active or already applied
        if not self.is_active or self.effect_applied:
            return
            
        # Wait for activation delay
        if current_time < self.start_time:
            return
            
        # Move projectile
        if self.velocity3d and self.current_position3d:
            x, y, z = self.current_position3d
            vx, vy, vz = self.velocity3d
            
            # Apply gravity if needed
            if self.definition.properties.get('affected_by_gravity', False):
                g = self.definition.properties.get('gravity_strength', 9.8)
                vz -= g * time_step
                self.velocity3d = (vx, vy, vz)
            
            # Update position
            new_x = x + vx * time_step
            new_y = y + vy * time_step
            new_z = z + vz * time_step
            self.current_position3d = (new_x, new_y, new_z)
            self.trajectory.append(self.current_position3d)
            
            # Check collision
            if game_map:
                hit_point = game_map.check_collision(
                    (x, y, z),
                    (new_x, new_y, new_z)
                )
                if hit_point:
                    # Handle bounce
                    if self.bounces_remaining > 0:
                        self.bounces_remaining -= 1
                        # Simple reflection - could be more sophisticated
                        self.velocity3d = (-vx, -vy, vz)
                    else:
                        # Apply effect at collision point
                        self.current_position3d = hit_point
                        self.apply_effect(game_map, players)
                        self.effect_applied = True
            
            # Check max range
            self.range_traveled += math.sqrt((new_x - x)**2 + (new_y - y)**2 + (new_z - z)**2)
            if self.range_traveled >= self.definition.max_range:
                self.apply_effect(game_map, players)
                self.effect_applied = True

@dataclass
class AreaAbilityInstance(AbilityInstance):
    """Handles abilities that apply effects instantly or in an area."""
    def tick(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        """Apply area effect and maintain it."""
        # Skip if not active
        if not self.is_active:
            return
            
        # Wait for formation time
        if current_time < self.start_time:
            return
            
        # Apply initial effect
        if not self.effect_applied:
            self.apply_effect(game_map, players)
            self.effect_applied = True
        
        # Continue applying effect to players in area
        if self.current_position3d:
            x, y, z = self.current_position3d
            for player in players:
                px, py, pz = player.location
                dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
                if dist <= self.definition.effect_radius:
                    # Apply continuous effects
                    if self.definition.damage > 0:
                        player.apply_damage(int(self.definition.damage * time_step))
                    if self.definition.healing > 0:
                        player.health = min(100, player.health + int(self.definition.healing * time_step))
                    # Add to affected players
                    self.affected_players.add(player.id)
                    # Apply status effects
                    for status in self.definition.status_effects:
                        if status not in player.status_effects:
                            player.status_effects.append(status)

@dataclass
class FlashAbilityInstance(ProjectileAbilityInstance):
    """Flash ability that blinds players looking at it."""
    def apply_effect(self, game_map: Any, players: List[Any]):
        """Apply flash effect to players in range."""
        if not self.current_position3d:
            return
            
        x, y, z = self.current_position3d
        affected = False
        for player in players:
            px, py, pz = player.location
            # Check if in range
            dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
            if dist <= self.definition.effect_radius:
                # Check if player is looking at flash
                dx = x - px
                dy = y - py
                dz = z - pz
                # Normalize direction to flash
                length = math.sqrt(dx*dx + dy*dy + dz*dz)
                if length > 0:
                    dx, dy, dz = dx/length, dy/length, dz/length
                    # Get dot product with player view direction
                    dot = (dx * player.view_direction[0] +
                          dy * player.view_direction[1] +
                          dz * player.view_direction[2])
                    # If player is looking towards flash (dot product > 0)
                    if dot > 0:
                        self.affected_players.add(player.id)
                        if 'flashed' not in player.status_effects:
                            player.status_effects.append('flashed')
                        affected = True
        self.effect_applied = True  # Flash always applies its effect

@dataclass
class SmokeAbilityInstance(AreaAbilityInstance):
    """Smoke ability that blocks vision in an area."""
    def apply_effect(self, game_map: Any, players: List[Any]):
        """Apply smoke effect to players in range."""
        if not self.current_position3d:
            return
            
        x, y, z = self.current_position3d
        affected = False
        for player in players:
            px, py, pz = player.location
            dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
            if dist <= self.definition.effect_radius:
                self.affected_players.add(player.id)
                if 'smoked' not in player.status_effects:
                    player.status_effects.append('smoked')
                affected = True
        self.effect_applied = affected or self.definition.blocks_vision

@dataclass
class MollyAbilityInstance(ProjectileAbilityInstance):
    """Molly ability that creates a damaging area."""
    def apply_effect(self, game_map: Any, players: List[Any]):
        """Apply molly damage to players in range."""
        if not self.current_position3d:
            return
            
        x, y, z = self.current_position3d
        affected = False
        for player in players:
            px, py, pz = player.location
            dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
            if dist <= self.definition.effect_radius:
                # Apply initial damage
                damage = int(self.definition.damage)
                player.apply_damage(damage)
                # Add burning status
                if 'burning' not in player.status_effects:
                    player.status_effects.append('burning')
                self.affected_players.add(player.id)
                affected = True
        self.effect_applied = True  # Molly always applies its effect

    def tick(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        """Update molly and apply damage over time."""
        # Skip if not active or not yet started
        if not self.is_active or current_time < self.start_time:
            return
            
        # Apply damage to players in area
        if self.current_position3d:
            x, y, z = self.current_position3d
            for player in players:
                px, py, pz = player.location
                dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
                if dist <= self.definition.effect_radius:
                    # Apply damage over time
                    damage = int(self.definition.damage * time_step)
                    player.apply_damage(damage)
                    # Add burning status
                    if 'burning' not in player.status_effects:
                        player.status_effects.append('burning')
                    self.affected_players.add(player.id)

@dataclass
class ReconAbilityInstance(ProjectileAbilityInstance):
    """Recon dart that pulses to reveal enemies in its radius periodically."""
    pulse_timer: float = 0.0
    def update(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        super().update(time_step, current_time, game_map, players)
        if self.effect_applied and current_time < self.end_time:
            # Pulse interval
            interval = self.definition.properties.get('pulse_interval', 1.0)
            self.pulse_timer += time_step
            if self.pulse_timer >= interval:
                self.pulse_timer -= interval
                # Reveal all players
                affected = False
                for p in players:
                    if p.id not in self.affected_players:
                        px, py, pz = p.location
                        dx = px - self.current_position3d[0]
                        dy = py - self.current_position3d[1]
                        if math.sqrt(dx*dx + dy*dy) <= self.definition.effect_radius:
                            # Mark revealed
                            p.status_effects.append('revealed')
                            self.affected_players.add(p.id)
                            affected = True
                self.effect_applied = affected

# Standard ability definitions
STANDARD_ABILITIES = {
    "flash": AbilityDefinition(
        name="Flash",
        description="Blinds enemies who look at it",
        ability_type=AbilityType.FLASH,
        targeting_type=AbilityTarget.PROJECTILE,
        max_charges=2,
        credit_cost=200,
        cast_time=0.2,
        duration=1.5,
        effect_radius=10.0,
        max_range=30.0,
        status_effects=["flashed"],
        properties={
            "bounce_count": 1,
            "activation_delay": 0.2,
            "projectile_speed": 20.0,
            "affected_by_gravity": True
        }
    ),
    "smoke": AbilityDefinition(
        name="Smoke",
        description="Creates a vision-blocking smoke cloud",
        ability_type=AbilityType.SMOKE,
        targeting_type=AbilityTarget.POINT,
        max_charges=3,
        credit_cost=100,
        cast_time=0.5,
        duration=15.0,
        effect_radius=5.0,
        max_range=40.0,
        blocks_vision=True,
        status_effects=["smoked"],
        properties={
            "formation_time": 0.5
        }
    ),
    "molly": AbilityDefinition(
        name="Molly",
        description="Creates a damaging area of effect",
        ability_type=AbilityType.MOLLY,
        targeting_type=AbilityTarget.PROJECTILE,
        max_charges=2,
        credit_cost=200,
        cast_time=0.2,
        duration=7.0,
        effect_radius=5.0,
        max_range=25.0,
        damage=8.0,
        status_effects=["burning"],
        properties={
            "projectile_speed": 15.0,
            "affected_by_gravity": True,
            "gravity_strength": 9.8,
            "can_bounce": True,
            "bounce_efficiency": 0.6,
            "max_bounces": 2
        }
    ),
    "recon": AbilityDefinition(
        name="Recon",
        description="Reveals enemies in its radius",
        ability_type=AbilityType.RECON,
        targeting_type=AbilityTarget.PROJECTILE,
        max_charges=2,
        credit_cost=150,
        cast_time=0.2,
        duration=8.0,
        effect_radius=10.0,
        max_range=35.0,
        reveals_enemies=True,
        status_effects=["revealed"],
        properties={
            "pulse_interval": 1.0,
            "projectile_speed": 25.0,
            "affected_by_gravity": True
        }
    ),
    "trap": AbilityDefinition(
        name="Trap",
        description="Places a trap that reveals enemies",
        ability_type=AbilityType.TRAP,
        targeting_type=AbilityTarget.POINT,
        max_charges=2,
        credit_cost=200,
        cast_time=0.5,
        duration=45.0,
        effect_radius=3.0,
        max_range=5.0,
        reveals_enemies=True,
        status_effects=["revealed", "vulnerable"],
        properties={
            "trigger_radius": 2.0,
            "arm_time": 1.0
        }
    ),
    "heal": AbilityDefinition(
        name="Heal",
        description="Heals allies in radius",
        ability_type=AbilityType.HEAL,
        targeting_type=AbilityTarget.AREA,
        max_charges=1,
        credit_cost=200,
        cast_time=0.5,
        duration=5.0,
        effect_radius=3.0,
        healing=5.0,
        properties={
            "heal_interval": 1.0
        }
    )
}
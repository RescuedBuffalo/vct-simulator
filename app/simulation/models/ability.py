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
    STIM = "stim"
    HEAL = "heal"
    RECON = "recon"
    DISPLACEMENT = "displacement"  # Abilities that move players (e.g., Jett updraft)
    VISION_BLOCK = "vision_block"  # One-way smokes, walls
    TRAP = "trap"  # Cypher trips, Killjoy alarmbot
    ULTIMATE = "ultimate"

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
    status_effects: Set[str] = field(default_factory=set)  # e.g., "flashed", "slowed", "vulnerable"
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
    instance_class: Type['AbilityInstance'] = field(init=False)
    # Effect geometry: 'circle' or 'rect'
    shape: str = 'circle'
    shape_params: Tuple[float, ...] = field(default_factory=tuple)  # e.g. (radius,) or (width, height)
    # Vertical extent of the effect (units)
    height: float = 0.0

    def __post_init__(self):
        # Choose default instance class based on targeting type
        if self.targeting_type == AbilityTarget.PROJECTILE:
            self.instance_class = ProjectileAbilityInstance
        else:
            self.instance_class = AreaAbilityInstance
        # Default geometry parameters for circle
        if self.shape == 'circle' and not self.shape_params:
            self.shape_params = (self.effect_radius,)

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

    def activate(self, current_time: float, origin: Tuple[float, float, float], direction: Tuple[float, float, float]):
        """Activate this ability: handle cast/formation, projectile launch, or immediate area effect."""
        self.is_active = True
        # Account for any cast_time (formation_time)
        cast_delay = self.definition.cast_time or self.definition.properties.get('formation_time', 0.0)
        self.start_time = current_time + cast_delay
        # End of ability effect
        self.end_time = self.start_time + self.definition.duration
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

    def apply_effect(self, game_map: Any, players: List[Any]):
        """Deploy the ability's effect (damage, status, vision_block, etc.) at current position."""
        if not self.current_position3d:
            return
        x, y, z = self.current_position3d
        # Area effect
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
                    p.status_effects.append(status)
        # Optionally, integrate vision blockers or recon pings here
        # (smoke clouds or recon pulses could be added to game_map or a global list)
        return

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(def={self.definition.name}, active={self.is_active}, "
                f"pos={self.current_position3d or self.origin}, charges={self.charges_remaining})")

# Helper functions to create common ability definitions
def create_smoke_ability(name: str, radius: float = 5.0, duration: float = 15.0) -> AbilityDefinition:
    ad = AbilityDefinition(
        name=name,
        description="Creates a smoke cloud that blocks vision",
        ability_type=AbilityType.SMOKE,
        targeting_type=AbilityTarget.PROJECTILE,
        duration=duration,
        effect_radius=radius,
        cooldown=45.0,
        max_charges=2,
        blocks_vision=True,
        properties={
            "formation_time": 1.0,
            "projectile_speed": 15.0,
            "affected_by_gravity": True,
            "gravity_strength": 9.8
        }
    )
    ad.instance_class = SmokeAbilityInstance
    return ad

def create_flash_ability(name: str, duration: float = 1.0) -> AbilityDefinition:
    ad = AbilityDefinition(
        name=name,
        description="Blinds nearby players instantly",
        ability_type=AbilityType.FLASH,
        targeting_type=AbilityTarget.SELF,
        duration=0.5,  # Flash explosion duration
        effect_radius=8.0,
        cooldown=45.0,
        max_charges=2,
        status_effects={"flashed"},
        properties={
            "flash_duration": duration,
            "projectile_speed": 0.0,
            "affected_by_gravity": False,
            "gravity_strength": 0.0,
            "can_bounce": False,
            "bounce_efficiency": 0.0
        }
    )
    ad.instance_class = FlashAbilityInstance
    return ad

def create_molly_ability(name: str, radius: float = 5.0, duration: float = 7.0, damage: float = 8.0) -> AbilityDefinition:
    ad = AbilityDefinition(
        name=name,
        description="Creates a fire area that damages players",
        ability_type=AbilityType.MOLLY,
        targeting_type=AbilityTarget.PROJECTILE,
        duration=duration,
        effect_radius=radius,
        cooldown=45.0,
        max_charges=1,
        damage=damage,
        status_effects={"burning"},
        properties={
            "projectile_speed": 12.0,
            "affected_by_gravity": True,
            "gravity_strength": 9.8,
            "can_bounce": True,
            "bounce_efficiency": 0.6,
            "max_bounces": 2
        }
    )
    ad.instance_class = MollyAbilityInstance
    return ad

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
    def tick(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        # Move projectile if not yet applied
        if self.effect_applied:
            return
        # Apply gravity
        if self.definition.properties.get('affected_by_gravity', False) and self.velocity3d:
            g = self.definition.properties.get('gravity_strength', 9.8)
            vx, vy, vz = self.velocity3d
            self.velocity3d = (vx, vy, vz - g * time_step)
        # Travel
        if self.velocity3d and self.current_position3d:
            x, y, z = self.current_position3d
            vx, vy, vz = self.velocity3d
            new_x, new_y, new_z = x + vx * time_step, y + vy * time_step, z + vz * time_step
            self.current_position3d = (new_x, new_y, new_z)
            self.trajectory.append(self.current_position3d)
            # Check collision or range
            hit_point, hit_obj, hit_player = game_map.cast_bullet((x,y,z), self.direction3d, self.range_traveled, players)
            if hit_obj or hit_player:
                self.current_position3d = hit_point
                self.apply_effect(game_map, players)
                self.effect_applied = True
                return
            # Otherwise, continue

@dataclass
class AreaAbilityInstance(AbilityInstance):
    """Handles abilities that apply effects instantly or in an area (e.g. smoke clouds, AOE heals)."""
    def tick(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        # Apply area effect once at start
        if not self.effect_applied:
            self.apply_effect(game_map, players)
            self.effect_applied = True

@dataclass
class FlashAbilityInstance(ProjectileAbilityInstance):
    """Called when a flash projectile lands to blind players in a radius."""
    def apply_effect(self, game_map: Any, players: List[Any]):
        # Pop flash: blind all players around current position
        # Use origin if no projectile position
        loc = self.current_position3d or self.origin
        if not loc:
            return
        x, y, z = loc
        for p in players:
            px, py, pz = p.location
            distance = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
            if distance <= self.definition.effect_radius:
                # Apply flashed status
                if 'flashed' not in p.status_effects:
                    p.status_effects.append('flashed')
        # Flash is instant: end immediately
        self.is_active = False
        self.effect_applied = True

    def update(self, time_step: float, current_time: float, game_map: Any, players: List[Any]):
        # Immediate pop flash, no projectile travel
        if not self.is_active or self.effect_applied:
            return
        # Apply effect at player's location instantly
        self.apply_effect(game_map, players)
        # Expire at end_time
        if current_time >= self.end_time:
            self.is_active = False
        return

@dataclass
class SmokeAbilityInstance(AreaAbilityInstance):
    """Deploys a smoke cloud that blocks vision in its radius and persists for duration."""
    def apply_effect(self, game_map: Any, players: List[Any]):
        # No per-player effect; visibility handled via map.line_of_sight checks
        # Just mark smoke present until end_time
        self.effect_applied = True

@dataclass
class MollyAbilityInstance(ProjectileAbilityInstance):
    """Molotov that creates a damaging fire area on impact."""
    def apply_effect(self, game_map: Any, players: List[Any]):
        if not self.current_position3d:
            return
        x, y, z = self.current_position3d
        # Damage all in radius
        for p in players:
            px, py, pz = p.location
            dist = math.sqrt((px - x)**2 + (py - y)**2 + (pz - z)**2)
            if dist <= self.definition.effect_radius:
                p.apply_damage(int(self.definition.damage))
        # The area persists and continues to damage over time (could be ticked separately)
        self.effect_applied = True

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
                for p in players:
                    if p.id not in self.affected_players:
                        px, py, pz = p.location
                        dx = px - self.current_position3d[0]
                        dy = py - self.current_position3d[1]
                        if math.sqrt(dx*dx + dy*dy) <= self.definition.effect_radius:
                            # Mark revealed
                            p.status_effects.append('revealed')
                            self.affected_players.add(p.id)
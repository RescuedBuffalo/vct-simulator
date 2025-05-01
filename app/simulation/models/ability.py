from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Type
from enum import Enum
import math
import uuid
import time
import random
from app.simulation.models.map import Map
from app.simulation.models.player import Player

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
    """Base class for ability instances."""
    definition: AbilityDefinition
    owner_id: str
    instance_id: str
    charges_remaining: int
    is_active: bool = False
    cooldown_remaining: float = 0.0
    current_position3d: Optional[Tuple[float, float, float]] = None
    affected_players: Set[str] = field(default_factory=set)
    effect_applied: bool = False
    start_time: float = 0.0
    end_time: Optional[float] = None
    
    def activate(self, current_time: float, origin: Tuple[float, float, float], direction: Tuple[float, float, float]) -> None:
        """Activate the ability."""
        self.is_active = True
        self.start_time = current_time
        self.current_position3d = origin
        if self.definition.duration > 0:
            self.end_time = current_time + self.definition.duration
        self.charges_remaining -= 1
        
    def update(self, time_step: float, current_time: float, game_map: Optional[Any], players: List[Any]) -> None:
        """Update ability state."""
        if self.end_time and current_time >= self.end_time:
            self.is_active = False
        
    def get_remaining_duration(self, current_time: float) -> float:
        """Get remaining duration of active ability."""
        if not self.is_active or not self.end_time:
            return 0.0
        return max(0.0, self.end_time - current_time)
        
    def apply_effect(self, game_state: Optional[Any], players: List[Any]) -> None:
        """Apply ability effect to players."""
        if not self.current_position3d or not self.is_active:
            return
            
        x, y, z = self.current_position3d
        self.effect_applied = False
        
        for player in players:
            if not player.is_alive:
                continue
                
            # Get player position
            px, py, pz = player.location
            
            # Calculate distance to player
            dx = x - px
            dy = y - py
            dz = z - pz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            # Check if player is in range
            if dist <= self.definition.effect_radius:  # Use effect_radius
                self.affected_players.add(player.id)
                
                # Apply damage
                if self.definition.damage > 0:
                    if hasattr(player, 'apply_damage'):
                        player.apply_damage(int(self.definition.damage))
                    else:
                        if player.armor > 0:
                            armor_damage = min(player.armor, self.definition.damage * 0.5)
                            player.armor -= armor_damage
                            player.health -= self.definition.damage - armor_damage
                        else:
                            player.health -= self.definition.damage
                            
                # Apply healing
                if self.definition.healing > 0:
                    player.health = min(player.health + int(self.definition.healing), 100)
                    
                # Apply status effects
                for status in self.definition.status_effects:
                    if status not in list(player.status_effects.keys()):
                        player.status_effects[status] = self.definition.duration
                        
                self.effect_applied = True

@dataclass
class ProjectileAbilityInstance(AbilityInstance):
    """Base class for projectile abilities."""
    origin: Optional[Tuple[float, float, float]] = None
    direction3d: Optional[Tuple[float, float, float]] = None
    velocity3d: Optional[Tuple[float, float, float]] = None
    range_traveled: float = 0.0
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)
    velocity: Optional[Tuple[float, float, float]] = None
    bounces_remaining: int = 1
    
    def activate(self, current_time: float, origin: Tuple[float, float, float], direction: Tuple[float, float, float]) -> None:
        """Activate the projectile ability."""
        super().activate(current_time, origin, direction)
        self.origin = origin
        self.direction3d = direction
        self.velocity3d = (direction[0] * 20.0, direction[1] * 20.0, direction[2] * 20.0)  # Default velocity
        self.trajectory = [origin]
        
    def update(self, time_step: float, current_time: float, game_map: Optional[Any], players: List[Any]) -> None:
        """Update projectile state."""
        super().update(time_step, current_time, game_map, players)
        
        if not self.is_active or not self.velocity3d or not self.current_position3d:
            return
            
        # Update position
        x, y, z = self.current_position3d
        vx, vy, vz = self.velocity3d
        new_x = x + vx * time_step
        new_y = y + vy * time_step
        new_z = z + vz * time_step
        
        # Check collision with map
        if game_map:
            t, hit_point, hit_obj = game_map.raycast(origin=(x, y, z), direction=(vx, vy, vz), max_range=self.definition.max_range)
            if hit_point:
                if self.bounces_remaining > 0:
                    self.bounces_remaining -= 1
                    self.velocity3d = (-vx, -vy, vz)  # Simple bounce
                else:
                    self.current_position3d = hit_point
                    self.apply_effect(game_map, players)
                    self.is_active = False
                    return
                    
        # Update position and trajectory
        self.current_position3d = (new_x, new_y, new_z)
        self.trajectory.append(self.current_position3d)
        
        # Check max range
        self.range_traveled += math.sqrt((new_x - x)**2 + (new_y - y)**2 + (new_z - z)**2)
        if self.range_traveled >= self.definition.max_range:
            self.apply_effect(game_map, players)
            self.is_active = False

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
                        if status not in list(player.status_effects.keys()):
                            player.status_effects[status] = self.definition.duration

@dataclass
class FlashAbilityInstance(ProjectileAbilityInstance):
    """Instance of a flash ability."""
    
    def apply_effect(self, game_map: Optional[Map], players: List[Player]) -> None:
        """Apply flash effect to players based on their view direction relative to the flash."""
        if not self.current_position3d or not self.is_active or not game_map:
            return
        # Use self as the source for FOV calculation
        self.location = self.current_position3d  # Ensure self has a location attribute
        self.direction = 0  # Flash has no facing, so use 0 (360 FOV)
        visible_players = game_map.calculate_player_fov(self, players, fov_angle=360.0, max_distance=self.definition.effect_radius)
        for player in visible_players:
            if not player.is_alive:
                continue
            x, y, z = self.current_position3d
            px, py, pz = player.location
            dx = x - px
            dy = y - py
            dz = z - pz
            length = math.sqrt(dx*dx + dy*dy + dz*dz)
            if length == 0:
                continue
            dx, dy, dz = dx/length, dy/length, dz/length
            vx, vy, vz = player.view_direction
            dot = dx*vx + dy*vy + dz*vz
            if dot > 0.7:
                self.affected_players.add(player.id)
                player.status_effects["flashed"] = self.definition.duration

    def update(self, time_step: float, current_time: float, game_map: Optional[Any], players: List[Any]) -> None:
        """Update flash state."""
        super().update(time_step, current_time, game_map, players)
        
        # Apply flash effect if active
        if self.is_active:
            self.apply_effect(game_map, players)
        
        # If flash is no longer active, remove effects from affected players
        if not self.is_active:
            for player_id in self.affected_players:
                player = self.get_player_by_id(player_id)
                if player and "flashed" in list(player.status_effects.keys()):
                    del player.status_effects["flashed"]

@dataclass
class SmokeAbilityInstance(ProjectileAbilityInstance):
    """Instance of a smoke ability."""
    
    def activate(self, current_time: float, origin: Tuple[float, float, float], direction: Tuple[float, float, float]) -> None:
        """Activate the smoke ability."""
        super().activate(current_time, origin, direction)
        self.current_position3d = origin  # Smoke stays at origin
        self.is_active = True  # Ensure smoke is active
        
    def apply_effect(self, game_state: Optional[Any], players: List[Any]) -> None:
        """Apply smoke effect to players in range."""
        if not self.current_position3d or not self.is_active:
            return
            
        x, y, z = self.current_position3d
        self.effect_applied = False
        self.affected_players.clear()  # Clear affected players before applying effect
        
        for player in players:
            if not player.is_alive:
                continue
                
            # Get player position
            px, py, pz = player.location
            
            # Calculate distance to player
            dx = x - px
            dy = y - py
            dz = z - pz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            # Check if player is in range
            if dist <= self.definition.effect_radius:  # Use effect_radius
                self.affected_players.add(player.id)
                if "smoked" not in list(player.status_effects.keys()):
                    player.status_effects["smoked"] = self.definition.duration
                self.effect_applied = True
                
    def update(self, time_step: float, current_time: float, game_map: Optional[Any], players: List[Any]) -> None:
        """Update smoke state."""
        super().update(time_step, current_time, game_map, players)
        
        # Apply smoke effect if active
        if self.is_active:
            self.apply_effect(game_map, players)
            
        # If smoke is no longer active, remove effects from affected players
        if not self.is_active:
            for player_id in self.affected_players:
                player = self.get_player_by_id(player_id)
                if player and "smoked" in list(player.status_effects.keys()):
                    del player.status_effects["smoked"]

@dataclass
class MollyAbilityInstance(ProjectileAbilityInstance):
    """Instance of a molly ability."""
    
    def activate(self, current_time: float, origin: Tuple[float, float, float], direction: Tuple[float, float, float]) -> None:
        """Activate the molly ability."""
        super().activate(current_time, origin, direction)
        self.current_position3d = origin  # Molly stays at origin
        self.is_active = True  # Ensure molly is active
        
    def apply_effect(self, game_state: Optional[Any], players: List[Any]) -> None:
        """Apply molly effect to players in range."""
        if not self.current_position3d or not self.is_active:
            return
            
        x, y, z = self.current_position3d
        self.effect_applied = False
        self.affected_players.clear()  # Clear affected players before applying effect
        
        for player in players:
            if not player.is_alive:
                continue
                
            # Get player position
            px, py, pz = player.location
            
            # Calculate distance to player
            dx = x - px
            dy = y - py
            dz = z - pz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            # Check if player is in range
            if dist <= self.definition.effect_radius:  # Use effect_radius
                self.affected_players.add(player.id)
                if "burning" not in list(player.status_effects.keys()):
                    player.status_effects["burning"] = self.definition.duration
                
                # Apply damage
                damage = self.definition.damage  # Second param is damage
                if hasattr(player, 'apply_damage'):
                    player.apply_damage(int(damage))
                else:
                    if player.armor > 0:
                        armor_damage = min(player.armor, damage * 0.5)  # Armor takes 50% of damage
                        player.armor = max(0, player.armor - armor_damage)  # Ensure armor doesn't go negative
                        player.health = max(0, player.health - (damage - armor_damage))  # Remaining damage to health
                    else:
                        player.health = max(0, player.health - damage)  # Full damage to health
                    
                self.effect_applied = True
                
    def update(self, time_step: float, current_time: float, game_map: Optional[Any], players: List[Player]) -> None:
        """Update molly state."""
        super().update(time_step, current_time, game_map, players)
        
        # Apply damage over time if active
        if self.is_active:
            self.apply_effect(game_map, players)
        
        # If molly is no longer active, remove effects from affected players
        if not self.is_active:
            for player in players:
                if player.id in self.affected_players:
                    if "burning" in list(player.status_effects.keys()):
                        del player.status_effects["burning"]

@dataclass
class ReconAbilityInstance(ProjectileAbilityInstance):
    """Instance of a recon ability."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pulse_timer = 0.0
    
    def apply_effect(self, game_state: Optional[Any], players: List[Any]) -> None:
        """Apply recon effect to players in range."""
        if not self.current_position3d or not self.is_active:
            return
            
        x, y, z = self.current_position3d
        self.effect_applied = False
        
        for player in players:
            if not player.is_alive:
                continue
                
            # Get player position
            px, py, pz = player.location
            
            # Calculate distance to player
            dx = x - px
            dy = y - py
            dz = z - pz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            # Check if player is in range
            if dist <= self.definition.effect_radius:  # Use effect_radius
                self.affected_players.add(player.id)
                if "revealed" not in list(player.status_effects.keys()):
                    player.status_effects["revealed"] = self.definition.duration
                self.effect_applied = True
                
    def update(self, time_step: float, current_time: float, game_map: Optional[Any], players: List[Any]) -> None:
        """Update recon state."""
        super().update(time_step, current_time, game_map, players)
        
        if self.is_active and current_time < self.end_time:
            # Pulse interval
            interval = self.definition.properties.get('pulse_interval', 1.0)
            self.pulse_timer += time_step
            if self.pulse_timer >= interval:
                self.pulse_timer -= interval
                self.apply_effect(game_map, players)
        
        # If recon is no longer active, remove effects from affected players
        if not self.is_active:
            for player_id in self.affected_players:
                player = self.get_player_by_id(player_id)
                if player and "revealed" in list(player.status_effects.keys()):
                    del player.status_effects["revealed"]

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
        instance_class=FlashAbilityInstance,
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
        instance_class=SmokeAbilityInstance,
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
        instance_class=MollyAbilityInstance,
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
        instance_class=ReconAbilityInstance,
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
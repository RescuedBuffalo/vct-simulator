from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

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
    
    # Special Properties (for unique ability behaviors)
    properties: Dict[str, any] = field(default_factory=dict)

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
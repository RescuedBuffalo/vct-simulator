# Combat System Documentation

The VCT simulator implements a sophisticated combat system that models realistic tactical FPS gameplay mechanics.

## Weapon System (`weapon.py`)

### Weapon Categories
- **Sidearms**
  - Classic (Free)
  - Shorty (200 credits)
  - Frenzy (450 credits)
  - Ghost (500 credits)
  - Sheriff (800 credits)

- **SMGs**
  - Stinger (950 credits)
  - Spectre (1600 credits)

- **Rifles**
  - Bulldog (2050 credits)
  - Guardian (2250 credits)
  - Phantom (2900 credits)
  - Vandal (2900 credits)

- **Sniper Rifles**
  - Marshal (950 credits)
  - Operator (4700 credits)

- **Heavy Weapons**
  - Ares (1600 credits)
  - Odin (3200 credits)

### Weapon Properties
```python
@dataclass
class WeaponProperties:
    damage: int           # Base damage
    falloff: float       # Damage reduction over distance
    fire_rate: float     # Rounds per second
    magazine: int        # Bullets per magazine
    reload_time: float   # Time to reload in seconds
    accuracy: float      # Base accuracy rating
    penetration: float   # Wall penetration power
    movement_penalty: float  # Movement speed reduction
```

## Combat Mechanics

### Damage Calculation
```python
def calculate_damage(weapon, distance, armor, penetration=0):
    base_damage = weapon.damage
    falloff = max(0, 1 - (distance * weapon.falloff))
    pen_reduction = penetration * weapon.penetration
    armor_reduction = 0.5 if armor else 0
    
    return base_damage * falloff * (1 - pen_reduction) * (1 - armor_reduction)
```

### Accuracy System
- Base weapon accuracy
- Movement inaccuracy
- Recoil patterns
- First shot accuracy
- Recovery time
- Spray patterns

### Hit Registration
- Hitbox detection
- Penetration calculation
- Damage falloff
- Armor reduction
- Headshot multiplier

## Combat Interactions

### Engagement Types
1. **Direct Combat**
   - Line of sight checks
   - Distance calculations
   - Weapon effectiveness
   - Movement state impact

2. **Wall Penetration**
   - Material penetration values
   - Damage reduction
   - Penetration limits
   - Sound propagation

3. **Ability Interactions**
   - Flash effectiveness
   - Smoke coverage
   - Molly damage
   - Ability combos

### Combat Resolution
```python
def resolve_combat(attacker, defender, weapon, game_state):
    # Check line of sight
    if not has_line_of_sight(attacker, defender, game_state):
        return None
        
    # Calculate hit probability
    hit_chance = calculate_hit_probability(
        attacker.aim_rating,
        weapon.accuracy,
        attacker.movement_accuracy,
        distance_between(attacker, defender)
    )
    
    # Resolve damage if hit
    if random.random() < hit_chance:
        damage = calculate_damage(
            weapon,
            distance_between(attacker, defender),
            defender.armor
        )
        apply_damage(defender, damage)
```

## Economy System

### Buy Phase
- Credit management
- Buy strategies
- Force buy detection
- Save round logic
- Drop requests

### Equipment Value
```python
def calculate_equipment_value(player):
    value = 0
    value += WEAPON_COSTS.get(player.weapon, 0)
    value += SHIELD_COSTS.get(player.shield, 0)
    value += sum(ABILITY_COSTS.get(ability, 0) for ability in player.abilities)
    return value
```

## Status Effects

### Effect Types
- Flashed
- Suppressed
- Vulnerable
- Concussed
- Burning
- Slowed

### Effect Application
```python
def apply_status_effect(player, effect, duration):
    player.status_effects.append({
        'type': effect,
        'duration': duration,
        'start_time': current_time
    })
```

## Combat Events

### Event Types
- Kill
- Damage
- Flash Assist
- Trade Kill
- Wall Bang
- Ability Kill

### Event Logging
```python
def log_combat_event(event_type, attacker, defender, weapon, damage):
    return {
        'type': event_type,
        'attacker_id': attacker.id,
        'defender_id': defender.id,
        'weapon': weapon.name,
        'damage': damage,
        'timestamp': current_time
    }
```

## Best Practices

1. **Combat Resolution**
   - Always check line of sight
   - Consider all status effects
   - Apply proper damage calculations
   - Handle edge cases

2. **Economy Management**
   - Track team economy
   - Consider save thresholds
   - Handle force buy scenarios
   - Manage drops properly

3. **Event Handling**
   - Log all combat events
   - Update statistics properly
   - Handle simultaneous events
   - Maintain event order

## Future Enhancements

Planned improvements to the combat system:
- Advanced recoil patterns
- Detailed penetration system
- Enhanced status effects
- Team buy strategies
- Advanced combat AI
- Realistic movement accuracy 
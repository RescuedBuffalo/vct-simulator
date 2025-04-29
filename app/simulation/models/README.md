# Simulation Models

This directory contains the core simulation models for the VCT (Valorant Champions Tour) simulator. Each model represents a key component of the tactical FPS simulation system.

## Core Models Overview

### Player (`player.py`)
The `Player` class represents an individual player in the simulation with:
- Identity: ID, name, team, role, and agent type
- Combat stats: aim rating, reaction time, movement accuracy, spray control
- Physics: location, direction, velocity, acceleration
- Status: health, armor, alive status, planting/defusing state
- Movement states: walking, crouching, jumping, falling

### Team (`team.py`)
The `Team` class manages a group of players:
- Team identity and roster management
- Team-wide statistics tracking
- Ability and ultimate charge management
- Economy and buy strategy coordination

### Match (`match.py`)
The `Match` class orchestrates full game simulations:
- Round management and scoring
- Team side switching
- Overtime handling
- Match statistics collection
- Timeout and pause management

### Round (`round.py`)
The `Round` class handles individual round simulation:
- Buy phase management
- Combat interactions
- Movement and positioning
- Ability usage
- Spike plant/defuse mechanics
- Round state transitions

## Combat and Equipment Models

### Weapon (`weapon.py`)
Defines all weapon characteristics:
- Damage models and falloff
- Fire rates and accuracy
- Movement penalties
- Economy costs
- Ammunition and reload mechanics

### Ability (`ability.py`)
Models agent abilities and their effects:
- Ability types (flash, smoke, molly, etc.)
- Duration and cooldowns
- Area of effect calculations
- Status effect application
- Interaction with game state

## Statistics and Analytics

### PlayerStats (`player_stats.py`)
Tracks individual player performance:
- Kill/Death/Assist counts
- Damage dealt/received
- Economy management
- Ability usage effectiveness
- Round impact scores

### TeamStats (`team_stats.py`)
Aggregates team-level statistics:
- Round win rates
- Site control percentages
- Economy management
- Utility usage patterns
- Overall performance metrics

### MatchStats (`match_stats.py`)
Comprehensive match statistics:
- Round-by-round analysis
- Player performance comparisons
- Economy tracking
- Map control patterns
- Critical moment identification

## Environment and State Management

### Map (`map.py`)
Handles the game environment:
- Map geometry and collision
- Line of sight calculations
- Sound propagation
- Tactical positions
- Navigation mesh

### Blackboard (`blackboard.py`)
Manages shared knowledge and state:
- Team information sharing
- Strategy coordination
- Enemy position tracking
- Economy status
- Round state awareness

## Field of Vision (FOV) System

The FOV system simulates what players can see during gameplay:

### Core Features
- 110° vision cone by default
- Wall and obstacle occlusion
- Smoke and flash effects
- Distance-based visibility

### Usage Example
```python
def update(self, time_step):
    # Update player positions
    self.map.update_player_visibility(self.players)
    
    # Access visible enemies
    for player in self.players:
        visible_enemies = player.visible_enemies
```

## Data Flow and Interaction

The models interact in the following hierarchy:
1. `Match` contains multiple `Round` instances
2. `Round` manages `Player` and `Team` interactions
3. `Player` uses `Weapon` and `Ability` instances
4. `Map` provides the environment for all interactions
5. `Blackboard` facilitates information sharing
6. Stats classes (`PlayerStats`, `TeamStats`, `MatchStats`) observe and record

## Extension Points

The system is designed for extensibility:
- New weapon types can be added to `weapon.py`
- Additional abilities can be defined in `ability.py`
- Custom stats tracking can be implemented in stats classes
- Map features can be extended in `map.py`
- AI behavior can be modified via `blackboard.py`

## Best Practices

When working with these models:
1. Always use the appropriate stats class for data collection
2. Update FOV calculations each simulation step
3. Maintain proper round state transitions
4. Handle ability interactions through the proper channels
5. Use the blackboard for team coordination
6. Respect the physics and movement constraints

## Future Enhancements

Planned improvements include:
- Enhanced ability interactions
- More sophisticated economy management
- Advanced team tactics modeling
- Improved performance analytics
- Additional map features
- Extended stats collection 
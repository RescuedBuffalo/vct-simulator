# Simulation Models

This directory contains the core simulation models for the Valorant-like tactical FPS simulator.

## Field of Vision (FOV) System

The FOV system simulates what players can see during gameplay, similar to Valorant's mechanics. It's implemented in the `Map` class and is used to:

1. Determine which enemies are visible to each player
2. Control ability effects like flashes
3. Provide realistic information to AI decision-making

### How FOV Works

The system considers:
- Each player's facing direction (110° cone of vision by default)
- Occlusion by walls and other obstacles (via raycasting)
- Effects that block vision (smokes)
- Distance limitations (max visibility range)

### Using the FOV System

To update player visibility in your simulation loop:

```python
# In your simulation update method:
def update(self, time_step):
    # Update player positions, handle inputs, etc.
    
    # Then update visibility for all players
    self.map.update_player_visibility(self.players)
    
    # Now each player.visible_enemies contains IDs of visible enemies
    # Use this for AI decision making, etc.
```

For special effects like flashes, check the `is_looking_at_player` property:

```python
# Example for flash effect
def apply_flash(self, flash_origin, players):
    for player in players:
        if player.is_looking_at_player:
            # Apply stronger flash effect if looking at flash source
            player.status_effects.append("flashed")
```

### Custom FOV Parameters

You can customize the FOV parameters:
- `fov_angle`: Width of the vision cone in degrees (default: 110°)
- `max_distance`: Maximum visibility distance (default: 50 units)

Example:
```python
# For a player with reduced vision (e.g., partially flashed)
visible = map.calculate_player_fov(player, all_players, fov_angle=60, max_distance=30)
``` 
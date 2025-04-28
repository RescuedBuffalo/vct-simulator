# Advanced Match Statistics System

This directory contains the implementation of the advanced statistics tracking system for the Valorant simulation. The system is designed to collect, process, and analyze detailed statistics from matches, similar to professional match analytics but with even more depth.

## Overview

The statistics system consists of several components:

1. **Player Statistics** (`player_stats.py`): Tracks detailed player-level metrics including kills, deaths, assists, damage, economy, and advanced metrics.
2. **Team Statistics** (`team_stats.py`): Tracks team-level metrics such as round wins/losses, site preferences, economy performance, and utility usage.
3. **Match Statistics** (`match_stats.py`): Manages both player and team statistics and provides a unified view of the entire match.
4. **Statistics Collection**: Integrated into the `Round` and `Match` classes to collect events during simulation.
5. **Statistics Viewing** (`view_match_stats.py`): Command-line tool to view and analyze match statistics.
6. **Statistics Saving** (`save_match_stats.py`): Utility to save match statistics to JSON files for later analysis.

## Key Metrics

### Player Level Metrics

- **Combat Metrics**: Kills, deaths, assists, headshots, damage dealt/received
- **Objective Metrics**: Plants, defuses, first bloods
- **Economic Metrics**: Credits spent/earned, weapon purchases
- **Multi-kills**: Tracking 2K, 3K, 4K, and 5K rounds
- **Entry Performance**: Entry attempts and success rate
- **Clutch Performance**: Clutch attempts and success rate
- **Utility Usage**: Utility damage, enemies flashed, blind duration caused
- **Advanced Stats**: Kill/Death/Assist ratio, Average Combat Score, damage per round

### Team Level Metrics

- **Round Performance**: Win rates by side (attack/defense)
- **Site Performance**: Site preferences, plant/defuse success rates
- **Economic Rounds**: Performance in eco, bonus, and full-buy rounds
- **Multi-round Stats**: Flawless rounds, thrifty rounds, consecutive rounds
- **Trade Efficiency**: Effectiveness of trade kills
- **Time Stats**: Average round duration on attack/defense, plant timing
- **Retake Performance**: Retake attempts and success rates

### Match Level Metrics

- **Timeline Events**: Complete timeline of kills, plants, defuses, damage
- **Round Analysis**: Detailed breakdown of each round
- **MVP Tracking**: Identification of top performers
- **Match Stats**: Total rounds, overtime rounds, match duration

## Using the Statistics System

### In Match Simulations

The statistics collection is integrated into the simulation. To enable full statistics tracking, use these steps:

```python
from app.simulation.models.match import Match
from app.simulation.models.map import Map
from app.simulation.models.team import Team
from app.simulation.models.player import Player
from app.simulation.models.round import Round

# Create match as usual
match = Match(map_obj, round_obj, team_a, team_b)

# Run the match
match.run()

# Get detailed match statistics
match_stats = match.get_detailed_match_stats()

# Save statistics to a file
from app.save_match_stats import save_match_stats
stats_file = save_match_stats(match_stats)
print(f"Match statistics saved to {stats_file}")
```

### Viewing Match Statistics

After a match, you can analyze the statistics using the view_match_stats.py script:

```bash
python app/view_match_stats.py path/to/match_stats.json
```

Options:
- `--summary`: Show only a brief match summary
- `--export FILE`: Export statistics to a different file format

## Customizing the Statistics System

The statistics system is designed to be extensible. To add new metrics:

1. Add the new metric to `PlayerMatchStats` or `EnhancedTeamStats` as appropriate
2. Update the corresponding `record_*` methods in `MatchStats` to collect the metric
3. Add event tracking in `Round` class where appropriate
4. Update the statistics processing in `Match._process_round_statistics()`

## Implementation Notes

- The system uses a event-based approach where events (kills, plants, etc.) are logged during simulation.
- Statistics are calculated both during the match and in a post-processing step after the match completes.
- The statistics model is inspired by professional Valorant analytics, but expanded with custom metrics.
- For efficiency, some advanced metrics are calculated lazily when requested rather than maintained in real-time.

## Future Enhancements

- **Heat Maps**: Player positioning and kill locations
- **Economy Analysis**: Detailed economy simulation and tracking
- **Machine Learning Integration**: Predictive models based on statistics
- **Web Visualization**: Interactive web-based statistics viewer
- **Real-Time Analysis**: Stream statistics during simulation for live analysis 
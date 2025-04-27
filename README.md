# VCT Simulator

A Python-based simulator for Valorant Champions Tour (VCT) tournaments, featuring:

- Team management with player stats and abilities
- Tournament simulation with groups and brackets
- Match simulation with round-by-round outcomes
- Interactive visualization using Pygame
- Map systems with proper elevation, pathfinding, and tactical movement

## Getting Started

### Prerequisites

- Python 3.7+
- Pygame

### Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/vct-simulator.git
cd vct-simulator
```

2. Install dependencies:
```
pip install pygame
```

### Running the Simulator

To run the VCT Tournament simulator:

```
python -m app.simulation.vct_simulator
```

This will:
1. Create a tournament with realistic VCT teams
2. Simulate a group stage
3. Advance top teams to playoffs
4. Visualize the tournament results in a Pygame window

## Features

### Tournament Simulation

- Group stage with round-robin format
- Playoff bracket for top teams
- Bo1, Bo3, and Bo5 match formats
- Team and player statistics tracking

### Visualization

- Tournament brackets
- Match results
- Team standings
- Player statistics

### Game Mechanics

The simulator includes detailed gameplay mechanics:

- **Movement**: Walking, running, crouching, jumping with realistic physics
- **Combat**: Aim ratings, damage calculation, armor system
- **Abilities**: Smokes, flashes, molotovs, and recon abilities with proper effects
- **Maps**: Multiple maps with proper elevation, ramps, stairs, and objects

## Project Structure

```
vct-simulator/
├── app/
│   ├── simulation/
│   │   ├── models/
│   │   │   ├── ability.py  # Ability mechanics
│   │   │   ├── map.py      # Map and environment
│   │   │   └── player.py   # Player mechanics
│   │   ├── test_abilities.py    # Test ability mechanics
│   │   ├── test_movement.py     # Test movement mechanics
│   │   ├── test_maze.py         # Test pathfinding
│   │   ├── vct_simulator.py     # Main simulator
│   │   └── vct_visualizer.py    # Tournament visualization
├── docs/
├── maps/
│   └── haven.py            # Haven map representation
└── README.md
```

## Future Enhancements

- More detailed agent abilities and ultimates
- Additional maps with accurate layouts
- Tactical AI for simulating actual gameplay
- Performance metrics and analytics
- Support for custom teams and players

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Valorant game mechanics by Riot Games
- Inspired by real VCT tournaments and competitive gameplay 
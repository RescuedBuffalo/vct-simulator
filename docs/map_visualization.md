# VCT Map Generator and Visualizer

This document explains the enhanced map generation system that creates realistic Valorant-style tactical maps and provides multiple visualization options.

## Features

### Realistic Map Design
- Supports both 2-site and 3-site map layouts
- Complex network of interconnected areas (sites, mid, connectors, etc.)
- Proper tactical elements (choke points, elevated positions, one-way drops)
- Cover objects within areas for tactical gameplay
- Default plant spots and ultimate orb positions

### Enhanced DataModel
- `MapArea` now supports:
  - Elevation levels (heaven/hell positions)
  - Cover objects (boxes, crates, etc.)
  - One-way connections (drops)
  - More specific area types (site, spawn, mid, choke, connector, heaven, etc.)

- `MapLayout` now includes:
  - Default plant spots for each site
  - Ultimate orb positions
  - Thematic decorations
  - Complete wall placement for realistic map geometry

### Visualization Options
1. **Matplotlib Visualization** - Simple static map rendering
   - Useful for quick previewing or saving map images
   - Shows basic layout, paths, and areas
   - No interactivity but works with minimal dependencies

2. **Arcade Visualization** - Interactive 2D map viewer
   - Interactive panning and zooming
   - Color-coded areas by type
   - Visual representation of all tactical elements
   - Detailed view of cover objects, paths, and connections
   - Proper arrow indicators for one-way paths

## Usage

### Map Generation
```python
from app.simulation.models.map import generate_random_map

# Generate a random map
map_layout = generate_random_map()

# Or with a specific seed for reproducibility
map_layout = generate_random_map(seed=42)

# Save map to JSON
map_layout.save_to_json("maps/my_map.json")

# Load map from JSON
loaded_map = MapLayout.load_from_json("maps/my_map.json")
```

### Map Visualization
```python
# Simple matplotlib visualization
map_layout.visualize()
# Save to file
map_layout.visualize(save_path="maps/my_map.png")

# Interactive Arcade visualization
map_layout.visualize_with_arcade()
```

### Testing
Run the test script with:
```bash
python -m app.simulation.test_map
```

Options:
- `--arcade`: Launch the Arcade visualizer
- `--save`: Save visualizations to PNG files

## Dependencies
- Required: matplotlib (for basic visualization)
- Optional: arcade (for interactive visualization)

Install with:
```bash
pip install matplotlib
pip install arcade
```

## Map Structure Features

### Area Types
- **Sites** (A/B/C): Bomb planting locations
- **Spawn Areas**: Starting positions for attackers and defenders
- **Mid Areas**: Central contested zones
- **Choke Points**: Narrow passages that funnel movement
- **Connectors**: Paths connecting different areas
- **Heaven/Hell**: Elevated/Lower positions
- **Cubbies**: Small hiding spots or corners

### Tactical Elements
- **Walls**: Define the physical structure of the map
- **Cover Objects**: Boxes, crates, and other objects for protection
- **Default Plant Spots**: Common positions for spike planting
- **Ultimate Orbs**: Special pickup locations
- **One-way Drops**: Paths that can only be traversed in one direction

## Map Generation Process
1. Select a theme and number of sites (2 or 3)
2. Create base map layout with spawn areas
3. Place sites and define main approach paths
4. Add mid areas and connectors
5. Create tactical elements (heaven positions, cubby spots)
6. Place walls to define proper map geometry
7. Add cover objects in strategic locations
8. Apply theme-specific naming and decorations

## Future Enhancements
- Import/export real Valorant map layouts
- Additional visualization options (3D, web-based)
- Support for dynamic elements (doors, teleporters)
- More detailed tactical analysis tools 
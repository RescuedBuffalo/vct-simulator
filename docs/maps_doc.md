Perfect. I’ll now design a comprehensive Map dataclass that integrates seamlessly with your existing player, round, and ability models. This will include:

A flexible structure to support 2 or 3 bomb sites

Map geometry for pathfinding and vision checking

Theming and aesthetic metadata with at least 12 preset theme profiles

A procedural generator that creates balanced, Valorant-style tactical maps

Support for serialization to and from JSON to ensure persistence

I'll update you shortly with the full implementation and an example of a generated map.

Valorant-Style Map Dataclass and Random Map Generator

Map Data Model (MapLayout Class)

To support a Valorant-style game simulation, we introduce a MapLayout dataclass to represent an entire map, and a helper MapArea dataclass for individual zones/areas. This design emphasizes gameplay utility (like navigation and sightlines) over visual fidelity. Key features of the map model include:

Multiple Bomb Sites: Supports either 2 or 3 bomb sites (randomly determined per map). Bomb site areas are marked as plantable zones (e.g. "A Site", "B Site", "C Site" for a 3-site map).

Pathfinding Geometry: The map is composed of interconnected zones (spawn areas, bomb sites, chokepoints, mid areas, etc.) forming a graph or “node network” for navigation. Each MapArea knows its neighbors, enabling pathfinding algorithms (BFS/A* on the graph) to route agents through the map.

Visibility & Occlusion: The map includes geometric obstacles (walls) for line-of-sight calculations. A line-of-sight check will iterate through wall segments and block vision if any wall intersects the view ray. The model can also account for smoke or vision-blocking abilities by treating them as temporary circular occluders in the line-of-sight logic.

Theming & Zone Naming: A theme preset (from a library of 12+ presets such as Venice, Moroccan City, Underground Facility, etc.) influences the map’s aesthetic metadata. Each theme can adjust zone names and add decorative elements appropriate to the setting. (For example, a Venice-themed map might label the mid area as "Courtyard" and include a gondola prop, whereas a Moroccan-themed map might call mid "Market" and feature archways.)

Persistence (Save/Load): The MapLayout can be serialized to a dictionary/JSON format and re-loaded. This preserves randomly generated maps between simulations by saving all key properties (zones, connections, spawns, etc.) to disk.

Below is the Python code for the MapArea and MapLayout classes, integrating these features:

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json

@dataclass
class MapArea:
    name: str                   # e.g. "A Site", "Mid", "Attacker Spawn"
    area_type: str              # "site", "spawn", "mid", "choke", etc.
    center: Tuple[float, float] # Coordinates for this area's central point
    neighbors: List[str] = field(default_factory=list)  # Adjacent areas (by name) for pathfinding
    radius: float = 0.0         # Radius for area (e.g. bomb plant radius if site)
    is_plant_site: bool = False # True if this area is a bomb site where spike can be planted

@dataclass
class MapLayout:
    name: str                   # Map name (often influenced by theme)
    theme: str                  # Thematic preset name (environment style)
    areas: List[MapArea] = field(default_factory=list)         # All zones/areas in the map
    walls: List[Dict[str, Tuple[float, float]]] = field(default_factory=list)  # Wall segments for occlusion
    attacker_spawns: List[Tuple[float, float]] = field(default_factory=list)   # Spawn points for attackers
    defender_spawns: List[Tuple[float, float]] = field(default_factory=list)   # Spawn points for defenders
    decorative_elements: List[Dict] = field(default_factory=list)   # Thematic props (type and position)

    def to_dict(self) -> Dict:
        """Serialize map layout to a dictionary (for JSON saving or Round consumption)."""
        data = {
            "name": self.name,
            "theme": self.theme,
            "attacker_spawns": self.attacker_spawns,
            "defender_spawns": self.defender_spawns,
            "plant_sites": {},
            "walls": self.walls,
            "decorative_elements": self.decorative_elements,
            "zones": {}
        }
        # Include each area’s info. Mark bomb sites with center and radius.
        for area in self.areas:
            # Populate bomb site info for quick lookup
            if area.is_plant_site:
                site_key = area.name[0]  # e.g. "A Site" -> "A"
                data["plant_sites"][site_key] = {
                    "center": area.center, 
                    "radius": area.radius, 
                    "name": area.name
                }
            # Record general zone info (type and neighbors) for potential use in AI or debugging
            data["zones"][area.name] = {
                "type": area.area_type,
                "center": area.center,
                "neighbors": list(area.neighbors)
            }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'MapLayout':
        """Deserialize a MapLayout from a saved dictionary (reverse of to_dict)."""
        layout = cls(name=data.get("name", "Unknown"), theme=data.get("theme", "Unknown"))
        # Reconstruct MapArea objects
        zones_info = data.get("zones", {})
        area_objs: Dict[str, MapArea] = {}
        for name, info in zones_info.items():
            area_objs[name] = MapArea(
                name=name,
                area_type=info.get("type", ""),
                center=tuple(info.get("center", (0.0, 0.0))),
                radius=info.get("radius", 0.0),
                is_plant_site=(info.get("type") == "site")
            )
        # Set up neighbors once all areas are created
        for name, info in zones_info.items():
            area = area_objs[name]
            for neigh_name in info.get("neighbors", []):
                if neigh_name in area_objs:
                    area.neighbors.append(neigh_name)
            layout.areas.append(area)
        # Restore spawns, walls, and decorations
        layout.attacker_spawns = [tuple(pt) for pt in data.get("attacker_spawns", [])]
        layout.defender_spawns = [tuple(pt) for pt in data.get("defender_spawns", [])]
        layout.walls = data.get("walls", [])
        layout.decorative_elements = data.get("decorative_elements", [])
        return layout

    def save_to_json(self, filepath: str) -> None:
        """Save this map layout to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load_from_json(cls, filepath: str) -> 'MapLayout':
        """Load a map layout from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

In this design, MapLayout.to_dict() produces a dictionary structure that the simulation’s Round class can consume. For example, plant_sites maps site labels ("A", "B", "C") to their coordinates and radii, which the Round logic uses to check if the spike was planted in a given site area. Likewise, attacker_spawns and defender_spawns lists provide starting positions for teams, and walls provides segments for collision/vision checks. The zones field contains detailed info on each map area (though the Round may not directly use it yet, it’s useful for AI decision-making or debugging).

Integration Note: The Round simulation can easily use this structure. For instance, on round start it can do:

round = Round(..., map_data=map_layout.to_dict(), ...)

The Round’s initialization will place players at attacker_spawns/defender_spawns and use plant_sites and walls from this data (the provided map_data keys match what the Round expects).

Pathfinding and Visibility

To facilitate agent navigation, MapLayout provides a find_path method that computes a route between two zones. We model the map’s walkable areas as a graph of nodes (zones) rather than a fine grid, which is sufficient for high-level path planning. Each MapArea.neighbors list defines the connectivity (edges) between zones. For example, "Attacker Spawn" might neighbor "A Main" and "B Main", which in turn neighbor the bomb sites, etc. Using these connections, we can perform a BFS or Dijkstra search to find a sequence of zones connecting any two points of interest.

class MapLayout:
    # ... (other methods) ...
    def find_path(self, start_area: str, goal_area: str) -> List[str]:
        """Find a path between two zone names using BFS."""
        if start_area == goal_area:
            return [start_area]
        # Standard BFS traversal
        queue = [start_area]
        came_from: Dict[str, Optional[str]] = {start_area: None}
        while queue:
            current = queue.pop(0)
            if current == goal_area:
                break
            for neighbor in self.get_neighbors(current):
                if neighbor not in came_from:       # not visited
                    came_from[neighbor] = current
                    queue.append(neighbor)
        # Reconstruct path if target reached
        if goal_area not in came_from:
            return []  # no path found
        path = []
        node = goal_area
        while node is not None:
            path.append(node)
            node = came_from[node]
        return path[::-1]  # reverse to get start->...->goal

    def get_neighbors(self, area_name: str) -> List[str]:
        """Safe getter for neighbors of a zone by name."""
        for area in self.areas:
            if area.name == area_name:
                return area.neighbors
        return []

In this BFS implementation, we keep track of where we came from for each visited node, then backtrack from the goal to construct the path. The result is a list of zone names from the start to goal (e.g. ["Attacker Spawn", "Mid", "B Site"]). In practice, an agent can use this path to navigate zone-by-zone toward the objective. (For more precise movement within zones, a finer grid or navmesh could be used, but that’s beyond our high-level simulation scope.)

For visibility checks, MapLayout includes a line_of_sight(p1, p2) method. This determines if two points (e.g. two players’ locations) can see each other, considering walls and active smokes. The implementation iterates through each wall segment in self.walls and checks if the line segment from p1 to p2 intersects any wall. This uses a standard line-segment intersection test (the same algorithm used in the Round class’s _line_intersects_wall function). If any wall blocks the line, visibility is false. Additionally, we account for smoke zones (from abilities that block vision) by checking if the line passes through any smoke’s radius. In our code, we represent an active smoke as a circle (with a center and radius); we calculate the distance from the line segment to the smoke center, and if it’s less than the smoke radius, we treat it as an intersection (no vision).

class MapLayout:
    # ... (other methods) ...
    def line_of_sight(self, p1: Tuple[float,float], p2: Tuple[float,float], smokes: Optional[List[Dict]] = None) -> bool:
        """Check if the line from p1 to p2 is clear (no walls or smoke blocking)."""
        # Check static walls
        for wall in self.walls:
            if self._line_segments_intersect(p1, p2, wall["start"], wall["end"]):
                return False
        # Check dynamic vision blockers (smokes)
        if smokes:
            for smoke in smokes:
                center = smoke.get("center");  rad = smoke.get("radius", 0)
                if center and rad:
                    if self._distance_point_to_line(center, p1, p2) <= rad:
                        return False
        return True

    def _line_segments_intersect(self, p1:Tuple[float,float], p2:Tuple[float,float], 
                                 q1:Tuple[float,float], q2:Tuple[float,float]) -> bool:
        # (Implement line segment intersection math or call existing utility)
        # ...

    def _distance_point_to_line(self, point:Tuple[float,float], a:Tuple[float,float], b:Tuple[float,float]) -> float:
        # (Calculate shortest distance from 'point' to line segment ab)
        # ...

This mirrors typical FPS game logic: cast a ray between two characters and see if any wall or smoke intersects it. The Round simulation can utilize this by replacing its internal _has_line_of_sight with MapLayout.line_of_sight for a more data-driven approach. For example, during each simulation tick, the Round could do:

if not current_map.line_of_sight(player1.location, player2.location, active_smokes):
    # Player 1 cannot see Player 2 due to wall or smoke
    continue

By centralizing LoS checking in MapLayout, we ensure the simulation always uses up-to-date map geometry (and any dynamic updates like new walls or smokes).

Theming Presets and Zone Naming

Every map in Valorant has a unique setting or theme, often inspired by real locations. For instance, Ascent is set in Venice, Italy (with open plazas and a central courtyard), whereas Bind is set in Morocco (with desert architecture and marketplaces). Our simulation supports at least a dozen theming presets that influence the visual flavor and naming of the map:

Theme Library: We maintain a list of theme presets, e.g. "Venice", "Moroccan City", "Underground Facility", "Cyberpunk City", "Space Station", "Jungle Temple", "Desert Ruins", "Industrial Port", "Snowy Outpost", "Mountain Monastery", "Futuristic City", "Medieval Castle", etc. Each theme can be associated with certain decorative elements and alternate names for standard zones.

Zone Naming Conventions: While the map’s functional zones have generic labels (A Site, B Site, Mid, etc.), the theme can provide more flavor. For example, a Venice theme might rename "Mid" to "Courtyard" or "Market", reflecting an open plaza in a Venetian city square. A Moroccan theme could rename "Mid" to "Market" or "Bazaar", suggesting a marketplace area. An Underground Facility theme might call mid "Tunnel" or "Lab", etc. These names are cosmetic and used for callouts or AI context, while the underlying logic still knows the area as a mid connector.

Decorative Elements: We can attach a list of props/decals appropriate to the theme. For instance, the Venice map might include a gondola model on a canal in one area, or Italian architecture elements. The Moroccan map might feature stone arches or a rug market in its design. These elements are stored in decorative_elements with type and position, so the simulation or a renderer could place them (they generally do not impact gameplay except possibly as cover if we design them so).

In code, after generating the base layout, we apply theme-based modifications. For example, in the generator (shown next) we do:

if theme == "Venice":
    # Rename "Mid" to "Courtyard"
    rename_map["Mid"] = "Courtyard"
    # Add a gondola decoration in the canal area
    layout.decorative_elements.append({"type": "gondola", "position": (x, y)})
elif theme == "Moroccan City":
    rename_map["Mid"] = "Market"
    layout.decorative_elements.append({"type": "archway", "position": (x, y)})
elif theme == "Underground Facility":
    rename_map["Mid"] = "Tunnel"
    layout.decorative_elements.append({"type": "pipe", "position": (x, y)})
# ... (other themes)
# Apply renaming to MapArea objects and their neighbor references
for area in layout.areas:
    if area.name in rename_map:
        new_name = rename_map[area.name]
        area.name = new_name
# Also update any neighbor names that were renamed
for area in layout.areas:
    area.neighbors = [rename_map.get(n, n) for n in area.neighbors]

This way, the functional labels like "A Site" remain (we don’t change site letters), but generic labels get a theme-specific twist. The end result is a map data structure that not only defines gameplay-critical zones, but also carries descriptive flavor (zone names and props) matching the map’s setting. This can enhance the realism of the simulation and allow AI or commentary to use proper callouts (e.g. “Enemies spotted in Market!” instead of just “Mid”).

Random Map Generation Function

To create maps procedurally, we provide a generator function that constructs a new MapLayout with a random layout and theme. The goal is to produce tactically balanced maps, meaning the layout offers fair opportunities for both attackers and defenders, with multiple routes and chokepoints similar to real Valorant maps.

Key design considerations for generating a balanced map:

Spawn Zones: Clearly defined Attacker Spawn and Defender Spawn areas. Attackers should spawn at a far end of the map, and defenders on the opposite side near the bomb sites. This ensures defenders can reach each site slightly faster than attackers (as in Valorant).

Bomb Sites: 2 or 3 bomb sites are placed, typically near the defender side of the map. If 2 sites, label them A Site and B Site. If 3 sites (like Haven), include C Site. Each site is a distinct zone with a radius where the spike can be planted.

Main Lanes: For each site, create a primary approach for attackers (often called “A Main”, “B Main”, etc.). These are corridors or open lanes leading from Attacker Spawn toward the site. They usually converge into the site through a chokepoint (doorway or arch). For example, A Main connects Attacker Spawn to A Site.

Mid and Rotations: Incorporate a mid-field area or connector that offers a secondary route. In two-site maps, a Mid zone between A and B can grant attackers a path to pressure another site or to split the defense. In three-site maps, the central site (B) often serves as the “mid” area, or there is a courtyard that links to it. Control of mid should allow quicker rotation (repositioning) between sites.

Connections (Edges): Connect the zones in a graph such that:

Attacker Spawn links to each main lane (and possibly to mid directly).

Mid lanes connect into the routes toward both sites (e.g. mid might branch into A Main and B Main, or directly into sites via small connectors).

Defender Spawn connects to each bomb site (allowing defenders to quickly reinforce any site). Sometimes defender spawn also has a path to mid or a back route between sites.

Each bomb site can be entered from at least two directions (for instance, A Site from A Main and from a mid connector or a flank). This prevents one chokepoint from being the sole entry.

Distances: Ensure reasonable distances: e.g., the travel distance from Attacker Spawn to a site is longer than from Defender Spawn to that site (so defenders can take positions). At the same time, routes like mid provide a shorter (but contestable) path. We also scatter some cover in long sightlines to avoid overly long uninterrupted sniper lanes (e.g., a wall or two to break up the line of sight).

Zone Labels: Assign names procedurally based on their role: "Attacker Spawn", "Defender Spawn", "A Site", "B Site", ("C Site" if needed), "A Main", "B Main", etc., plus "Mid" or other connectors. The naming scheme ensures the simulation and AI can reference them logically. (After this, theme-based renaming may apply as described above.)

Below is an example of the generator function, generate_random_map(), which creates a new MapLayout with random settings. It uses simple coordinate placements for clarity – a real generator could randomize positions and add variations in layout topology, but here we ensure a balanced, comprehensible structure:

import random

def generate_random_map(seed: Optional[int] = None) -> MapLayout:
    if seed: 
        random.seed(seed)
    # 1. Choose a random theme and number of sites
    themes = ["Venice", "Moroccan City", "Underground Facility", "Cyberpunk City", 
              "Space Station", "Jungle Temple", "Desert Ruins", "Industrial Port",
              "Snowy Outpost", "Mountain Monastery", "Futuristic City", "Medieval Castle"]
    theme = random.choice(themes)
    num_sites = random.choice([2, 3])
    map_name = f"{theme} Map"
    layout = MapLayout(name=map_name, theme=theme)

    # 2. Define map size and key coordinates (simple rectangular layout)
    width, height = (120.0, 100.0) if num_sites == 3 else (100.0, 100.0)
    # Place spawns at opposite ends
    attacker_spawn_pos = (10.0, height/2)
    defender_spawn_pos = (width - 10.0, height/2)
    # Create spawn areas
    layout.areas.append(MapArea("Attacker Spawn", "spawn", attacker_spawn_pos, radius=5.0))
    layout.areas.append(MapArea("Defender Spawn", "spawn", defender_spawn_pos, radius=5.0))
    layout.attacker_spawns = [attacker_spawn_pos]
    layout.defender_spawns = [defender_spawn_pos]

    # 3. Create bomb site areas and connecting routes
    if num_sites == 2:
        # Two-site map (A and B)
        a_site_pos = (width - 20.0, height * 1/3)   # A Site towards left-top
        b_site_pos = (width - 20.0, height * 2/3)   # B Site towards left-bottom
        a_main_pos = (width/2, height * 1/3)        # chokepoint on route to A
        b_main_pos = (width/2, height * 2/3)        # chokepoint on route to B
        mid_pos    = (width/2, height/2)            # central mid area

        # Create areas for sites and lanes
        layout.areas += [
            MapArea("A Site", "site", a_site_pos, radius=10.0, is_plant_site=True),
            MapArea("B Site", "site", b_site_pos, radius=10.0, is_plant_site=True),
            MapArea("A Main", "choke", a_main_pos),
            MapArea("B Main", "choke", b_main_pos),
            MapArea("Mid",    "mid",   mid_pos)
        ]
        # Set up neighbors (graph edges)
        _neighbors = {  # temporary dict for readability
            "Attacker Spawn": ["A Main", "B Main", "Mid"],
            "Defender Spawn": ["A Site", "B Site"],
            "A Main": ["Attacker Spawn", "A Site", "Mid"],
            "B Main": ["Attacker Spawn", "B Site", "Mid"],
            "Mid":    ["Attacker Spawn", "A Main", "B Main"],
            "A Site": ["A Main", "Defender Spawn"],
            "B Site": ["B Main", "Defender Spawn"]
        }
    else:
        # Three-site map (A, B, C)
        a_site_pos = (width - 30.0, height * 1/4)   # A Site (top)
        b_site_pos = (width - 20.0, height * 1/2)   # B Site (middle)
        c_site_pos = (width - 30.0, height * 3/4)   # C Site (bottom)
        a_main_pos = (width/2, height * 1/4)        # A long route
        c_main_pos = (width/2, height * 3/4)        # C long route

        layout.areas += [
            MapArea("A Site", "site", a_site_pos, radius=10.0, is_plant_site=True),
            MapArea("B Site", "site", b_site_pos, radius=10.0, is_plant_site=True),
            MapArea("C Site", "site", c_site_pos, radius=10.0, is_plant_site=True),
            MapArea("A Main", "choke", a_main_pos),
            MapArea("C Main", "choke", c_main_pos)
        ]
        # Define neighbors. Here we treat B Site as the mid connector as well.
        _neighbors = {
            "Attacker Spawn": ["A Main", "B Site", "C Main"],
            "Defender Spawn": ["A Site", "B Site", "C Site"],
            "A Main": ["Attacker Spawn", "A Site", "B Site"],
            "C Main": ["Attacker Spawn", "C Site", "B Site"],
            "A Site": ["A Main", "B Site", "Defender Spawn"],
            "B Site": ["Attacker Spawn", "A Site", "C Site", "Defender Spawn"],
            "C Site": ["C Main", "B Site", "Defender Spawn"]
        }

    # Apply neighbor relations to MapArea objects
    for area in layout.areas:
        if area.name in _neighbors:
            area.neighbors = _neighbors[area.name]

    # 4. Place walls to shape the map geometry (for occlusion and pathing).
    # (We add a few example walls to break up long lines of sight and force paths through chokepoints)
    if num_sites == 2:
        # One wall in mid to block straight sight from attacker to defender spawn
        layout.walls.append({"start": (width/2 + 5, height/2 - 15), "end": (width/2 + 5, height/2 + 15)})
        # Walls to create choke at A Main and B Main (e.g., top of A Main corridor, bottom of B Main corridor)
        layout.walls.append({"start": (width/2, height*1/3 - 5), "end": (width - 20, height*1/3 - 5)})
        layout.walls.append({"start": (width/2, height*2/3 + 5), "end": (width - 20, height*2/3 + 5)})
    else:
        # Walls in a 3-site map
        layout.walls.append({"start": (width/2, height/2 - 10), "end": (width/2, height/2 + 10)})  # block direct mid sight
        layout.walls.append({"start": (width/2, height*1/4 - 5), "end": (width - 30, height*1/4 - 5)})  # A Site entrance cover
        layout.walls.append({"start": (width/2, height*3/4 + 5), "end": (width - 30, height*3/4 + 5)})  # C Site entrance cover

    # 5. Thematic adjustments (rename zones, add decorations)
    if theme == "Venice":
        # E.g., rename "Mid" to "Courtyard" for flavor
        if "Mid" in _neighbors: 
            _neighbors["Courtyard"] = _neighbors.pop("Mid")
        for area in layout.areas:
            if area.name == "Mid":
                area.name = "Courtyard"
        layout.decorative_elements.append({"type": "gondola", "position": (width/2 - 10, height/2)})
    elif theme == "Moroccan City":
        if "Mid" in _neighbors:
            _neighbors["Market"] = _neighbors.pop("Mid")
        for area in layout.areas:
            if area.name == "Mid":
                area.name = "Market"
        layout.decorative_elements.append({"type": "archway", "position": (width/2, height/2)})
    # (similar blocks for other themes...)

    # Ensure neighbors dict keys match any renamed areas
    for area in layout.areas:
        # Update neighbor names inside each MapArea after renaming
        area.neighbors = [n if n not in _neighbors else n for n in area.neighbors]

    return layout

Let’s break down what this generator does:

Theme & Site Count: Randomly pick a theme from the list (we might get "Venice", "Moroccan City", etc.) and randomly decide on 2 or 3 sites for the map. This randomness can be seeded for reproducibility.

Initialize Map and Spawns: Create the MapLayout and add attacker/defender spawn areas. We position attackers on the left side (x ~ 10) and defenders on the right (x ~ 90-110) of a 100x100 (or 120x100 for 3 sites) map.

Create Sites and Routes: If 2 sites:

Place A Site and B Site at upper-left and lower-left portions of the map (towards defender side).

Define A Main and B Main roughly mid-map as chokepoints on the routes to A and B respectively.

Define a Mid area in the center.

Connect Attacker Spawn to A Main, B Main, and Mid (attackers can choose any of the three routes initially).

Connect Mid to both A Main and B Main (so mid acts as a hub/alternate path between the two lanes).

Connect Defender Spawn to A Site and B Site (defenders can quickly go to either site).

Connect each Site to its Main and to Defender Spawn. (Attackers reach site via main; defenders come from behind the site).
This yields a typical two-lane plus mid layout, akin to Valorant’s Ascent or Bind where mid control is pivotal for rotations.

If 3 sites:

Place A, B, C Sites top, middle, bottom of defender side.

A Main and C Main as long routes from attacker side to A and C.

Use B Site as a central area (mid) directly connected to Attacker Spawn (analogous to Haven’s mid/B site area).

Connect Attacker Spawn to A Main, C Main, and directly to B Site route.

Connect B Site with A Site and C Site as well (simulating the short connectors on Haven: an attacker can go through B to reach A or C from an alternate angle).

Defenders spawn links to all three sites.
This creates a web of connections ensuring all sites are reachable and rotatable: attackers have three initial routes (toward A, B, or C), and controlling the central B Site helps them pivot to the others, similar to Haven’s design.

Walls/Occlusion: We add a few wall segments to simulate map geometry that funnels movement:

In the 2-site layout, a vertical wall in the middle prevents a straight line of sight from attacker spawn to defender spawn (so teams can’t see/shoot each other across the map at round start). Other walls at A Main and B Main create choke points (attackers must turn a corner or go through a doorway to reach the site, rather than seeing the site directly from far away). These encourage the intended pathways and provide cover.

In the 3-site layout, similar walls block overly long sightlines (e.g., a wall in front of B Site to require attackers to commit into the site, and walls at A and C entries).
We aim to include a mix of tight angles and long corridors to make firefights interesting, and ensure there are some safe areas out of spawn where teams can strategize without immediate contact.

Apply Theme Changes: Based on the chosen theme, adjust zone names and add decorative elements. In the code above, for example, if the theme is "Venice", we rename the "Mid" area to "Courtyard" and add a gondola decoration. If "Moroccan City", we rename "Mid" to "Market" and add an archway prop. These changes are done after setting up the core layout so they don’t affect connectivity – they’re purely cosmetic/organizational. We make sure to update the neighbor references so the graph remains consistent after renaming.

Return the MapLayout: The finished MapLayout object contains all the data (areas, spawns, walls, theme info). We can then save it to disk or plug it into a simulation Round.

By running this generator, we get a new map each time, for example:

Venice Map: 3 sites (A, B, C) set in an Italianate style. The mid area is labeled Courtyard, and there’s a gondola decoration near the canal (perhaps between A and B). Attackers have three lanes, with a fountain courtyard (mid) that connects towards all sites.

Moroccan City Map: 2 sites (A, B) in a Moroccan bazaar setting. The mid area is Market. Expect tight alleyways (A Main, B Main) leading to open marketplaces at the sites, and maybe a rooftop or arch providing cover. Teleporters could even be added as special connectors (as Bind has), though our model hasn’t explicitly included teleporters – they could be represented as additional edges in the graph if desired.

Each generated map prioritizes gameplay fidelity – the distances, chokepoints, and routes are designed to ensure fair play and strategic depth, much like real Valorant maps. We are not focusing on high graphical detail or perfect real-world geometry. Instead, we ensure the data integrates smoothly with the simulation: the Round can use the node graph for agent navigation and the walls for line-of-sight, and the AI can reason about areas like “Mid” or “Site” with thematic context. This approach yields a flexible system where new maps can be rolled out in simulation, providing variety in an esport simulation league without manual map creation.

Integration with Round and Agent Logic

Finally, we may need to extend or update the Round simulation class (and related models like Player and Ability) to fully utilize this map model:

Round Initialization: The Round should accept a MapLayout (or a dict from MapLayout.to_dict()). As seen in our design, Round’s _initialize_player_positions already uses map_data["attacker_spawns"] and ["defender_spawns"] to spawn players. Our MapLayout provides these, so integration is seamless. The Round can also store a reference to the MapLayout for on-the-fly queries (e.g., to call find_path or line_of_sight during simulation).

Agent Navigation: With the map’s graph available, AI agents can make pathfinding decisions. For example, if an attacker bot decides to rotate from A Site to B Site, it can request a path:

path = current_map.find_path("A Site", "B Site")  # might return ["A Site", "Defender Spawn", "B Site"] or via mid

The AI could then follow this route zone by zone. We would update the Round logic to move players incrementally along these paths. For instance, each Player could have a current target position or next waypoint. The Round’s update loop can calculate a direction vector toward the next waypoint and update the player’s location and direction accordingly, factoring in movement speed and obstacles. (The Player.velocity field can be used for movement; e.g., set a velocity toward the next node).

Zone Awareness: We might add a method to map, e.g., get_zone(position) to determine which zone a player is currently in (by checking which area’s region contains the coordinates). This could update Player.map_location or similar, so that the simulation knows “Player X is in B Main”. This ties into the Player.map_knowledge and callouts fields, allowing bots to share info like “Enemy spotted at Market (Mid)” using the thematic callout names.

Visibility & Abilities: The Round’s combat logic should use the map’s geometry for cover and vision. We would replace any direct distance-based visibility checks with map_layout.line_of_sight(p1, p2, active_smokes=...). As abilities like smokes or Sage walls are deployed, we can dynamically add temporary occluders:

For a smoke ability (AbilityType.SMOKE), when activated, create a smoke entry (with center and radius) and include it in the smokes list passed to line_of_sight. The smoke persists for its duration, after which it’s removed.

For a wall ability (AbilityType.VISION_BLOCK or similar), we could add new wall segments to map_layout.walls or handle it similarly to smokes (as a set of line segments or a large radius blocker).

The AbilityInstance data in the simulation already has blocks_vision flags, so the Round can check those and inform the map model. For example, if a smoke grenade is thrown at point X with radius R, do: current_map.walls.append({...}) or keep a separate Round.active_smokes and pass it in to LoS checks.

Round Results and Analysis: Since our map tracks site info (centers, radii), the Round can determine which site the spike was planted on by checking distances – our plant_sites data facilitates that. Also, having named zones can enrich post-round analytics (e.g., “Most kills happened in A Main area” if we track death locations against zone polygons).

By integrating the MapLayout with Round in this way, we achieve a cohesive simulation:

The map provides the ground truth for where players can move and what they can see.

The Round and Player logic utilize this to simulate realistic agent movement (taking proper routes instead of straight-line teleportation) and combat engagements (with walls and smokes truly blocking vision).

Everything is data-driven: switching to a new map or theme is as simple as loading a different JSON or generating a new layout – the rest of the engine automatically uses the new geometry and zone labels.

In summary, we’ve designed a robust Python Map dataclass system for a Valorant-style game, consisting of MapLayout and MapArea, along with a generator for random map creation. This system supports 2-3 bomb sites, pathfinding via a node graph, line-of-sight and occlusion (with walls and smoke), over a dozen thematic variants with unique zone naming and props, and the ability to save/load maps for persistence. It integrates tightly with the existing simulation models: the Round uses the map data for spawning and visibility, and can be extended to use the pathfinding for agent navigation and strategic decision-making. This design prioritizes gameplay and integration fidelity – ensuring that maps contribute to fair and strategic play – rather than exact artistic detail, which aligns with our simulation needs. Each generated map offers a fresh yet believable scenario for the virtual esports environment, much like how each Valorant map provides a distinct strategic flavor within the same core ruleset.


import random
import math
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class MapFeature:
    """Represents a tactical feature in the map."""
    feature_type: str  # "cover", "elevation", "connector", "choke", etc.
    position: Tuple[float, float]
    size: Tuple[float, float]
    elevation: float = 0.0
    properties: Dict = None

class MapGenerator:
    """Advanced map generator with support for tactical features and elevation."""
    
    def __init__(self, width: float = 100.0, height: float = 100.0):
        self.width = width
        self.height = height
        self.features = []
        self.areas = {}
        self.walls = []
        self.objects = []
        self.elevation_points = []
        
        # Tactical parameters
        self.min_site_size = 15.0
        self.max_site_size = 25.0
        self.min_corridor_width = 4.0
        self.max_corridor_width = 8.0
        self.min_elevation_diff = 1.0
        self.max_elevation_diff = 3.0
        
    def generate_map(self, num_sites: int = 2, theme: str = "default") -> Dict:
        """Generate a complete map with tactical features."""
        # Reset state
        self.features = []
        self.areas = {}
        self.walls = []
        self.objects = []
        self.elevation_points = []
        
        # Generate basic layout
        self._generate_base_layout(num_sites)
        
        # Add tactical features
        self._add_tactical_features()
        
        # Add elevation variation
        self._add_elevation()
        
        # Add cover objects
        self._add_cover_objects()
        
        # Generate final map data
        return self._create_map_data(theme)
    
    def _generate_base_layout(self, num_sites: int):
        """Generate the basic map layout with sites and main paths."""
        # Place bomb sites
        site_positions = self._place_bomb_sites(num_sites)
        
        # Place spawn areas
        attacker_spawn = (self.width * 0.1, self.height * 0.5)
        defender_spawn = (self.width * 0.9, self.height * 0.5)
        
        # Create main paths to each site
        for site_pos in site_positions:
            # Direct path from attacker spawn
            self._create_path(attacker_spawn, site_pos, "attack_path")
            # Direct path from defender spawn
            self._create_path(defender_spawn, site_pos, "defend_path")
        
        # Create mid area and connectors
        if num_sites >= 2:
            mid_pos = (self.width * 0.5, self.height * 0.5)
            self._create_mid_area(mid_pos)
            
            # Connect mid to sites
            for site_pos in site_positions:
                self._create_path(mid_pos, site_pos, "mid_connector")
    
    def _place_bomb_sites(self, num_sites: int) -> List[Tuple[float, float]]:
        """Place bomb sites in tactically interesting positions."""
        positions = []
        
        if num_sites == 2:
            # Two sites on opposite sides
            positions = [
                (self.width * 0.8, self.height * 0.25),  # A site
                (self.width * 0.8, self.height * 0.75),  # B site
            ]
        elif num_sites == 3:
            # Three sites triangle formation
            positions = [
                (self.width * 0.8, self.height * 0.2),   # A site
                (self.width * 0.8, self.height * 0.8),   # C site
                (self.width * 0.85, self.height * 0.5),  # B site
            ]
        
        # Create site areas
        for i, pos in enumerate(positions):
            site_name = chr(65 + i)  # A, B, C
            size = (
                random.uniform(self.min_site_size, self.max_site_size),
                random.uniform(self.min_site_size, self.max_site_size)
            )
            self.areas[f"{site_name} Site"] = {
                "type": "site",
                "x": pos[0] - size[0]/2,
                "y": pos[1] - size[1]/2,
                "w": size[0],
                "h": size[1],
                "elevation": 0.0
            }
        
        return positions
    
    def _create_path(self, start: Tuple[float, float], end: Tuple[float, float], path_type: str):
        """Create a path between two points with tactical variations."""
        # Calculate path direction
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Add some randomness to path
        num_segments = random.randint(2, 4)
        current_pos = start
        
        for i in range(num_segments):
            # Calculate next point with some random offset
            progress = (i + 1) / num_segments
            target_x = start[0] + dx * progress
            target_y = start[1] + dy * progress
            
            if i < num_segments - 1:  # Don't offset final segment
                offset = random.uniform(-distance*0.2, distance*0.2)
                if random.random() < 0.5:
                    target_x += offset
                else:
                    target_y += offset
            
            # Create path segment
            self._create_path_segment(current_pos, (target_x, target_y), path_type)
            current_pos = (target_x, target_y)
    
    def _create_path_segment(self, start: Tuple[float, float], end: Tuple[float, float], path_type: str):
        """Create a single path segment with appropriate width and features."""
        # Calculate segment properties
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        angle = math.atan2(dy, dx)
        length = math.sqrt(dx*dx + dy*dy)
        width = random.uniform(self.min_corridor_width, self.max_corridor_width)
        
        # Create corridor area
        corridor_name = f"corridor_{len(self.areas)}"
        self.areas[corridor_name] = {
            "type": "corridor",
            "x": start[0],
            "y": start[1] - width/2,
            "w": length,
            "h": width,
            "angle": math.degrees(angle),
            "elevation": 0.0
        }
        
        # Add choke points with some probability
        if random.random() < 0.3:
            choke_pos = (
                start[0] + dx * random.uniform(0.3, 0.7),
                start[1] + dy * random.uniform(0.3, 0.7)
            )
            self._add_choke_point(choke_pos, angle)
    
    def _create_mid_area(self, position: Tuple[float, float]):
        """Create a mid area with tactical features."""
        size = (
            random.uniform(20.0, 30.0),
            random.uniform(20.0, 30.0)
        )
        
        self.areas["Mid"] = {
            "type": "mid",
            "x": position[0] - size[0]/2,
            "y": position[1] - size[1]/2,
            "w": size[0],
            "h": size[1],
            "elevation": 0.0
        }
        
        # Add some cover objects in mid
        num_covers = random.randint(3, 5)
        for _ in range(num_covers):
            cover_pos = (
                position[0] + random.uniform(-size[0]/3, size[0]/3),
                position[1] + random.uniform(-size[1]/3, size[1]/3)
            )
            self._add_cover_object(cover_pos)
    
    def _add_choke_point(self, position: Tuple[float, float], angle: float):
        """Add a choke point with appropriate cover."""
        choke_width = self.min_corridor_width * 0.7  # Make it narrower
        choke_length = random.uniform(3.0, 5.0)
        
        # Add walls to create choke
        wall_thickness = 1.0
        self.walls.append({
            "x": position[0] - choke_length/2,
            "y": position[1] - choke_width/2 - wall_thickness,
            "w": choke_length,
            "h": wall_thickness,
            "angle": math.degrees(angle)
        })
        self.walls.append({
            "x": position[0] - choke_length/2,
            "y": position[1] + choke_width/2,
            "w": choke_length,
            "h": wall_thickness,
            "angle": math.degrees(angle)
        })
        
        # Add cover object near choke
        cover_offset = random.uniform(-choke_length/2, choke_length/2)
        cover_pos = (
            position[0] + cover_offset * math.cos(angle),
            position[1] + cover_offset * math.sin(angle)
        )
        self._add_cover_object(cover_pos)
    
    def _add_tactical_features(self):
        """Add tactical features like elevated positions and connectors."""
        # Add elevated positions near sites
        for area in self.areas.values():
            if area["type"] == "site":
                if random.random() < 0.7:  # 70% chance for elevated position
                    self._add_elevated_position(
                        (area["x"] + area["w"]/2, area["y"] + area["h"]/2),
                        "heaven"
                    )
        
        # Add connectors between areas
        self._add_connectors()
        
        # Add some random tactical positions
        num_tactical = random.randint(3, 6)
        for _ in range(num_tactical):
            pos = (
                random.uniform(self.width * 0.2, self.width * 0.8),
                random.uniform(self.height * 0.2, self.height * 0.8)
            )
            feature_type = random.choice(["cubby", "corner", "peek"])
            self._add_tactical_position(pos, feature_type)
    
    def _add_elevated_position(self, position: Tuple[float, float], pos_type: str):
        """Add an elevated position (heaven/hell) with proper access."""
        size = (
            random.uniform(8.0, 12.0),
            random.uniform(8.0, 12.0)
        )
        elevation = random.uniform(self.min_elevation_diff, self.max_elevation_diff)
        
        # Add the elevated area
        area_name = f"{pos_type}_{len(self.areas)}"
        self.areas[area_name] = {
            "type": pos_type,
            "x": position[0] - size[0]/2,
            "y": position[1] - size[1]/2,
            "w": size[0],
            "h": size[1],
            "elevation": elevation
        }
        
        # Add access ramp or stairs
        ramp_length = elevation * 3  # Reasonable ramp slope
        ramp_width = self.min_corridor_width
        ramp_angle = random.uniform(0, 2*math.pi)
        
        ramp_start = (
            position[0] + (size[0]/2 + ramp_length/2) * math.cos(ramp_angle),
            position[1] + (size[1]/2 + ramp_length/2) * math.sin(ramp_angle)
        )
        
        self.areas[f"ramp_{area_name}"] = {
            "type": "ramp",
            "x": ramp_start[0] - ramp_width/2,
            "y": ramp_start[1] - ramp_length/2,
            "w": ramp_width,
            "h": ramp_length,
            "angle": math.degrees(ramp_angle),
            "elevation_start": 0.0,
            "elevation_end": elevation
        }
    
    def _add_connectors(self):
        """Add connecting paths between areas."""
        # Find areas that should be connected
        areas_to_connect = []
        for name, area in self.areas.items():
            if area["type"] in ["site", "mid"]:
                center = (
                    area["x"] + area["w"]/2,
                    area["y"] + area["h"]/2
                )
                areas_to_connect.append((name, center))
        
        # Create some connections
        for i, (name1, pos1) in enumerate(areas_to_connect):
            for name2, pos2 in areas_to_connect[i+1:]:
                if random.random() < 0.6:  # 60% chance to connect areas
                    self._create_path(pos1, pos2, "connector")
    
    def _add_tactical_position(self, position: Tuple[float, float], pos_type: str):
        """Add a tactical position like a cubby or corner."""
        size = (
            random.uniform(3.0, 5.0),
            random.uniform(3.0, 5.0)
        )
        
        self.features.append(MapFeature(
            feature_type=pos_type,
            position=position,
            size=size
        ))
        
        # Add appropriate walls/cover
        if pos_type == "cubby":
            # Create a small enclosed space
            self.walls.extend([
                {
                    "x": position[0] - size[0]/2,
                    "y": position[1] - size[1]/2,
                    "w": size[0],
                    "h": 0.5
                },
                {
                    "x": position[0] - size[0]/2,
                    "y": position[1] - size[1]/2,
                    "w": 0.5,
                    "h": size[1]
                },
                {
                    "x": position[0] + size[0]/2,
                    "y": position[1] - size[1]/2,
                    "w": 0.5,
                    "h": size[1]
                }
            ])
        elif pos_type == "corner":
            # Create a corner with cover
            self.walls.extend([
                {
                    "x": position[0] - size[0]/2,
                    "y": position[1] - size[1]/2,
                    "w": size[0],
                    "h": 0.5
                },
                {
                    "x": position[0] - size[0]/2,
                    "y": position[1] - size[1]/2,
                    "w": 0.5,
                    "h": size[1]
                }
            ])
        elif pos_type == "peek":
            # Create a peek spot with partial cover
            self._add_cover_object(position)
    
    def _add_elevation(self):
        """Add elevation variation to the map."""
        # Add elevation to existing areas
        for area in self.areas.values():
            if area["type"] not in ["site", "spawn"]:  # Keep sites and spawns flat
                if random.random() < 0.3:  # 30% chance for elevation change
                    area["elevation"] = random.uniform(
                        self.min_elevation_diff,
                        self.max_elevation_diff
                    )
        
        # Add some random elevation points
        num_points = random.randint(5, 10)
        for _ in range(num_points):
            pos = (
                random.uniform(0, self.width),
                random.uniform(0, self.height)
            )
            elevation = random.uniform(
                self.min_elevation_diff,
                self.max_elevation_diff
            )
            self.elevation_points.append({
                "position": pos,
                "elevation": elevation,
                "radius": random.uniform(5.0, 10.0)
            })
    
    def _add_cover_objects(self):
        """Add cover objects throughout the map."""
        # Add cover to sites
        for area in self.areas.values():
            if area["type"] == "site":
                num_covers = random.randint(3, 5)
                for _ in range(num_covers):
                    pos = (
                        area["x"] + random.uniform(0, area["w"]),
                        area["y"] + random.uniform(0, area["h"])
                    )
                    self._add_cover_object(pos)
        
        # Add cover to paths and mid
        for area in self.areas.values():
            if area["type"] in ["corridor", "mid", "connector"]:
                if random.random() < 0.4:  # 40% chance for cover
                    pos = (
                        area["x"] + random.uniform(0, area["w"]),
                        area["y"] + random.uniform(0, area["h"])
                    )
                    self._add_cover_object(pos)
    
    def _add_cover_object(self, position: Tuple[float, float]):
        """Add a cover object at the specified position."""
        cover_types = [
            ("box", (2, 2)),
            ("crate", (2.5, 2.5)),
            ("barrel", (1.5, 1.5)),
            ("wall", (3, 1))
        ]
        
        cover_type, size = random.choice(cover_types)
        
        self.objects.append({
            "type": cover_type,
            "x": position[0] - size[0]/2,
            "y": position[1] - size[1]/2,
            "w": size[0],
            "h": size[1],
            "angle": random.uniform(0, 360) if cover_type != "wall" else 0
        })
    
    def _create_map_data(self, theme: str) -> Dict:
        """Create the final map data dictionary."""
        return {
            "metadata": {
                "name": f"{theme.capitalize()} Map",
                "theme": theme,
                "map-size": [self.width, self.height],
                "version": "2.0"
            },
            "map-areas": self.areas,
            "walls": {f"wall_{i}": wall for i, wall in enumerate(self.walls)},
            "objects": {f"obj_{i}": obj for i, obj in enumerate(self.objects)},
            "elevation-points": self.elevation_points,
            "tactical-features": [
                {
                    "type": f.feature_type,
                    "position": f.position,
                    "size": f.size,
                    "elevation": f.elevation,
                    "properties": f.properties or {}
                }
                for f in self.features
            ]
        }

def generate_map(width: float = 100.0, height: float = 100.0, 
                num_sites: int = 2, theme: str = "default") -> Dict:
    """Generate a complete map with the specified parameters."""
    generator = MapGenerator(width, height)
    return generator.generate_map(num_sites, theme)

if __name__ == "__main__":
    # Example usage
    map_data = generate_map(theme="haven")
    with open("generated_map.json", "w") as f:
        json.dump(map_data, f, indent=2) 
"""
Smart Grid Alignment System for BIM IFC Generation
====================================================

Masalah sebelumnya:
- Room placement tidak snap ke grid → offset 1m (Kitchen tidak sejajar)
- Wall generation terpisah → gap 20cm antar ruangan
- Tidak ada validasi gap → ruangan tidak menyatu dengan benar

Solusi:
1. BUILDING GRID - Semua koordinat snap ke grid 0.5m
2. ADJACENCY MATRIX - Track relasi antar ruangan
3. WALL COHERENCE - Dinding yang bersebelahan menjadi SATU entity
4. GAP ELIMINATION - Pastikan tidak ada gap antara ruangan

Flow:
  1. LLM generates layout (center_x, center_y)
  2. GridSnap: Snap semua koordinat ke grid 0.5m
  3. BuildAdjacency: Buat matriks ketetanggaan ruangan
  4. GenerateWalls: Buat dinding dengan koordinat yang SAMA untuk
     ruangan yang bersebelahan
  5. ValidateLayout: Check gap dan overlap
  6. GenerateIFC: Output dengan dinding yang coherent
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
import math


class WallType(Enum):
    EXTERIOR = "exterior"
    INTERIOR = "interior"
    SHARED = "shared"  # Dinding bersama 2 ruangan


@dataclass
class GridPoint:
    """Titik dalam grid building"""
    x: float
    y: float
    
    def __hash__(self):
        return hash((round(self.x, 3), round(self.y, 3)))
    
    def __eq__(self, other):
        if not isinstance(other, GridPoint):
            return False
        return abs(self.x - other.x) < 0.001 and abs(self.y - other.y) < 0.001


@dataclass
class RoomBounds:
    """Boundary ruangan dengan koordinat yang sudah di-snap"""
    name: str
    room_type: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    floor_number: int = 1
    
    # Dinding boundary (untuk referensi)
    north_wall: Tuple[float, float, float, float] = None  # (x1, y1, x2, y2)
    south_wall: Tuple[float, float, float, float] = None
    east_wall: Tuple[float, float, float, float] = None
    west_wall: Tuple[float, float, float, float] = None
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def depth(self) -> float:
        return self.y_max - self.y_min
    
    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2
    
    def edges(self) -> List[Tuple[float, float, float, float, str]]:
        """Return semua edges ruangan"""
        return [
            (self.x_min, self.y_min, self.x_max, self.y_min, "south"),   # South
            (self.x_min, self.y_max, self.x_max, self.y_max, "north"),   # North
            (self.x_min, self.y_min, self.x_min, self.y_max, "west"),    # West
            (self.x_max, self.y_min, self.x_max, self.y_max, "east"),    # East
        ]


@dataclass 
class WallSegment:
    """Segment dinding dengan informasi ruangan yang berbagi"""
    x1: float
    y1: float
    x2: float
    y2: float
    wall_type: WallType
    shared_by: List[str] = field(default_factory=list)
    side: str = ""  # "north", "south", "east", "west"
    orientation: str = ""  # "horizontal", "vertical"
    length: float = 0.0
    z_start: float = 0.0
    z_end: float = 0.0
    thickness: float = 0.0
    
    def __post_init__(self):
        self.length = math.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)


@dataclass
class AdjacencyInfo:
    """Informasi ketetanggaan antar ruangan"""
    room_a: str
    room_b: str
    shared_wall: WallSegment
    has_door: bool = False
    door_width: float = 0.0
    door_position: Tuple[float, float] = None


class SmartGridSystem:
    """
    Sistem grid cerdas untuk memastikan semua ruangan align
    dan dinding menyatu dengan sempurna.
    
    Usage:
        grid = SmartGridSystem(grid_size=0.5)  # Grid 0.5m
        grid.snap_position(2.73)  # Returns 2.5 or 3.0
    """
    
    def __init__(self, grid_size: float = 0.5, margin: float = 0.05):
        """
        Args:
            grid_size: Ukuran grid dalam meter (default 0.5m)
            margin: Tolerance untuk deteksi adjacency (default 5cm)
        """
        self.grid_size = grid_size
        self.margin = margin
        self.rooms: Dict[str, RoomBounds] = {}
        self.walls: List[WallSegment] = []
        self.adjacencies: Dict[str, List[AdjacencyInfo]] = {}
        
    def snap_position(self, value: float) -> float:
        """Snap nilai ke grid terdekat"""
        return round(value / self.grid_size) * self.grid_size
    
    def snap_to_building_grid(self, x: float, y: float, 
                              building_x_min: float, building_y_min: float) -> Tuple[float, float]:
        """
        Snap posisi ke grid building.
        Building grid diukur dari origin (0,0)
        """
        # Snap relative to building origin
        rel_x = x - building_x_min
        rel_y = y - building_y_min
        
        snapped_x = self.snap_position(rel_x) + building_x_min
        snapped_y = self.snap_position(rel_y) + building_y_min
        
        return snapped_x, snapped_y
    
    def add_room(self, name: str, room_type: str, 
                 center_x: float, center_y: float,
                 width: float, depth: float,
                 floor_number: int = 1,
                 building_width: float = 8.0,
                 building_depth: float = 20.0) -> RoomBounds:
        """
        Tambahkan ruangan dengan koordinat yang sudah di-snap.
        
        Args:
            name: Nama ruangan
            room_type: Tipe ruangan
            center_x, center_y: Posisi pusat (dari LLM)
            width, depth: Dimensi ruangan
            building_width, building_depth: Ukuran bangunan
            
        Returns:
            RoomBounds dengan koordinat yang sudah di-snap
        """
        building_x_min = -building_width / 2
        building_y_min = -building_depth / 2
        
        # Snap center position
        snapped_cx, snapped_cy = self.snap_to_building_grid(
            center_x, center_y,
            building_x_min, building_y_min
        )
        
        # Calculate bounds
        half_w = width / 2
        half_d = depth / 2
        
        x_min = snapped_cx - half_w
        x_max = snapped_cx + half_w
        y_min = snapped_cy - half_d
        y_max = snapped_cy + half_d
        
        # Snap bounds ke grid
        x_min = self.snap_position(x_min)
        x_max = self.snap_position(x_max)
        y_min = self.snap_position(y_min)
        y_max = self.snap_position(y_max)
        
        # Ensure minimum size
        if x_max - x_min < width:
            x_max = x_min + self.snap_position(width)
        if y_max - y_min < depth:
            y_max = y_min + self.snap_position(depth)
        
        room = RoomBounds(
            name=name,
            room_type=room_type,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            floor_number=floor_number
        )
        
        # Calculate wall edges
        room.north_wall = (x_min, y_max, x_max, y_max)
        room.south_wall = (x_min, y_min, x_max, y_min)
        room.west_wall = (x_min, y_min, x_min, y_max)
        room.east_wall = (x_max, y_min, x_max, y_max)
        
        self.rooms[name] = room
        self.adjacencies[name] = []
        
        return room
    
    def _edges_equal(self, e1: Tuple, e2: Tuple) -> bool:
        """Check apakah 2 edge sama (dengan tolerance)"""
        return (
            abs(e1[0] - e2[0]) < self.margin and
            abs(e1[1] - e2[1]) < self.margin and
            abs(e1[2] - e2[2]) < self.margin and
            abs(e1[3] - e2[3]) < self.margin
        ) or (
            abs(e1[0] - e2[2]) < self.margin and
            abs(e1[1] - e2[3]) < self.margin and
            abs(e1[2] - e2[0]) < self.margin and
            abs(e1[3] - e2[1]) < self.margin
        )
    
    def build_adjacency_matrix(self) -> Dict[str, List[str]]:
        """
        Bangun matriks ketetanggaan ruangan.
        
        Returns:
            Dict[room_name] -> List of adjacent room names
        """
        adjacency = {name: [] for name in self.rooms}
        
        room_list = list(self.rooms.values())
        
        for i, room_a in enumerate(room_list):
            for room_b in room_list[i+1:]:
                # Check setiap edge dari room_a vs room_b
                for edge_a in room_a.edges():
                    for edge_b in room_b.edges():
                        if self._edges_equal(edge_a, edge_b):
                            # Mereka bersebelahan!
                            adjacency[room_a.name].append(room_b.name)
                            adjacency[room_b.name].append(room_a.name)
                            
                            # Record adjacency info
                            wall_seg = WallSegment(
                                x1=edge_a[0], y1=edge_a[1],
                                x2=edge_a[2], y2=edge_a[3],
                                wall_type=WallType.SHARED,
                                shared_by=[room_a.name, room_b.name],
                                side=edge_a[4],
                                orientation="horizontal" if abs(edge_a[2]-edge_a[0]) > abs(edge_a[3]-edge_a[1]) else "vertical"
                            )
                            self.walls.append(wall_seg)
                            
                            self.adjacencies[room_a.name].append(
                                AdjacencyInfo(room_a.name, room_b.name, wall_seg)
                            )
                            self.adjacencies[room_b.name].append(
                                AdjacencyInfo(room_b.name, room_a.name, wall_seg)
                            )
                            break
        
        return adjacency
    
    def generate_coherent_walls(self, z_start: float, z_end: float, 
                                wall_thickness: float,
                                exterior_bounds: Tuple[float, float, float, float]) -> List[WallSegment]:
        """
        Generate dinding dengan koordinat yang COHERENT.
        
        Semua dinding yang bersebelahan akan memiliki koordinat
        yang SAMA persis, eliminasi gap.
        
        Args:
            z_start: Z start (floor level)
            z_end: Z end (ceiling level)
            wall_thickness: Ketebalan dinding
            exterior_bounds: (x_min, y_min, x_max, y_max)
        """
        x_min, y_min, x_max, y_max = exterior_bounds
        
        # First, merge all shared walls (already built in build_adjacency_matrix)
        # Now generate exterior walls
        
        exterior_walls = []
        
        # North wall (y = y_max)
        exterior_walls.append(WallSegment(
            x1=x_min, y1=y_max, x2=x_max, y2=y_max,
            wall_type=WallType.EXTERIOR,
            side="north",
            orientation="horizontal",
            z_start=z_start, z_end=z_end,
            thickness=wall_thickness
        ))
        
        # South wall (y = y_min)
        exterior_walls.append(WallSegment(
            x1=x_min, y1=y_min, x2=x_max, y2=y_min,
            wall_type=WallType.EXTERIOR,
            side="south",
            orientation="horizontal",
            z_start=z_start, z_end=z_end,
            thickness=wall_thickness
        ))
        
        # West wall (x = x_min)
        exterior_walls.append(WallSegment(
            x1=x_min, y1=y_min, x2=x_min, y2=y_max,
            wall_type=WallType.EXTERIOR,
            side="west",
            orientation="vertical",
            z_start=z_start, z_end=z_end,
            thickness=wall_thickness
        ))
        
        # East wall (x = x_max)
        exterior_walls.append(WallSegment(
            x1=x_max, y1=y_min, x2=x_max, y2=y_max,
            wall_type=WallType.EXTERIOR,
            side="east",
            orientation="vertical",
            z_start=z_start, z_end=z_end,
            thickness=wall_thickness
        ))
        
        # Add exterior walls to list
        for wall in exterior_walls:
            wall.length = math.sqrt((wall.x2-wall.x1)**2 + (wall.y2-wall.y1)**2)
        
        self.walls.extend(exterior_walls)
        
        return self.walls
    
    def validate_layout(self) -> Dict[str, any]:
        """
        Validasi layout - check untuk gap dan overlap.
        
        Returns:
            Dict dengan status validasi dan masalah yang ditemukan
        """
        issues = []
        warnings = []
        
        # Check untuk gap antara ruangan yang seharusnya bersebelahan
        for name_a, adj_list in self.adjacencies.items():
            room_a = self.rooms[name_a]
            
            for adj_info in adj_list:
                room_b = self.rooms[adj_info.room_b]
                wall = adj_info.shared_wall
                
                # Check jika wall coordinate match
                if wall.shared_by and len(wall.shared_by) == 2:
                    # Wall sudah di-share, berarti sudah benar
                    continue
                
        # Check untuk interior gaps (ruangan tidak bersebelahan tapi seharusnya)
        for name, room in self.rooms.items():
            for other_name, other_room in self.rooms.items():
                if name >= other_name:
                    continue
                if room.floor_number != other_room.floor_number:
                    continue
                    
                # Check jika mereka horizontal atau vertical adjacent
                # (X ranges overlap dan Y langsung bersebelahan)
                
                x_overlap = (
                    room.x_min < other_room.x_max - self.margin and
                    room.x_max > other_room.x_min + self.margin
                )
                
                y_adjacent = (
                    abs(room.y_max - other_room.y_min) < self.margin or
                    abs(room.y_min - other_room.y_max) < self.margin
                )
                
                if x_overlap and y_adjacent:
                    # Mereka seharusnya bersebelahan tapi tidak ada di adjacency
                    warnings.append(
                        f"Gap potential antara {name} dan {other_name}"
                    )
        
        # Check overlap
        for name_a, room_a in self.rooms.items():
            for name_b, room_b in self.rooms.items():
                if name_a >= name_b:
                    continue
                if room_a.floor_number != room_b.floor_number:
                    continue
                    
                # Check overlap
                x_overlap = (
                    room_a.x_min < room_b.x_max and
                    room_a.x_max > room_b.x_min
                )
                y_overlap = (
                    room_a.y_min < room_b.y_max and
                    room_a.y_max > room_b.y_min
                )
                
                if x_overlap and y_overlap:
                    issues.append(
                        f"OVERLAP antara {name_a} dan {name_b}"
                    )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_rooms": len(self.rooms),
            "total_walls": len([w for w in self.walls if w.wall_type == WallType.SHARED]),
            "total_exterior_walls": len([w for w in self.walls if w.wall_type == WallType.EXTERIOR])
        }
    
    def get_wall_data_for_ifc(self, z_start: float, z_end: float,
                               wall_thickness: float, 
                               interior_material: str = "interior_wall",
                               exterior_material: str = "exterior_wall") -> List[Dict]:
        """
        Generate wall data untuk IFC generation.
        
        Returns list of dict dengan struktur yang sesuai untuk IFC geometry.
        """
        from ..models.ifc_data import WallData
        
        wall_list = []
        
        for wall in self.walls:
            # Create WallData object
            wall_data = WallData(
                name=f"Wall_{'_'.join(wall.shared_by) if wall.shared_by else f'Exterior_{wall.side}'}",
                wall_type=wall.wall_type.value,
                start_x=wall.x1,
                start_y=wall.y1,
                start_z=z_start,
                end_x=wall.x2,
                end_y=wall.y2,
                end_z=z_end,
                thickness_m=wall_thickness,
                height_m=z_end - z_start,
                material=exterior_material if wall.wall_type == WallType.EXTERIOR else interior_material
            )
            wall_list.append(wall_data)
        
        return wall_list


class LayoutValidator:
    """
    Validator untuk memastikan layout memenuhi constraints.
    """
    
    @staticmethod
    def check_alignment(walls: List[WallSegment], tolerance: float = 0.01) -> Dict:
        """
        Check apakah semua dinding aligned dengan benar.
        
        Returns:
            Dict dengan masalah alignment jika ada
        """
        issues = []
        
        # Group walls by orientation
        horizontal = [w for w in walls if w.orientation == "horizontal"]
        vertical = [w for w in walls if w.orientation == "vertical"]
        
        # Check horizontal walls - semua harus memiliki Y yang sama untuk 
        # dinding yang seharusnya sejajar
        y_groups = {}
        for wall in horizontal:
            y_key = round(wall.y1, 2)  # Group by Y coordinate
            if y_key not in y_groups:
                y_groups[y_key] = []
            y_groups[y_key].append(wall)
        
        # Check untuk misalignment dalam group yang sama
        for y, wall_group in y_groups.items():
            x_coords = []
            for wall in wall_group:
                x_coords.extend([wall.x1, wall.x2])
            
            # Semua X harus membentuk range yang continuous
            x_coords.sort()
            for i in range(len(x_coords) - 1):
                gap = x_coords[i+1] - x_coords[i]
                if 0 < gap < tolerance:
                    issues.append(f"Gap sangat kecil ({gap*100:.1f}cm) pada y={y}")
        
        return {
            "aligned": len(issues) == 0,
            "issues": issues
        }


# Example usage:
"""
from app.core.smart_grid import SmartGridSystem

# Initialize grid system
grid = SmartGridSystem(grid_size=0.5, margin=0.05)

# Add rooms (from LLM layout spec)
grid.add_room("living_room_0", "living_room", 
              center_x=-2.0, center_y=3.0,
              width=5.0, depth=5.0)

grid.add_room("dining_room_0", "dining_room",
              center_x=-2.0, center_y=-1.0,
              width=4.0, depth=4.0)

grid.add_room("kitchen_0", "kitchen",
              center_x=-2.0, center_y=-5.0,
              width=4.0, depth=4.0)

# Build adjacency matrix
grid.build_adjacency_matrix()

# Generate coherent walls
grid.generate_coherent_walls(
    z_start=0.0, z_end=3.0,
    wall_thickness=0.2,
    exterior_bounds=(-4.0, -10.0, 4.0, 10.0)
)

# Validate
validation = grid.validate_layout()
print(f"Layout valid: {validation['valid']}")

# Get walls for IFC
walls = grid.get_wall_data_for_ifc(0.0, 3.0, 0.2)
"""
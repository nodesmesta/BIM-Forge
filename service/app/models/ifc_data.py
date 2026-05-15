from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Low-level data contracts, no dependencies
@dataclass
class WallData:
    name: str
    wall_type: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    start_z: float
    end_z: float
    thickness_m: float
    height_m: float
    material: str

@dataclass
class DoorData:
    name: str
    width_m: float
    height_m: float
    center_x: float
    center_y: float
    center_z: float
    thickness_m: float
    rotation_deg: float
    wall_name: str
    swing_direction: str
    # New fields for smart placement
    connects_spaces: Optional[List[str]] = None  # 2 ruang yang dihubungkan (None untuk entrance)
    wall_segment: Optional[tuple] = None  # (sx, sy, ex, ey)
    wall_side: Optional[str] = None  # "north", "south", "east", "west"
    wall_orientation: Optional[str] = None  # "horizontal" atau "vertical"
    is_entrance: bool = False  # True untuk pintu utama (masuk ke bangunan)

@dataclass
class WindowData:
    name: str
    width_m: float
    height_m: float
    center_x: float
    center_y: float
    sill_height_m: float
    thickness_m: float
    rotation_deg: float
    wall_name: str
    window_type: str
    # New fields for smart placement
    wall_segment: Optional[tuple] = None  # (sx, sy, ex, ey)
    wall_side: Optional[str] = None  # "north", "south", "east", "west"
    wall_orientation: Optional[str] = None  # "horizontal" atau "vertical"

@dataclass
class SpaceData:
    name: str
    room_type: str
    center_x: float
    center_y: float
    width_m: float
    length_m: float
    ifc_class: str
    area_sqm: float
    zone: str
    window_placement: bool
    # Enhanced fields for rich design data
    interior: Optional[Dict[str, Any]] = None
    exterior: Optional[Dict[str, Any]] = None
    mep: Optional[Dict[str, Any]] = None
    materials: Optional[Dict[str, Any]] = None
    blenderkit: Optional[Dict[str, Any]] = None
    # Wall bounds for furniture placement (from CoordinatorAgent)
    wall_bounds: Optional[Dict[str, Any]] = None

@dataclass
class RoofData:
    name: str
    type: str
    slope_deg: float
    overhang_m: float
    thickness_m: float
    material: str
    insulation_thickness_m: Optional[float] = None
    ventilation: Optional[str] = None
    reasoning: Optional[str] = None

@dataclass
class SiteData:
    name: str
    total_area_sqm: float
    building_footprint_sqm: float
    setback_front: float
    setback_back: float
    setback_left: float
    setback_right: float

@dataclass
class BuildingData:
    name: str
    width_m: float
    depth_m: float

# High-level data contracts that depend on the above

@dataclass
class FloorData:
    name: str
    floor_number: int
    height_m: float
    exterior_bounds: dict
    walls: List[WallData] = field(default_factory=list)
    doors: List[DoorData] = field(default_factory=list)
    windows: List[WindowData] = field(default_factory=list)
    spaces: List[SpaceData] = field(default_factory=list)

@dataclass
class ArchitecturalDesignData:
    site: SiteData
    building: BuildingData
    floors: List[FloorData]
    roof: RoofData
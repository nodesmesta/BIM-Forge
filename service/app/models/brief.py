from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class ProjectType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"
    MIXED_USE = "mixed_use"


class ResidentialType(str, Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    TOWNHOUSE = "townhouse"
    VILLA = "villa"


class BudgetRange(str, Enum):
    ECONOMY = "economy"
    MEDIUM = "medium"
    PREMIUM = "premium"
    LUXURY = "luxury"


class SiteOrientation(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTH_EAST = "north_east"
    NORTH_WEST = "north_west"
    SOUTH_EAST = "south_east"
    SOUTH_WEST = "south_west"


class ClientRequirement(BaseModel):
    requirement_type: str
    description: str
    priority: str = "medium"
    is_mandatory: bool = False
    details: Dict = {}


class RoomRequirement(BaseModel):
    """Room requirement with count and area specifications."""
    count: int
    min_area_m2: float = 4.0
    max_area_m2: Optional[float] = None
    features: List[str] = []


class ArchitecturalParameters(BaseModel):
    floor_height_ground: float = Field(default=3.5, ge=2.5, le=5.0)
    floor_height_upper: float = Field(default=3.0, ge=2.5, le=4.5)
    floor_to_ceiling: float = Field(default=3.0, ge=2.4, le=4.0)
    slab_thickness: float = Field(default=0.15, ge=0.1, le=0.3)
    wall_thickness_exterior: float = Field(default=0.2, ge=0.15, le=0.4)
    wall_thickness_interior: float = Field(default=0.1, ge=0.08, le=0.2)
    roof_overhang: float = Field(default=0.5, ge=0.3, le=1.5)
    roof_thickness: float = Field(default=0.15, ge=0.1, le=0.3)
    room_width: float = Field(default=4.0, ge=2.0, le=10.0)
    room_length: float = Field(default=4.0, ge=2.0, le=10.0)
    corridor_width: float = Field(default=1.2, ge=0.9, le=2.5)
    staircase_width: float = Field(default=1.2, ge=1.0, le=1.5)
    building_width: Optional[float] = None
    building_depth: Optional[float] = None
    foundation_type: str = "shallow"
    structural_system: str = "frame"

    @property
    def width_m(self) -> float:
        return self.room_width

    @property
    def length_m(self) -> float:
        return self.room_length


class SiteParameters(BaseModel):
    plot_area: Optional[float] = None
    plot_width: Optional[float] = None
    plot_length: Optional[float] = None
    orientation: Optional[SiteOrientation] = None
    topography: Optional[str] = None
    soil_type: Optional[str] = None
    access_direction: Optional[SiteOrientation] = None
    setback_front: float = Field(default=3.0, ge=0, le=10)
    setback_back: float = Field(default=2.0, ge=0, le=10)
    setback_left: float = Field(default=2.5, ge=0, le=10)
    setback_right: float = Field(default=2.5, ge=0, le=10)


class ZoningRegulation(BaseModel):
    max_building_height: Optional[float] = None
    max_building_area: Optional[float] = None
    max_building_coverage: Optional[float] = None
    max_floor_area_ratio: Optional[float] = None
    min_front_setback: Optional[float] = None
    min_back_setback: Optional[float] = None
    min_side_setback: Optional[float] = None
    min_open_space: Optional[float] = None
    parking_requirement: Optional[str] = None


class ZoningAnalysis(BaseModel):
    project_id: Optional[str] = None
    site_parameters: Optional[SiteParameters] = None
    zoning_regulations: Optional[ZoningRegulation] = None
    buildable_area: Optional[float] = None
    max_building_volume: Optional[float] = None
    setbacks: Dict[str, float] = {}
    orientation_analysis: Dict = {}
    restrictions: List[str] = []
    recommendations: List[str] = []
    compliance_notes: List[str] = []


class ProjectBrief(BaseModel):
    project_id: Optional[str] = None
    project_type: ProjectType = ProjectType.RESIDENTIAL
    residential_type: Optional[ResidentialType] = None
    title: str = ""
    description: str = ""
    requirements: List[ClientRequirement] = []
    desired_features: List[str] = []
    constraints: List[str] = []
    budget_range: Optional[BudgetRange] = None
    target_completion: Optional[str] = None
    style_preference: Optional[str] = None
    floor_count: Optional[int] = None
    approximate_area: Optional[float] = None
    room_requirements: Dict[str, RoomRequirement] = {}
    notes: List[str] = []
    architectural_params: Optional[ArchitecturalParameters] = None
    site_params: Optional[SiteParameters] = None


class BriefAndZoning(BaseModel):
    brief: Optional[ProjectBrief] = None
    zoning: Optional[ZoningAnalysis] = None

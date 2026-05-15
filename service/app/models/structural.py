"""
Structural design models for building engineering.
Contains all data structures for structural analysis and design.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class FoundationType(str, Enum):
    """Foundation system types."""
    STRIP = "strip"  # Tapak menerus
    RAFT = "raft"    # Pelat menerus
    PILED = "piled"  # Tiang pancang
    ISOLATED = "isolated"  # Tapak tunggal


class StructuralMemberType(str, Enum):
    """Types of structural members."""
    BEAM = "beam"
    COLUMN = "column"
    SLAB = "slab"
    WALL = "wall"
    FOOTING = "footing"


class MaterialGrade(str, Enum):
    """Concrete and steel material grades (Indonesian standards)."""
    CONCRETE_K225 = "K-225"
    CONCRETE_K300 = "K-300"
    CONCRETE_K350 = "K-350"
    CONCRETE_K400 = "K-400"
    STEEL_BJTP40 = "BJTP-40"
    STEEL_BJTS50 = "BJTS-50"


class ReinforcementType(str, Enum):
    """Reinforcement bar types."""
    ROUND = "round"
    DEFORMED = "deformed"


class Dimensions(BaseModel):
    """3D dimensions."""
    width: float = Field(..., description="Width in meters")
    depth: float = Field(..., description="Depth in meters")
    height: float = Field(..., description="Height in meters")


class SpatialLocation(BaseModel):
    """Spatial location of an element."""
    floor_number: int = 1
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ReinforcementSpec(BaseModel):
    """Reinforcement specification for concrete elements."""
    main_bar_diameter: float = Field(..., description="Main bar diameter in mm")
    main_bar_count: int = Field(..., description="Number of main bars")
    stirrup_diameter: float = Field(..., description="Stirrup diameter in mm")
    stirrup_spacing: float = Field(..., description="Stirrup spacing in mm")
    cover: float = Field(..., description="Concrete cover in mm")
    bar_type: ReinforcementType = ReinforcementType.DEFORMED


class FoundationSystem(BaseModel):
    """Foundation design data."""
    foundation_type: FoundationType
    depth: float = Field(..., description="Foundation depth in meters")
    bearing_capacity: float = Field(..., description="Soil bearing capacity in kPa")
    width: float = Field(..., description="Foundation width in meters")
    length: float = Field(..., description="Foundation length in meters")
    thickness: float = Field(..., description="Foundation thickness in meters")
    concrete_grade: MaterialGrade = MaterialGrade.CONCRETE_K300
    reinforcement: Optional[ReinforcementSpec] = None
    location: Optional[SpatialLocation] = None


class StructuralMember(BaseModel):
    """Individual structural element."""
    member_type: StructuralMemberType
    designation: str  # B1, C1, S1, F1, etc.
    dimensions: Dimensions
    material_grade: MaterialGrade
    reinforcement: Optional[ReinforcementSpec] = None
    location: SpatialLocation
    load_bearing: bool = True
    span: Optional[float] = None  # Span length in meters
    support_type: Literal["simply_supported", "fixed", "continuous"] = "simply_supported"


class LoadCase(BaseModel):
    """Structural load case."""
    case_name: str
    dead_load: float = Field(..., description="Dead load in kN/m2")
    live_load: float = Field(..., description="Live load in kN/m2")
    seismic_factor: Optional[float] = None
    wind_factor: Optional[float] = None
    load_combination: str = "1.2D + 1.6L"


class StructuralDesign(BaseModel):
    """Complete structural design data."""
    system_type: Literal["RC_FRAME", "STEEL_FRAME", "MASONRY", "HYBRID"]
    foundation_design: List[FoundationSystem] = []
    columns: List[StructuralMember] = []
    beams: List[StructuralMember] = []
    slabs: List[StructuralMember] = []
    load_cases: List[LoadCase] = []
    seismic_zone: Optional[str] = None
    wind_zone: Optional[str] = None
    design_notes: List[str] = []

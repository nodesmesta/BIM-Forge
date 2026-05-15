"""
Material specification models for building construction.
Contains all data structures for material selection and quantity takeoffs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class MaterialCategory(str, Enum):
    """Material categories."""
    CONCRETE = "concrete"
    STEEL = "steel"
    MASONRY = "masonry"
    TIMBER = "timber"
    FINISH = "finish"
    GLASS = "glass"
    INSULATION = "insulation"
    WATERPROOF = "waterproofing"


class MaterialProperties(BaseModel):
    """Material physical and mechanical properties."""
    density: Optional[float] = Field(None, description="Density in kg/m3")
    compressive_strength: Optional[float] = Field(None, description="Compressive strength in MPa")
    tensile_strength: Optional[float] = Field(None, description="Tensile strength in MPa")
    thermal_conductivity: Optional[float] = Field(None, description="Thermal conductivity in W/mK")
    fire_rating: Optional[str] = Field(None, description="Fire resistance rating")
    water_absorption: Optional[float] = Field(None, description="Water absorption percentage")


class MaterialSpecification(BaseModel):
    """Detailed material specification."""
    material_id: str
    category: MaterialCategory
    type: str  # e.g., K-300, BJTP-40, Ceramic Tile
    name: str  # Human-readable name
    properties: Optional[MaterialProperties] = None
    unit_cost: float = 0.0
    unit: str = "m3"  # m3, kg, m2, m, pcs
    supplier: Optional[str] = None
    sustainability_rating: Optional[str] = None  # Green Mark, LEED, etc.
    application: Optional[str] = None  # Where this material is used


class MaterialTakeoff(BaseModel):
    """Quantified material requirements."""
    material_id: str
    quantity: float
    unit: str
    location: str  # which element/floor
    waste_factor: float = 0.0  # Waste percentage
    total_quantity: float = 0.0  # quantity * (1 + waste_factor/100)
    total_cost: float = 0.0


class MaterialSchedule(BaseModel):
    """Complete material schedule for a project."""
    materials: List[MaterialSpecification] = []
    takeoffs: List[MaterialTakeoff] = []
    total_material_cost: float = 0.0

    def add_material(self, material: MaterialSpecification):
        self.materials.append(material)

    def add_takeoff(self, takeoff: MaterialTakeoff):
        self.takeoffs.append(takeoff)
        self.total_material_cost += takeoff.total_cost

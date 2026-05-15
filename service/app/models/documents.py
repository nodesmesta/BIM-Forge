"""
Drawing and document models for construction documentation.
Contains all data structures for drawings, quantities, and BOQ.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class DrawingDiscipline(str, Enum):
    """Drawing discipline categories."""
    ARCH = "ARCH"  # Architectural
    STRUCT = "STRUCT"  # Structural
    MEP = "MEP"  # Mechanical, Electrical, Plumbing
    CIVIL = "CIVIL"  # Civil/Site


class DrawingType(str, Enum):
    """Types of drawings."""
    FLOOR_PLAN = "floor_plan"
    SITE_PLAN = "site_plan"
    ELEVATION = "elevation"
    SECTION = "section"
    DETAIL = "detail"
    SCHEDULE = "schedule"


class DrawingSet(BaseModel):
    """Complete drawing set metadata."""
    drawing_id: str
    discipline: DrawingDiscipline
    drawing_type: DrawingType
    sheet_number: str
    title: str
    scale: str
    file_path: Optional[str] = None
    revision: str = "A"
    dependencies: List[str] = []  # IFC entities or models used
    description: Optional[str] = None


class QuantityItem(BaseModel):
    """Bill of Quantities (BOQ) line item."""
    item_number: str
    description: str
    specification_ref: Optional[str] = None
    unit: str  # m, m2, m3, kg, pcs, etc.
    quantity: float
    unit_rate: float = 0.0
    total_cost: float = 0.0
    location: str = ""
    notes: Optional[str] = None


class AreaTakeoff(BaseModel):
    """Area takeoff for spaces/elements."""
    area_id: str
    area_name: str
    area_type: str  # floor, wall, roof, etc.
    gross_area: float
    net_area: float
    deductions: List[Dict] = []  # openings, etc.
    location: str


class VolumeTakeoff(BaseModel):
    """Volume takeoff for elements."""
    volume_id: str
    element_name: str
    element_type: str  # concrete, excavation, etc.
    gross_volume: float
    net_volume: float
    location: str


class CountTakeoff(BaseModel):
    """Count takeoff for items."""
    count_id: str
    item_name: str
    item_type: str  # door, window, fixture, etc.
    quantity: int
    specifications: Dict = {}
    location: str


class QuantityTakeoff(BaseModel):
    """Complete quantity takeoff data."""
    project_id: str
    area_takeoffs: List[AreaTakeoff] = []
    volume_takeoffs: List[VolumeTakeoff] = []
    count_takeoffs: List[CountTakeoff] = []
    boq_items: List[QuantityItem] = []
    total_construction_area: float = 0.0
    notes: List[str] = []

    def add_boq_item(self, item: QuantityItem):
        item.total_cost = item.quantity * item.unit_rate
        self.boq_items.append(item)

    def get_total_boq_cost(self) -> float:
        return sum(item.total_cost for item in self.boq_items)

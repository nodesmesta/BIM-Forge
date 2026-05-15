"""
Cost estimation (RAB - Rencana Anggaran Biaya) models.
Contains all data structures for construction cost estimation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class WorkItemType(str, Enum):
    """Construction work item categories."""
    CLEARING = "pekerjaan_pembersihan"
    FOUNDATION = "pekerjaan_fondasi"
    STRUCTURE = "pekerjaan_struktur"
    MASONRY = "pekerjaan_dinding"
    FLOORING = "pekerjaan_lantai"
    ROOFING = "pekerjaan_atap"
    JOINERY = "pekerjaan_kayu"
    PAINTING = "pekerjaan_cat"
    SANITARY = "pekerjaan_saniter"
    ELECTRICAL = "pekerjaan_listrik"
    PLUMBING = "pekerjaan_plumbing"
    OUTSIDE = "pekerjaan_luar"


class CostCategory(str, Enum):
    """Cost breakdown categories."""
    MATERIAL = "material"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    OVERHEAD = "overhead"
    PROFIT = "profit"


class RABItem(BaseModel):
    """Rencana Anggaran Biaya (RAB) line item."""
    item_code: str
    work_item: WorkItemType
    description: str
    specification_ref: Optional[str] = None
    unit: str  # m, m2, m3, kg, pcs, etc.
    quantity: float
    unit_price: float = 0.0
    total_price: float = 0.0
    labor_cost: float = 0.0
    material_cost: float = 0.0
    equipment_cost: float = 0.0
    hours_required: Optional[float] = None
    notes: Optional[str] = None


class UnitRate(BaseModel):
    """Unit rate database entry."""
    rate_code: str
    description: str
    unit: str
    base_price: float
    labor_rate: float = 0.0
    material_rate: float = 0.0
    equipment_rate: float = 0.0
    region: str = "Jakarta"
    last_updated: Optional[str] = None


class CostBreakdown(BaseModel):
    """Cost breakdown by category."""
    material_total: float = 0.0
    labor_total: float = 0.0
    equipment_total: float = 0.0
    subtotal: float = 0.0
    overhead_percentage: float = 5.0
    overhead_amount: float = 0.0
    profit_percentage: float = 10.0
    profit_amount: float = 0.0
    total: float = 0.0


class CostEstimation(BaseModel):
    """Complete cost estimation (RAB) for a project."""
    project_id: str
    rab_items: List[RABItem] = []
    cost_breakdown: CostBreakdown = Field(default_factory=CostBreakdown)
    contingency_percentage: float = 5.0
    contingency_amount: float = 0.0
    total_cost: float = 0.0
    cost_per_square_meter: float = 0.0
    total_building_area: float = 0.0
    currency: str = "IDR"
    valid_until: Optional[str] = None
    notes: List[str] = []

    def add_rab_item(self, item: RABItem):
        """Add a RAB item and recalculate totals."""
        item.total_price = item.quantity * item.unit_price
        self.rab_items.append(item)
        self._recalculate()

    def _recalculate(self):
        """Recalculate all cost totals."""
        # Calculate category totals
        material_total = sum(item.material_cost for item in self.rab_items)
        labor_total = sum(item.labor_cost for item in self.rab_items)
        equipment_total = sum(item.equipment_cost for item in self.rab_items)
        subtotal = sum(item.total_price for item in self.rab_items)

        # Calculate overhead and profit
        overhead_amount = subtotal * self.contingency_percentage / 100
        profit_amount = (subtotal + overhead_amount) * 10 / 100  # Default 10% profit

        # Total cost
        total_cost = subtotal + overhead_amount + profit_amount + self.contingency_amount

        # Update breakdown
        self.cost_breakdown = CostBreakdown(
            material_total=material_total,
            labor_total=labor_total,
            equipment_total=equipment_total,
            subtotal=subtotal,
            overhead_percentage=5.0,
            overhead_amount=overhead_amount,
            profit_percentage=10.0,
            profit_amount=profit_amount,
            total=total_cost
        )

        self.total_cost = total_cost

        # Cost per square meter
        if self.total_building_area > 0:
            self.cost_per_square_meter = total_cost / self.total_building_area

    def get_summary(self) -> Dict:
        """Get cost summary as dictionary."""
        return {
            "total_cost": self.total_cost,
            "material_cost": self.cost_breakdown.material_total,
            "labor_cost": self.cost_breakdown.labor_total,
            "equipment_cost": self.cost_breakdown.equipment_total,
            "overhead": self.cost_breakdown.overhead_amount,
            "profit": self.cost_breakdown.profit_amount,
            "contingency": self.contingency_amount,
            "cost_per_m2": self.cost_per_square_meter,
            "currency": self.currency
        }

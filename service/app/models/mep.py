"""
MEP (Mechanical, Electrical, Plumbing) design models.
Contains all data structures for building systems design.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class HVACType(str, Enum):
    """HVAC system types."""
    SPLIT = "split"
    CENTRAL = "central"
    VRF = "vrf"
    WINDOW = "window"
    PACKAGED = "packaged"


class ElectricalLoadType(str, Enum):
    """Electrical load categories."""
    LIGHTING = "lighting"
    POWER = "power"
    HVAC = "hvac"
    SPECIAL = "special"


class PlumbingFixtureType(str, Enum):
    """Plumbing fixture types."""
    TOILET = "toilet"
    SINK = "sink"
    SHOWER = "shower"
    BATHTUB = "bathtub"
    KITCHEN_SINK = "kitchen_sink"
    WASHING_MACHINE = "washing_machine"


class EquipmentSpec(BaseModel):
    """Equipment specification."""
    equipment_id: str
    equipment_type: str
    capacity: float
    capacity_unit: str
    power_consumption: Optional[float] = None
    voltage: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None


class DuctSegment(BaseModel):
    """HVAC duct segment."""
    segment_id: str
    start_point: List[float]  # [x, y, z]
    end_point: List[float]  # [x, y, z]
    width: float
    height: float
    airflow: float  # CFM or m3/h


class DiffuserSpec(BaseModel):
    """HVAC diffuser specification."""
    diffuser_id: str
    location: List[float]  # [x, y, z]
    size: str  # e.g., "600x600"
    airflow: float
    direction: str


class PanelSpec(BaseModel):
    """Electrical panel specification."""
    panel_id: str
    panel_type: str  # Main, Sub-panel
    voltage: int
    phases: int
    amperage: int
    num_circuits: int
    location: str


class CircuitSpec(BaseModel):
    """Electrical circuit specification."""
    circuit_id: str
    circuit_type: str
    voltage: int
    amperage: int
    wire_size: str
    conduit_size: str
    connected_load: float
    panel_id: str
    location: str


class LightingZone(BaseModel):
    """Lighting zone specification."""
    zone_id: str
    area: float
    lighting_level: float  # lux
    fixtures: List[str]  # fixture IDs
    control_type: str  # switch, dimmer, sensor


class PipeSegment(BaseModel):
    """Plumbing pipe segment."""
    segment_id: str
    start_point: List[float]
    end_point: List[float]
    diameter: float
    pipe_material: str
    flow_rate: Optional[float] = None


class FixtureSpec(BaseModel):
    """Plumbing fixture specification."""
    fixture_id: str
    fixture_type: PlumbingFixtureType
    water_supply_size: str  # pipe size
    drainage_size: str  # pipe size
    flow_rate: Optional[float] = None
    location: str


class HVACSystem(BaseModel):
    """HVAC system design."""
    system_type: HVACType
    cooling_load: float  # BTU/hr or kW
    heating_load: float  # BTU/hr or kW
    equipment: List[EquipmentSpec] = []
    duct_routing: List[DuctSegment] = []
    diffusers: List[DiffuserSpec] = []
    zones: List[str] = []  # Zone IDs


class ElectricalSystem(BaseModel):
    """Electrical system design."""
    connected_load: float  # VA or kW
    demand_factor: float = 0.8
    main_panel: Optional[PanelSpec] = None
    branch_circuits: List[CircuitSpec] = []
    lighting_zones: List[LightingZone] = []
    panel_schedule: List[Dict] = []
    grounding_type: str = "TN-S"


class PlumbingSystem(BaseModel):
    """Plumbing system design."""
    water_source: str
    main_pipe_size: float  # inches or mm
    branch_layout: List[PipeSegment] = []
    fixtures: List[FixtureSpec] = []
    water_heater: Optional[EquipmentSpec] = None
    drainage_system: str = "gravity"


class MEPDesign(BaseModel):
    """Complete MEP design data."""
    hvac_system: Optional[HVACSystem] = None
    electrical_system: Optional[ElectricalSystem] = None
    plumbing_system: Optional[PlumbingSystem] = None
    fire_protection: Optional[Dict] = None
    equipment_schedule: List[EquipmentSpec] = []
    design_notes: List[str] = []

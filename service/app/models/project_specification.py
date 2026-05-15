"""
Project Specification models for IFC-compliant building generation.

These models define the structured input schema that matches IFC standards
for site, building, floor, and room specifications.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


class StyleType(str, Enum):
  """Architectural style types."""
  MODERN = "modern"
  MINIMALIST = "minimalist"
  TROPICAL = "tropical"
  TRADITIONAL = "traditional"
  INDUSTRIAL = "industrial"
  MEDITERRANEAN = "mediterranean"


class RoomType(str, Enum):
  """IFC-compliant room types."""
  LIVING_ROOM = "living_room"
  DINING_ROOM = "dining_room"
  KITCHEN = "kitchen"
  BEDROOM = "bedroom"
  MASTER_BEDROOM = "master_bedroom"
  BATHROOM = "bathroom"
  OFFICE = "office"
  GUEST_ROOM = "guest_room"
  LAUNDRY = "laundry"
  STORAGE = "storage"
  GARAGE = "garage"
  CARPORT = "carport"
  HALLWAY = "hallway"
  STAIRCASE = "staircase"
  BALCONY = "balcony"
  TERRACE = "terrace"
  GARDEN = "garden"


class OrientationType(str, Enum):
  """Building orientation."""
  NORTH = "north"
  SOUTH = "south"
  EAST = "east"
  WEST = "west"


class LocationInfo(BaseModel):
  """Location information for solar analysis and local building codes."""
  name: str = Field(..., description="City/regency name")
  country: str = Field(..., description="Country name")
  latitude: float = Field(..., description="Latitude coordinate")
  longitude: float = Field(..., description="Longitude coordinate")
  timezone: str = Field("UTC", description="Timezone identifier")


class SiteSpecification(BaseModel):
  """Site and building dimension specifications."""
  total_land_area_m2: float = Field(..., description="Total luas tanah (m²)")
  building_footprint_m2: float = Field(..., description="Luas footprint bangunan per lantai (m²)")
  building_width_m: float = Field(..., description="Lebar bangunan (m)")
  building_depth_m: float = Field(..., description="Dalam bangunan (m)")
  orientation: OrientationType = Field(OrientationType.NORTH, description="Arah hadap bangunan")
  setback_north_m: float = Field(..., description="Jarak dari batas utara (m)")
  setback_south_m: float = Field(..., description="Jarak dari batas selatan (m)")
  setback_east_m: float = Field(..., description="Jarak dari batas timur (m)")
  setback_west_m: float = Field(..., description="Jarak dari batas barat (m)")
  slope_degree: float = Field(0.0, description="Kemiringan lahan (°)")
  shape_id: Optional[str] = Field(None, description="Shape type (rectangle, trapezoid, l-shape, triangle)")
  shape_dimensions: Optional[Dict[str, float]] = Field(None, description="Shape dimensions")


class FloorSpecification(BaseModel):
  """Floor-level specifications."""
  floor_number: int = Field(..., ge=1, description="Nomor lantai")
  height_m: float = Field(3.5, ge=2.5, le=5.0, description="Tinggi lantai dari slab ke slab (m)")
  ceiling_height_m: float = Field(3.0, ge=2.4, le=4.5, description="Tinggi plafon (m)")
  slab_thickness_m: float = Field(0.15, ge=0.1, le=0.3, description="Tebal slab (m)")
  purpose: str = Field("residential", description="Fungsi lantai (public/private/service)")


class RoomRequirement(BaseModel):
  """Room requirements with IFC-compliant specifications."""
  room_type: RoomType = Field(..., description="Tipe ruang")
  count: int = Field(..., ge=1, description="Jumlah ruang")
  min_width_m: float = Field(3.0, ge=1.5, description="Lebar minimum (m)")
  min_length_m: float = Field(3.0, ge=1.5, description="Dalam minimum (m)")
  min_area_m2: float = Field(..., gt=0, description="Luas minimum (m²)")
  preferred_floor: int = Field(1, ge=1, description="Lantai preferensi")
  adjacent_to: List[str] = Field([], description="Ruang yang harus berdekatan")
  exterior_access: bool = Field(False, description="Butuh akses exterior")
  private: bool = Field(False, description="Ruang privat")


class CirculationRequirement(BaseModel):
  """Circulation and vertical transportation."""
  corridor_width_m: float = Field(1.2, ge=0.9, le=2.0, description="Lebar koridor minimum (m)")
  staircase_width_m: float = Field(1.2, ge=1.0, le=1.5, description="Lebar tangga (m)")
  staircase_type: str = Field("straight", description="Jenis tangga")
  elevator: bool = Field(False, description="Butuh lift")


class ZoningPreference(BaseModel):
  """Zoning preferences for space classification."""
  public: List[str] = Field([], description="Ruang publik")
  private: List[str] = Field([], description="Ruang privat")
  service: List[str] = Field([], description="Ruang servis")


class LayoutConstraints(BaseModel):
  """Layout constraints for positioning."""
  entrance_position: str = Field("front_center", description="Posisi pintu masuk")
  kitchen_location: str = Field("rear", description="Lokasi dapur")
  master_bedroom_location: str = Field("rear_corner", description="Lokasi kamar utama")


class ProjectSpecification(BaseModel):
  """
  Complete project specification for IFC-compliant building generation.

  This model contains all the structured information needed to generate
  a valid IFC building model with proper layout, dimensions, and relationships.
  """
  project_name: str = Field(..., description="Nama proyek")
  style: StyleType = Field(StyleType.MODERN, description="Gaya arsitektur")

  # Location - for solar analysis and local building codes
  location: Optional[LocationInfo] = Field(None, description="Project location for solar and compliance analysis")

  # Site & Building
  site: SiteSpecification = Field(..., description="Site specifications")

  # Floors
  floors: List[FloorSpecification] = Field(..., min_length=1, description="Floor specifications")

  # Room Requirements
  rooms: List[RoomRequirement] = Field(..., min_length=1, description="Room requirements")

  # Circulation
  circulation: CirculationRequirement = Field(default_factory=CirculationRequirement)

  # Zoning
  zoning: Optional[ZoningPreference] = None

  # Layout Constraints
  constraints: Optional[LayoutConstraints] = None

  @validator('rooms')
  def validate_rooms_count(cls, v):
    """Validate that at least one room is specified."""
    if not v:
      raise ValueError('Minimal harus ada 1 room requirement')
    return v

  @validator('floors')
  def validate_floors_sorted(cls, v):
    """Validate floors are sorted by floor number."""
    return sorted(v, key=lambda f: f.floor_number)

  def get_rooms_by_floor(self, floor_number: int) -> List[RoomRequirement]:
    """Get all rooms for a specific floor."""
    return [r for r in self.rooms if r.preferred_floor == floor_number]

  def get_total_rooms_count(self) -> Dict[str, int]:
    """Get total count per room type."""
    counts = {}
    for room in self.rooms:
      key = room.room_type.value
      counts[key] = counts.get(key, 0) + room.count
    return counts

  def calculate_total_room_area(self) -> float:
    """Calculate total room area requirement."""
    return sum(r.min_area_m2 * r.count for r in self.rooms)

  def calculate_efficiency(self) -> float:
    """Calculate space efficiency ratio."""
    if not self.site.building_footprint_m2:
      return 0.0
    total_area = self.calculate_total_room_area()
    return (total_area / self.site.building_footprint_m2) * 100

  def get_solar_analysis_context(self) -> Dict[str, Any]:
    """
    Get solar analysis context for the location.
    This can be used by agents to make orientation and daylight decisions.
    """
    if not self.location:
      return {"enabled": False}

    return {
      "enabled": True,
      "location": {
        "name": self.location.name,
        "country": self.location.country,
        "latitude": self.location.latitude,
        "longitude": self.location.longitude,
        "timezone": self.location.timezone
      },
      "solar_notes": (
        f"Building orientation should consider sun path at {self.location.latitude}° latitude. "
        f"Primary windows should avoid direct west exposure for thermal comfort."
      )
    }


class StructuredGenerateRequest(BaseModel):
  """Request model for structured building generation."""
  prompt: str  # JSON string or regular prompt
  is_structured: bool = False
  specification: Optional[ProjectSpecification] = None
  priority: int = 1
  budget_limit: Optional[float] = None
  max_revisions: int = 3

"""
Structured specification to ProjectBrief converter.

Converts structured frontend specification directly to ProjectBrief
without any LLM involvement. This is a pure field mapping operation.
"""

from typing import Dict, Any, Optional, List
from ..models.brief import ProjectBrief, ArchitecturalParameters, SiteParameters, ProjectType, RoomRequirement as BriefRoomRequirement
from enum import Enum


class StylePreference(str, Enum):
    MODERN = "modern"
    MINIMALIST = "minimalist"
    TROPICAL = "tropical"
    TRADITIONAL = "traditional"
    INDUSTRIAL = "industrial"


class SpecificationConversionError(Exception):
    """Raised when specification conversion fails."""
    pass


class SpecificationConverter:
    """
    Converts structured ProjectSpecification to ProjectBrief.

    NO LLM involved - this is a direct field mapping operation.
    If required fields are missing, raises SpecificationConversionError.
    """

    def specification_to_brief(self, specification: Dict[str, Any]) -> ProjectBrief:
        """
        Convert structured specification to ProjectBrief.

        Args:
            specification: Structured specification from frontend containing:
                - project_name: str
                - style: str (modern|min minimalist|tropical|traditional|industrial)
                - location: Optional[Dict] with name, country, latitude, longitude
                - site: Dict with dimensions and setbacks
                - floors: List of floor specifications
                - rooms: List of room requirements
                - circulation: Dict with corridor/staircase widths
                - zoning: Dict with public/private/service room lists
                - constraints: Dict with positioning constraints

        Returns:
            ProjectBrief with all fields populated from specification

        Raises:
            SpecificationConversionError: If required fields are missing
        """
        if not specification:
            raise SpecificationConversionError("Specification cannot be empty")

        # Required fields - raise error if missing (no fallback)
        project_name = specification.get("project_name")
        if not project_name:
            raise SpecificationConversionError("Missing required field: project_name")

        style = specification.get("style")
        if not style:
            raise SpecificationConversionError("Missing required field: style")

        site = specification.get("site")
        if not site:
            raise SpecificationConversionError("Missing required field: site")

        floors = specification.get("floors")
        if not floors:
            raise SpecificationConversionError("Missing required field: floors")

        rooms = specification.get("rooms")
        if not rooms:
            raise SpecificationConversionError("Missing required field: rooms")

        # Convert style to StylePreference
        style_map = {
            "modern": StylePreference.MODERN,
            "minimalist": StylePreference.MINIMALIST,
            "tropical": StylePreference.TROPICAL,
            "traditional": StylePreference.TRADITIONAL,
            "industrial": StylePreference.INDUSTRIAL
        }

        style_lower = style.lower()
        if style_lower not in style_map:
            raise SpecificationConversionError(f"Invalid style: {style}. Valid styles: {list(style_map.keys())}")

        style_preference = style_map[style_lower]

        # Convert location
        location = specification["location"]
        desired_features = [f"{location['name']}, {location['country']}"]

        # Convert site parameters
        site_params = self._convert_site_params(site)

        # Convert room requirements
        room_requirements = self._convert_room_requirements(rooms)

        # Convert floor count
        floor_count = len(floors)

        # Extract circulation params (frontend always sends these values)
        circulation = specification["circulation"]
        corridor_width = circulation["corridor_width_m"]
        staircase_width = circulation["staircase_width_m"]

        # Extract constraints - convert dict to list of strings
        constraints_dict = specification.get("constraints", {})
        constraints_list: List[str] = []
        if constraints_dict:
            for key, value in constraints_dict.items():
                constraints_list.append(f"{key}: {value}")

        # Build architectural parameters
        arch_params = self._build_architectural_params(
            site_params, floor_count, room_requirements,
            corridor_width, staircase_width
        )

        return ProjectBrief(
            title=project_name,
            project_type=ProjectType.RESIDENTIAL,  # Default to residential
            style_preference=style_preference.value if isinstance(style_preference, StylePreference) else style_preference,
            desired_features=desired_features if desired_features else [],
            floor_count=floor_count,
            room_requirements=room_requirements,
            site_params=site_params,
            architectural_params=arch_params,
            constraints=constraints_list if constraints_list else []
        )

    def _convert_site_params(self, site: Dict[str, Any]) -> SiteParameters:
        """Convert site specification to SiteParameters."""
        # Required site fields - no fallback
        building_width = site.get("building_width_m")
        if building_width is None:
            raise SpecificationConversionError("Missing required site field: building_width_m")

        building_depth = site.get("building_depth_m")
        if building_depth is None:
            raise SpecificationConversionError("Missing required site field: building_depth_m")

        total_land_area = site.get("total_land_area_m2")
        if total_land_area is None:
            raise SpecificationConversionError("Missing required site field: total_land_area_m2")

        building_footprint = site.get("building_footprint_m2")
        if building_footprint is None:
            raise SpecificationConversionError("Missing required site field: building_footprint_m2")

        # Setbacks - require explicit values based on cardinal directions
        setback_north = site.get("setback_north_m")
        if setback_north is None:
            raise SpecificationConversionError("Missing required site field: setback_north_m")

        setback_south = site.get("setback_south_m")
        if setback_south is None:
            raise SpecificationConversionError("Missing required site field: setback_south_m")

        setback_east = site.get("setback_east_m")
        if setback_east is None:
            raise SpecificationConversionError("Missing required site field: setback_east_m")

        setback_west = site.get("setback_west_m")
        if setback_west is None:
            raise SpecificationConversionError("Missing required site field: setback_west_m")

        # Convert to SiteParameters format (which uses front/back/left/right)
        # Assuming north = back, south = front, east = right, west = left
        # But this depends on building orientation which we don't have yet
        # For now, use direct mapping
        return SiteParameters(
            plot_area=total_land_area,
            plot_width=building_width,
            plot_length=building_depth,
            setback_front=setback_south,  # South is typically front
            setback_back=setback_north,   # North is typically back
            setback_left=setback_west,    # West is typically left
            setback_right=setback_east    # East is typically right
        )

    def _convert_room_requirements(self, rooms: list) -> Dict[str, Any]:
        """Convert room list to room requirements dictionary."""
        requirements = {}

        for room in rooms:
            room_type = room.get("room_type")
            if not room_type:
                raise SpecificationConversionError("Room missing required field: room_type")

            count = room.get("count")
            if count is None:
                raise SpecificationConversionError(f"Room {room_type} missing required field: count")

            min_width = room.get("min_width_m")
            if min_width is None:
                raise SpecificationConversionError(f"Room {room_type} missing required field: min_width_m")

            min_length = room.get("min_length_m")
            if min_length is None:
                raise SpecificationConversionError(f"Room {room_type} missing required field: min_length_m")

            min_area = room.get("min_area_m2")
            if min_area is None:
                raise SpecificationConversionError(f"Room {room_type} missing required field: min_area_m2")

            preferred_floor = room["preferred_floor"]

            requirements[room_type] = {
                "count": count,
                "min_width_m": min_width,
                "min_length_m": min_length,
                "min_area_m2": min_area,
                "preferred_floor": preferred_floor,
                "adjacent_to": room.get("adjacent_to", []),
                "exterior_access": room.get("exterior_access", False),
                "private": room.get("private", False)
            }

        return requirements

    def _build_architectural_params(
        self,
        site_params: SiteParameters,
        floor_count: int,
        room_requirements: Dict[str, Any],
        corridor_width: float,
        staircase_width: float
    ) -> ArchitecturalParameters:
        """Build architectural parameters from converted data."""
        # Calculate building dimensions
        building_width = site_params.plot_width - site_params.setback_left - site_params.setback_right
        building_depth = site_params.plot_length - site_params.setback_front - site_params.setback_back

        # Calculate average room dimensions
        # room_requirements tidak mungkin empty karena sudah divalidasi sebelumnya
        avg_width = sum(r["min_width_m"] for r in room_requirements.values()) / len(room_requirements)
        avg_length = sum(r["min_length_m"] for r in room_requirements.values()) / len(room_requirements)

        return ArchitecturalParameters(
            room_width=avg_width,
            room_length=avg_length,
            corridor_width=corridor_width,
            staircase_width=staircase_width,
            floor_height_ground=3.5,
            floor_height_upper=3.2,
            floor_to_ceiling=3.0,
            slab_thickness=0.15,
            roof_thickness=0.15,
            roof_overhang=0.6,
            wall_thickness_exterior=0.3,
            wall_thickness_interior=0.2,
            foundation_type="shallow",
            structural_system="frame",
            building_width=building_width,
            building_depth=building_depth
        )

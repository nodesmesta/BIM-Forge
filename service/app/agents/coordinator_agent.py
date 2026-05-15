import json
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..models.task import Task, TaskStatus
from ..models.brief import ProjectBrief
from ..models.ifc_data import WallData, DoorData, WindowData, SpaceData, FloorData, BuildingData, SiteData, ArchitecturalDesignData, RoofData
from ..core.gemini_client import GeminiClient
from ..core.config import settings
from ..core.space_types import canonical_space_type_key
from .base import BaseAgent


def _coordinator_material_surface_bundle(raw: Any, label: str) -> Dict[str, Any]:
    base = {
        "name": "unspecified",
        "color": "neutral",
        "finish": "smooth",
        "thermal_conductivity": 1.4,
        "density": 1800.0,
        "specific_heat": 880.0,
        "fire_rating": "REI45",
        "stc": "STC40",
        "u_value": 2.0,
    }
    if isinstance(raw, dict) and "name" in raw and "thermal_conductivity" in raw:
        merged = dict(base)
        merged.update(raw)
        return merged
    if isinstance(raw, str) and raw.strip():
        merged = dict(base)
        merged["name"] = raw.strip()
        return merged
    raise ValueError(f"Invalid coordinator material for {label}: {raw!r}")


def _normalize_coordinator_materials(response: Dict[str, Any]) -> Dict[str, Any]:
    walls = response.get("walls") or {}
    return {
        **response,
        "walls": {
            "exterior": _coordinator_material_surface_bundle(walls.get("exterior"), "walls.exterior"),
            "interior": _coordinator_material_surface_bundle(walls.get("interior"), "walls.interior"),
        },
        "floors": _coordinator_material_surface_bundle(response.get("floors"), "floors"),
        "roof": _coordinator_material_surface_bundle(response.get("roof"), "roof"),
        "windows": _coordinator_material_surface_bundle(response.get("windows"), "windows"),
    }


class CoordinatorAgent(BaseAgent):

    def __init__(self):
        super().__init__("CoordinatorAgent")
        self.gemini_client = GeminiClient()

    async def generate_layout(
        self,
        task: Task,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.log("Generating layout...")
        task.status = TaskStatus.SPEC_GENERATING
        task.progress = 35

        specification = context["specification"]
        project_brief_dict = context["project_brief"]
        project_brief = ProjectBrief(**project_brief_dict)
        environment_context = context["environment_context"]

        site = specification["site"]
        rooms = specification["rooms"]
        circulation = specification.get("circulation")
        constraints = specification.get("constraints")
        zoning = specification.get("zoning")

        building_width = site["building_width_m"]
        building_depth = site["building_depth_m"]
        style = project_brief.style_preference

        corridor_width = circulation["corridor_width_m"]
        staircase_width = circulation["staircase_width_m"]

        arch_params = await self._generate_architectural_params(
            environment_context, style, building_width, building_depth,
            corridor_width, staircase_width
        )

        materials = await self._select_materials(environment_context, style)

        roof = await self._generate_roof(environment_context, style)

        layout_optimization = await self._optimize_layout(
            environment_context, [], building_width, building_depth,
            constraints, zoning
        )

        room_requirements = self._build_room_requirements_for_layout(
            rooms, circulation, arch_params
        )

        layout_spec = await self._generate_layout_with_llm(
            building_width, building_depth, room_requirements,
            layout_optimization, constraints, zoning,
            environment_context, style
        )

        # FIX: Generate floor data (including walls) SYNCHRONOUSLY before space agents run
        # This ensures space agents know the wall boundaries when specifying furniture placement
        self.log("Generating complete floor data with walls...")
        floors_data = self._generate_complete_floors_data(
            layout_spec, building_width, building_depth,
            arch_params, materials, layout_optimization, specification
        )

        # Create wall_bounds dict for each space to pass to space agents
        wall_bounds_by_space = self._create_wall_bounds_for_spaces(floors_data, layout_spec)

        context["layout_spec"] = layout_spec
        context["arch_params"] = arch_params
        context["materials"] = materials
        context["roof"] = roof
        context["layout_optimization"] = layout_optimization
        context["floors_data"] = floors_data  # Complete data with walls
        context["wall_bounds_by_space"] = wall_bounds_by_space  # Wall info for space agents

        task.progress = 50

        return layout_spec

    def _generate_complete_floors_data(
        self,
        layout_spec: Dict[str, Any],
        building_width: float,
        building_depth: float,
        arch_params: Dict[str, Any],
        materials: Dict[str, Any],
        layout_optimization: Dict[str, Any],
        specification: Dict[str, Any]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Generate complete floor data including all walls, doors, windows.
        This is called SYNCHRONOUSLY before space agents run.
        """
        # Group spaces by floor
        floors_dict = {}
        for space_key, layout_info in layout_spec.items():
            floor_num = layout_info["floor_number"]
            if floor_num not in floors_dict:
                floors_dict[floor_num] = []
            floors_dict[floor_num].append({
                "key": space_key,
                **layout_info
            })

        floors_data = {}
        for floor_num in sorted(floors_dict.keys()):
            spaces = floors_dict[floor_num]
            
            # Call _arrange_spaces_optimized to get walls, doors, windows
            arranged_spaces, floor_walls, floor_doors, floor_windows = self._arrange_spaces_optimized(
                [{"name": s["key"], "dimensions": {"width_m": s["width_m"], "length_m": s["length_m"]}, **s} for s in spaces],
                floor_num, building_width, building_depth,
                layout_optimization, arch_params, materials
            )

            # Calculate exterior bounds
            floor_height = arch_params["floor_height_ground"] if floor_num == 1 else arch_params["floor_height_upper"]

            floors_data[floor_num] = {
                "floor_number": floor_num,
                "height_m": floor_height,
                "spaces": arranged_spaces,
                "walls": floor_walls,
                "doors": floor_doors,
                "windows": floor_windows,
                "exterior_bounds": {
                    "width_m": building_width,
                    "depth_m": building_depth,
                    "origin_x": -building_width / 2,
                    "origin_y": -building_depth / 2
                }
            }

        return floors_data

    def _create_wall_bounds_for_spaces(
        self,
        floors_data: Dict[int, Dict[str, Any]],
        layout_spec: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create wall bounds dictionary for each space.
        This is passed to space agents so they can specify furniture placement relative to walls.
        """
        wall_bounds = {}

        for space_key, layout_info in layout_spec.items():
            floor_num = layout_info["floor_number"]
            center_x = layout_info["center_x"]
            center_y = layout_info["center_y"]
            width = layout_info["width_m"]
            length = layout_info["length_m"]

            # Calculate space boundaries
            x0 = center_x - width / 2  # left edge
            x1 = center_x + width / 2  # right edge
            y0 = center_y - length / 2  # back edge
            y1 = center_y + length / 2  # front edge

            wall_bounds[space_key] = {
                "floor_number": floor_num,
                "center_x": center_x,
                "center_y": center_y,
                "width": width,
                "length": length,
                # Absolute wall boundaries (for wall_anchor calculation)
                "bounds": {
                    "north": y1,  # y max
                    "south": y0,  # y min
                    "east": x1,    # x max
                    "west": x0,    # x min
                },
                # Relative positions (for placement_hint)
                "relative": {
                    "north_offset": 0.0,  # distance from north wall
                    "south_offset": 0.0,  # distance from south wall
                    "east_offset": 0.0,   # distance from east wall
                    "west_offset": 0.0,    # distance from west wall
                }
            }

        return wall_bounds

    async def merge_space_designs(
        self,
        task: Task,
        context: Dict[str, Any],
        space_designs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        task.status = TaskStatus.SPEC_GENERATING

        layout_spec = context["layout_spec"]
        arch_params = context["arch_params"]
        materials = context["materials"]
        roof = context["roof"]
        layout_optimization = context["layout_optimization"]
        specification = context["specification"]

        merged_spaces = []
        for space_design in space_designs:
            st = canonical_space_type_key(space_design["space_type"])
            iid = space_design["instance_id"]
            space_key = f"{st}_{iid}"
            layout_info = layout_spec[space_key]

            merged = {
                **space_design,
                "dimensions": {
                    "width_m": layout_info["width_m"],
                    "length_m": layout_info["length_m"],
                    "height_m": layout_info["height_m"]
                },
                "center_x": layout_info["center_x"],
                "center_y": layout_info["center_y"],
                "floor_number": layout_info["floor_number"]
            }

            merged_spaces.append(merged)

        floors_dict = self._group_spaces_by_floor(merged_spaces)
        num_floors = len(floors_dict)

        building_width = specification["site"]["building_width_m"]
        building_depth = specification["site"]["building_depth_m"]

        floors = []
        all_walls = []
        all_doors = []
        all_windows = []

        for floor_num in sorted(floors_dict.keys()):
            spaces = floors_dict[floor_num]

            arranged_spaces, floor_walls, floor_doors, floor_windows = self._arrange_spaces_optimized(
                spaces, floor_num, building_width, building_depth,
                layout_optimization, arch_params, materials
            )

            floor_height = arch_params["floor_height_ground"] if floor_num == 1 else arch_params["floor_height_upper"]

            floors.append(FloorData(
                floor_number=floor_num,
                name=f"{'Ground' if floor_num == 1 else f'Floor {floor_num}'} Floor",
                height_m=floor_height,
                spaces=arranged_spaces,
                walls=floor_walls,
                doors=floor_doors,
                windows=floor_windows,
                exterior_bounds={
                    "width_m": building_width,
                    "depth_m": building_depth,
                    "origin_x": -building_width / 2,
                    "origin_y": -building_depth / 2
                }
            ))

            all_walls.extend(floor_walls)
            all_doors.extend(floor_doors)
            all_windows.extend(floor_windows)

        if num_floors > 1:
            staircase = self._generate_staircase(num_floors, building_width, building_depth, arch_params)
            if staircase:
                # Convert staircase dict to SpaceData
                from ..models.ifc_data import SpaceData
                staircase_space = SpaceData(
                    name=staircase["name"],
                    room_type=staircase["room_type"],
                    center_x=staircase["center_x"],
                    center_y=staircase["center_y"],
                    width_m=staircase["width_m"],
                    length_m=staircase["length_m"],
                    ifc_class=staircase["ifc_class"],
                    area_sqm=staircase["area_sqm"],
                    zone="circulation",
                    window_placement=False
                )
                for i, floor in enumerate(floors[:-1]):
                    floor.spaces.append(staircase_space)

        # Generate exterior walls for each floor
        for i, floor in enumerate(floors):
            floor_num = i + 1
            exterior_walls = self._generate_exterior_walls(building_width, building_depth, arch_params, materials, floor_num)
            floor.walls.extend(exterior_walls)

        # DEBUG: Log generated data
        self.log(f"DEBUG: Generated {len(floors)} floors")
        for i, floor in enumerate(floors):
            self.log(f"DEBUG: Floor {i+1}: {floor.name}")
            self.log(f"DEBUG:   - Height: {floor.height_m}m")
            self.log(f"DEBUG:   - Walls: {len(floor.walls)}")
            self.log(f"DEBUG:   - Doors: {len(floor.doors)}")
            self.log(f"DEBUG:   - Windows: {len(floor.windows)}")
            self.log(f"DEBUG:   - Spaces: {len(floor.spaces)}")
            for j, wall in enumerate(floor.walls[:3]):  # Log first 3 walls
                self.log(f"DEBUG:   - Wall {j}: {wall.name} ({wall.wall_type}), "
                        f"start_z={wall.start_z}m, end_z={wall.end_z}m, "
                        f"height={wall.height_m}m")
            for j, door in enumerate(floor.doors[:2]):  # Log first 2 doors
                self.log(f"DEBUG:   - Door {j}: {door.name}, "
                        f"center_z={door.center_z}m, wall={door.wall_name}")


        site_params = context["ifc_site_parameters"]

        roof_data = roof if isinstance(roof, RoofData) else RoofData(**roof)

        site_data = SiteData(
            name=site_params["name"],
            total_area_sqm=specification["site"]["total_land_area_m2"],
            building_footprint_sqm=building_width * building_depth,
            setback_front=specification["site"]["setback_south_m"],
            setback_back=specification["site"]["setback_north_m"],
            setback_left=specification["site"]["setback_west_m"],
            setback_right=specification["site"]["setback_east_m"]
        )

        building_data = BuildingData(
            name="Main Building",
            width_m=building_width,
            depth_m=building_depth
        )

        design = ArchitecturalDesignData(
            site=site_data,
            building=building_data,
            floors=floors,
            roof=roof_data
        )

        context["architectural_design"] = design
        context["llm_design"] = design
        context["space_designs"] = merged_spaces

        task.status = TaskStatus.SPEC_COMPLETE
        task.progress = 60

        return context

    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("WARNING: execute() is deprecated. Use generate_layout() + merge_space_designs()")

        layout_spec = await self.generate_layout(task, context)
        context["layout_spec"] = layout_spec

        return context


    async def _generate_architectural_params(
        self,
        environment_context: Dict[str, Any],
        style: str,
        building_width: float,
        building_depth: float,
        corridor_width: Optional[float],
        staircase_width: Optional[float]
    ) -> Dict[str, Any]:
        self.log("Generating architectural params...")
        climate_zone = environment_context["climate_zone"]
        rainfall = environment_context["rainfall_mm"]
        temperature = environment_context["temperature"]["annual_avg"]
        hemisphere = environment_context["hemisphere"]

        corridor_instruction = f"{corridor_width}m (user specified - use this exact value)" if corridor_width is not None else "NOT specified - determine optimal width based on climate, style, and building dimensions"
        staircase_instruction = f"{staircase_width}m (user specified - use this exact value)" if staircase_width is not None else "NOT specified - determine optimal width based on climate, style, and building dimensions"

        prompt = f"""Design optimal architectural parameters for:
Climate zone: {climate_zone}
Annual rainfall: {rainfall}mm
Average temperature: {temperature}C
Hemisphere: {hemisphere}
Building style: {style}
Building dimensions: {building_width}m x {building_depth}m
Corridor width: {corridor_instruction}
Staircase width: {staircase_instruction}

Return ONLY JSON with this exact structure:
{{
  "floor_height_ground": number (3.0-4.5),
  "floor_height_upper": number (2.8-4.0),
  "floor_to_ceiling": number (2.6-3.5),
  "slab_thickness": number (0.12-0.25),
  "wall_thickness_exterior": number (0.20-0.40),
  "wall_thickness_interior": number (0.10-0.20),
  "roof_overhang": number (0.4-1.2),
  "roof_thickness": number (0.10-0.20),
  "foundation_type": "shallow" | "deep" | "pile" | "raft",
  "structural_system": "frame" | "load-bearing" | "shear-wall" | "moment-frame",
  "corridor_width": number,
  "staircase_width": number,
  "door_width_m": number (0.8-1.0),
  "door_height_m": number (2.0-2.2),
  "door_thickness_m": number (0.04-0.06),
  "window_width_m": number (1.2-2.0),
  "window_height_m": number (1.2-1.8),
  "window_thickness_m": number (0.08-0.12)
}}

Reasoning: Consider climate appropriateness, thermal mass needs, moisture protection, and structural requirements.
IMPORTANT: If user specified corridor_width or staircase_width, use those exact values. If NOT specified, determine optimal values based on building type, climate, and style.
IMPORTANT: door and window dimensions must be standard architectural sizes appropriate for the building type."""

        response = await self.gemini_client.generate_content(prompt)
        # response is already parsed JSON dictionary
        if corridor_width is not None:
            response["corridor_width"] = corridor_width
        if staircase_width is not None:
            response["staircase_width"] = staircase_width
        return response

    async def _select_materials(
        self,
        environment_context: Dict[str, Any],
        style: str
    ) -> Dict[str, Any]:
        self.log("Selecting materials...")
        climate_zone = environment_context["climate_zone"]
        rainfall = environment_context["rainfall_mm"]
        temperature = environment_context["temperature"]["annual_avg"]
        humidity = environment_context["humidity"]
        recommendations = environment_context["recommendations"]

        prompt = f"""Select optimal building materials for:
Climate: {climate_zone}
Annual rainfall: {rainfall}mm
Average temperature: {temperature}C
Humidity: {humidity}%
Style: {style}
Climate recommendations: {recommendations}

Return ONLY JSON with this exact structure:
{{
  "walls": {{
    "exterior": "material name",
    "interior": "material name"
  }},
  "floors": "material name",
  "roof": "material name",
  "windows": "material name",
  "foundation": "material name",
  "reasoning": "explanation of material choices based on climate and style"
}}"""

        response = await self.gemini_client.generate_content(prompt)
        response_content = response  # Already parsed JSON
        return _normalize_coordinator_materials(response_content)

    async def _generate_roof(
        self,
        environment_context: Dict[str, Any],
        style: str
    ) -> RoofData:
        self.log("Generating roof...")
        climate_zone = environment_context["climate_zone"]
        rainfall = environment_context["rainfall_mm"]
        solar = environment_context["solar"]
        wind = environment_context["prevailing_wind"]

        prompt = f"""Design roof specifications for:
Climate: {climate_zone}
Annual rainfall: {rainfall}mm
Style: {style}
Solar exposure: {solar}
Prevailing wind: {wind}

Return ONLY JSON with this exact structure:
{{
  "type": "gable" | "flat" | "hipped" | "shed" | "gambrel",
  "slope_deg": number (5-45),
  "overhang_m": number (0.3-1.2),
  "thickness_m": number (0.10-0.25),
  "material": "material name",
  "insulation_thickness_m": number (0.05-0.20),
  "ventilation": "ridge" | "soffit" | "gable" | "combined",
  "reasoning": "explanation of roof design choices"
}}"""

        response = await self.gemini_client.generate_content(prompt)
        response_content = response  # Already parsed JSON
        response_content['name'] = 'Generated_Roof'
        return RoofData(**response_content)


    async def _optimize_layout(
        self,
        environment_context: Dict[str, Any],
        space_designs: List[Dict],
        building_width: float,
        building_depth: float,
        constraints: Dict[str, Any],
        zoning: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.log("Optimizing layout...")
        climate_zone = environment_context["climate_zone"]
        sun_orientation = environment_context["sun_orientation"]
        recommendations = environment_context["recommendations"]

        adjacency_requirements = []
        for space in space_designs:
            if "adjacent_to" in space and space["adjacent_to"]:
                adjacency_requirements.append({
                    "space": space["name"],
                    "adjacent_to": space["adjacent_to"]
                })

        prompt = f"""Optimize building layout for:
Climate: {climate_zone}
Sun orientation: {sun_orientation}
Climate recommendations: {recommendations}
Building dimensions: {building_width}m x {building_depth}m
Spaces: {len(space_designs)} rooms

Adjacency requirements: {adjacency_requirements}
Constraints: {constraints}
Zoning preferences: {zoning}

Return ONLY JSON with this exact structure:
{{
  "strategy": "cross-ventilation" | "thermal-zoning" | "solar-optimized" | "compact",
  "primary_orientation": "north" | "south" | "east" | "west",
  "public_zone_position": "front" | "rear" | "side",
  "private_zone_position": "front" | "rear" | "side",
  "service_zone_position": "front" | "rear" | "side",
  "corridor_layout": "single" | "double" | "courtyard",
  "ventilation_strategy": "cross" | "stack" | "night-flushing",
  "solar_control": "overhangs" | "louvers" | "trees" | "combined",
  "reasoning": "explanation of layout strategy"
}}"""

        response = await self.gemini_client.generate_content(prompt)
        response_content = response  # Already parsed JSON
        return response

    def _arrange_spaces_optimized(
        self,
        spaces: List[Dict],
        floor_num: int,
        building_width: float,
        building_depth: float,
        layout_optimization: Dict[str, Any],
        arch_params: Dict[str, Any],
        materials: Dict[str, Any]
    ) -> Tuple[List[SpaceData], List[WallData], List[DoorData], List[WindowData]]:
        arranged_spaces = []
        doors = []
        windows = []

        layout = self._solve_constraints_optimized(spaces, building_width, building_depth, layout_optimization)

        strategy = layout_optimization["strategy"]
        primary_orientation = layout_optimization["primary_orientation"]

        door_width = arch_params["door_width_m"]
        door_height = arch_params["door_height_m"]
        door_thickness = arch_params["door_thickness_m"]

        window_width = arch_params["window_width_m"]
        window_height = arch_params["window_height_m"]
        window_thickness = arch_params["window_thickness_m"]

        interior_wall_material = materials["walls"]["interior"]
        floor_z_start = (floor_num - 1) * arch_params["floor_height_ground"]
        floor_z_end = floor_z_start + arch_params["floor_to_ceiling"]
        wall_thickness_int = arch_params["wall_thickness_interior"]

        half_w = building_width / 2
        half_d = building_depth / 2
        tolerance = 0.05

        space_bounds = {}
        for space in spaces:
            space_name = space["name"]
            position = layout[space_name]
            center_x = position["center_x"]
            center_y = position["center_y"]
            space_dims = space["dimensions"]
            sw = space_dims["width_m"]
            sd = space_dims["length_m"]

            has_exterior_windows = self._determine_window_placement(
                space, position, strategy, primary_orientation, building_width, building_depth
            )

            # Calculate space boundaries FIRST (needed for wall_bounds)
            x0 = center_x - sw / 2
            x1 = center_x + sw / 2
            y0 = center_y - sd / 2
            y1 = center_y + sd / 2

                        # Preserve interior data from space agent (includes furniture with wall_anchor)
            interior_data = space.get("interior")
            exterior_data = space.get("exterior")
            mep_data = space.get("mep")
            materials_data = space.get("materials")

            arranged_spaces.append(SpaceData(
                name=space_name,
                room_type=space.get("space_type", "room"),
                ifc_class="IfcSpace",
                center_x=center_x,
                center_y=center_y,
                width_m=sw,
                length_m=sd,
                area_sqm=sw * sd,
                zone=self._classify_space_zone(space, strategy),
                window_placement=has_exterior_windows,
                # Preserve interior design data (furniture with wall_anchor)
                interior=interior_data,
                exterior=exterior_data,
                mep=mep_data,
                materials=materials_data,
                # Include wall bounds for furniture placement
                wall_bounds={
                    "floor_number": floor_num,
                    "center_x": center_x,
                    "center_y": center_y,
                    "width": sw,
                    "length": sd,
                    "bounds": {
                        "north": y1,
                        "south": y0,
                        "east": x1,
                        "west": x0,
                    }
                }
            ))

            space_bounds[space_name] = (x0, y0, x1, y1)

        raw_segments = []
        for name, (x0, y0, x1, y1) in space_bounds.items():
            raw_segments.append((name, "south", x0, y0, x1, y0))
            raw_segments.append((name, "north", x0, y1, x1, y1))
            raw_segments.append((name, "west",  x0, y0, x0, y1))
            raw_segments.append((name, "east",  x1, y0, x1, y1))

        def on_exterior(sx, sy, ex, ey):
            if abs(sx - ex) < tolerance:
                return abs(sx - (-half_w)) < tolerance or abs(sx - half_w) < tolerance
            else:
                return abs(sy - (-half_d)) < tolerance or abs(sy - half_d) < tolerance

        def segments_equal(s1, s2):
            # Handle both (owners, sx, sy, ex, ey) - 5 values and (owners, side, sx, sy, ex, ey) - 6 values
            if len(s1) == 5:
                _, s1_sx, s1_sy, s1_ex, s1_ey = s1
            else:
                _, _, s1_sx, s1_sy, s1_ex, s1_ey = s1
            
            if len(s2) == 5:
                _, s2_sx, s2_sy, s2_ex, s2_ey = s2
            else:
                _, _, s2_sx, s2_sy, s2_ex, s2_ey = s2
            
            return (
                (abs(s1_sx - s2_sx) < tolerance and abs(s1_sy - s2_sy) < tolerance and
                 abs(s1_ex - s2_ex) < tolerance and abs(s1_ey - s2_ey) < tolerance) or
                (abs(s1_sx - s2_ex) < tolerance and abs(s1_sy - s2_ey) < tolerance and
                 abs(s1_ex - s2_sx) < tolerance and abs(s1_ey - s2_sy) < tolerance)
            )

        interior_segments = []
        for seg in raw_segments:
            if not on_exterior(seg[2], seg[3], seg[4], seg[5]):
                interior_segments.append(seg)

        unique_segments = []
        used = [False] * len(interior_segments)
        for i, seg_i in enumerate(interior_segments):
            if used[i]:
                continue
            owners = [seg_i[0]]
            for j in range(i + 1, len(interior_segments)):
                if used[j]:
                    continue
                if segments_equal(seg_i, interior_segments[j]):
                    owners.append(interior_segments[j][0])
                    used[j] = True
            used[i] = True
            unique_segments.append((owners, seg_i[2], seg_i[3], seg_i[4], seg_i[5]))

        walls = []
        for owners, sx, sy, ex, ey in unique_segments:
            owner_names = "_".join(sorted(set(owners)))
            walls.append(WallData(
                name=f"Wall_{owner_names}",
                wall_type="interior",
                start_x=sx,
                start_y=sy,
                start_z=floor_z_start,
                end_x=ex,
                end_y=ey,
                end_z=floor_z_end,
                thickness_m=wall_thickness_int,
                height_m=arch_params["floor_to_ceiling"],
                material=interior_wall_material
            ))

        if floor_num == 1:
            door_center_z = arch_params["floor_to_ceiling"] / 2
        else:
            door_center_z = arch_params["floor_height_ground"] * (floor_num - 1) + (arch_params["floor_to_ceiling"] / 2)

        # =========================================================================
        # SMART DOOR PLACEMENT - Pintu di dinding yang menghubungkan 2 ruang
        # =========================================================================
        
        # Build adjacency map: which spaces share walls
        shared_walls = {}  # (space1, space2) -> wall_segment (sx, sy, ex, ey)
        for i, (owners_i, sx, sy, ex, ey) in enumerate(unique_segments):
            if len(owners_i) >= 2:  # Wall shared by multiple spaces
                for j in range(i + 1, len(unique_segments)):
                    owners_j = unique_segments[j][0]
                    if segments_equal((owners_i, sx, sy, ex, ey), (owners_j, unique_segments[j][1], unique_segments[j][2], unique_segments[j][3], unique_segments[j][4])):
                        # Found shared wall
                        for space_a in owners_i:
                            for space_b in owners_j:
                                key = tuple(sorted([space_a, space_b]))
                                shared_walls[key] = (sx, sy, ex, ey)

        # Track which spaces have doors
        spaces_with_doors = set()
        
        # Create doors for interior walls (connecting 2+ spaces)
        # Each unique_segment with multiple owners is a shared wall
        for owners, sx, sy, ex, ey in unique_segments:
            if len(owners) >= 2:
                # This wall is shared by multiple spaces
                space_a = owners[0]
                space_b = owners[1] if len(owners) > 1 else owners[0]
                
                spaces_with_doors.add(space_a)
                spaces_with_doors.add(space_b)
                
                # Determine wall orientation and side
                is_vertical = abs(ex - sx) < tolerance
                if is_vertical:
                    wall_orientation = "vertical"
                    wall_side = "west" if sx < 0 else "east"
                    center_x = sx
                    center_y = (sy + ey) / 2
                    rotation_deg = 90  # Pintu menghadap ke arah Y
                else:
                    wall_orientation = "horizontal"
                    wall_side = "south" if sy < 0 else "north"
                    center_x = (sx + ex) / 2
                    center_y = sy
                    rotation_deg = 0  # Pintu menghadap ke arah X
                
                wall_name = f"Wall_{space_a}_{space_b}"
                
                doors.append(DoorData(
                    name=f"Door_{space_a}_{space_b}",
                    width_m=door_width,
                    height_m=door_height,
                    thickness_m=door_thickness,
                    center_x=center_x,
                    center_y=center_y,
                    center_z=door_center_z,
                    rotation_deg=rotation_deg,
                    wall_name=wall_name,
                    swing_direction="double-swing",
                    connects_spaces=[space_a, space_b],
                    wall_segment=(sx, sy, ex, ey),
                    wall_side=wall_side,
                    wall_orientation=wall_orientation,
                    is_entrance=False
                ))

        # Create entrance door on ground floor (connects outside to inside)
        if floor_num == 1:
            # Find the best exterior wall for entrance
            # Prioritize south wall (front of building) or the wall with largest public space
            entrance_x = 0
            entrance_y = -half_d  # South wall
            entrance_rotation = 0  # Opens outward
            entrance_wall_name = "Wall_Exterior_South"
            entrance_segment = (-2, -half_d, 2, -half_d)
            entrance_side = "south"
            entrance_orientation = "horizontal"
            
            # Check if living_room or main public space exists
            for space in spaces:
                space_name = space["name"]
                if space.get("space_type") in ["living_room", "dining_room", "kitchen"]:
                    pos = layout.get(space_name)
                    if pos:
                        # Place entrance aligned with public space
                        entrance_x = pos["center_x"]
                        entrance_segment = (entrance_x - 1, -half_d, entrance_x + 1, -half_d)
                        break
            
            doors.append(DoorData(
                name="Door_Main_Entrance",
                width_m=door_width * 1.2,  # Entrance door slightly wider
                height_m=door_height,
                thickness_m=door_thickness,
                center_x=entrance_x,
                center_y=entrance_y,
                center_z=door_center_z,
                rotation_deg=entrance_rotation,
                wall_name=entrance_wall_name,
                swing_direction="single-swing-out",
                connects_spaces=None,  # Entrance connects outside to inside
                wall_segment=entrance_segment,
                wall_side=entrance_side,
                wall_orientation=entrance_orientation,
                is_entrance=True
            ))

        # =========================================================================
        # SMART WINDOW PLACEMENT - Jendela di dinding exterior
        # =========================================================================
        
        # Exterior wall segments
        exterior_segments = []
        for seg in raw_segments:
            space_name, side, sx, sy, ex, ey = seg
            if on_exterior(sx, sy, ex, ey):
                is_vertical = abs(ex - sx) < tolerance
                orientation = "vertical" if is_vertical else "horizontal"
                exterior_segments.append((space_name, side, sx, sy, ex, ey, orientation))

        # Place windows on exterior walls
        for space in spaces:
            space_name = space["name"]
            position = layout[space_name]
            center_x = position["center_x"]
            center_y = position["center_y"]
            space_dims = space["dimensions"]
            sw = space_dims["width_m"]
            sd = space_dims["length_m"]
            
            has_exterior_windows = self._determine_window_placement(
                space, position, strategy, primary_orientation, building_width, building_depth
            )
            
            if not has_exterior_windows:
                continue
            
            # Find exterior walls for this space
            x0 = center_x - sw / 2
            x1 = center_x + sw / 2
            y0 = center_y - sd / 2
            y1 = center_y + sd / 2
            
            # Check each exterior wall of this space
            for ext_space, side, sx, sy, ex, ey, orientation in exterior_segments:
                if ext_space != space_name:
                    continue
                    
                # Calculate window position (center of wall segment)
                if orientation == "horizontal":
                    win_center_x = (sx + ex) / 2
                    win_center_y = sy if sy < 0 else sy  # South or North
                    rotation_deg = 0 if side == "south" else 180
                    wall_side = side
                else:
                    win_center_x = sx
                    win_center_y = (sy + ey) / 2
                    rotation_deg = 90 if side == "west" else 270
                    wall_side = side
                
                if floor_num == 1:
                    window_sill_height = arch_params["floor_to_ceiling"] * 0.4
                else:
                    window_sill_height = arch_params["floor_height_ground"] * (floor_num - 1) + (arch_params["floor_to_ceiling"] * 0.4)
                
                # Limit window width to wall segment length
                wall_length = abs(ex - sx) if orientation == "horizontal" else abs(ey - sy)
                actual_window_width = min(window_width, wall_length - 0.4)  # 0.2m margin each side
                if actual_window_width < 0.6:  # Minimum window width
                    continue
                
                windows.append(WindowData(
                    name=f"Window_{space_name}_{side}",
                    width_m=actual_window_width,
                    height_m=window_height,
                    thickness_m=window_thickness,
                    center_x=win_center_x,
                    center_y=win_center_y,
                    sill_height_m=window_sill_height,
                    rotation_deg=rotation_deg,
                    wall_name=f"Wall_Exterior_{wall_side}",
                    window_type="double-glazed",
                    wall_segment=(sx, sy, ex, ey),
                    wall_side=wall_side,
                    wall_orientation=orientation
                ))

        return arranged_spaces, walls, doors, windows

    def _determine_window_placement(
        self,
        space: Dict,
        position: Dict,
        strategy: str,
        primary_orientation: str,
        building_width: float,
        building_depth: float
    ) -> bool:
        room_type = space.get("space_type", "room")
        center_x = position["center_x"]
        center_y = position["center_y"]
        half_w = building_width / 2
        half_d = building_depth / 2
        # Increased tolerance for exterior detection (1.5m margin)
        tolerance = 1.5

        # Check if this space has any exterior walls
        sw = space["dimensions"]["width_m"]
        sd = space["dimensions"]["length_m"]
        x0 = center_x - sw / 2
        x1 = center_x + sw / 2
        y0 = center_y - sd / 2
        y1 = center_y + sd / 2

        # A space has exterior walls if any of its edges are within the exterior zone
        has_exterior = (
            x0 <= -half_w + tolerance or  # Left edge within tolerance of building left
            x1 >= half_w - tolerance or   # Right edge within tolerance of building right
            y0 <= -half_d + tolerance or   # Bottom edge within tolerance of building bottom
            y1 >= half_d - tolerance       # Top edge within tolerance of building top
        )

        if not has_exterior:
            return False

        if room_type in ["bedroom", "living_room", "dining_room"]:
            return True

        if strategy == "cross-ventilation":
            return room_type not in ["bathroom", "storage"]
        elif strategy == "solar-optimized":
            return room_type in ["living_room", "dining_room", "office"]
        else:
            return room_type not in ["bathroom", "storage", "laundry"]

    def _classify_space_zone(self, space: Dict, strategy: str) -> str:
        room_type = space.get("space_type", "room")

        public_rooms = ["living_room", "dining_room", "kitchen", "guest_room"]
        service_rooms = ["bathroom", "laundry", "storage", "garage"]

        if room_type in public_rooms:
            return "public"
        elif room_type in service_rooms:
            return "service"
        else:
            return "private"

    def _solve_constraints_optimized(
        self,
        spaces: List[Dict],
        building_width: float,
        building_depth: float,
        layout_optimization: Dict[str, Any]
    ) -> Dict[str, Dict[str, float]]:
        margin = settings.margin_default

        sorted_spaces = sorted(
            spaces,
            key=lambda s: s["dimensions"]["width_m"] * s["dimensions"]["length_m"],
            reverse=True
        )

        layout = {}
        occupied = []

        x_min = -building_width / 2 + margin
        x_max = building_width / 2 - margin
        y_min = -building_depth / 2 + margin
        y_max = building_depth / 2 - margin

        for space in sorted_spaces:
            name = space["name"]
            width = space["dimensions"]["width_m"]
            depth = space["dimensions"]["length_m"]

            placed = False
            best_x, best_y = 0.0, 0.0

            for row_y in [y_min + depth/2, 0.0, y_max - depth/2]:
                if placed:
                    break
                x_cursor = x_min + width / 2
                while x_cursor + width / 2 <= x_max:
                    test_x = x_cursor
                    test_y = row_y

                    if abs(test_y) + depth / 2 <= y_max - margin:
                        overlaps = False
                        for ox, oy, ow, od in occupied:
                            if not self._no_overlap(test_x, test_y, width, depth, ox, oy, ow, od):
                                overlaps = True
                                break

                        if not overlaps:
                            best_x, best_y = test_x, test_y
                            placed = True
                            break

                    x_cursor += 0.5

            if not placed:
                best_x = x_min + width / 2
                best_y = 0.0
                for ox, oy, ow, od in occupied:
                    if not self._no_overlap(best_x, best_y, width, depth, ox, oy, ow, od):
                        best_y = oy + od / 2 + depth / 2 + 0.2

            layout[name] = {
                "center_x": best_x,
                "center_y": best_y
            }
            occupied.append((best_x, best_y, width, depth))

        return layout

    def _simple_layout(
        self,
        spaces: List[Dict],
        building_width: float,
        building_depth: float
    ) -> Dict[str, Dict[str, float]]:
        layout = {}
        margin = settings.margin_default

        public_spaces = []
        private_spaces = []
        service_spaces = []

        for space in spaces:
            room_type = space.get("space_type", "")
            if room_type in ["living_room", "dining_room", "kitchen"]:
                public_spaces.append(space)
            elif room_type in ["bathroom", "laundry", "storage", "garage"]:
                service_spaces.append(space)
            else:
                private_spaces.append(space)

        all_zones = [
            ("public", public_spaces, -building_depth/2 + margin, building_depth/2 - margin),
            ("private", private_spaces, -building_depth/2 + margin, building_depth/2 - margin),
            ("service", service_spaces, -building_depth/2 + margin, building_depth/2 - margin),
        ]

        current_y = -building_depth/2 + margin + 1.0

        for zone_name, zone_spaces, y_min, y_max in all_zones:
            if not zone_spaces:
                continue

            max_depth_in_zone = max(
                (s["dimensions"]["length_m"] for s in zone_spaces),
                default=3.0
            )

            x_offset = -building_width/2 + margin
            row_y = current_y + max_depth_in_zone / 2

            if row_y + max_depth_in_zone / 2 > building_depth/2 - margin:
                row_y = building_depth/2 - margin - max_depth_in_zone / 2

            for space in zone_spaces:
                name = space["name"]
                width = space["dimensions"]["width_m"]
                depth = space["dimensions"]["length_m"]

                if x_offset + width > building_width/2 - margin:
                    x_offset = -building_width/2 + margin
                    current_y += max_depth_in_zone + 0.5
                    row_y = current_y + depth / 2

                layout[name] = {
                    "center_x": x_offset + width / 2,
                    "center_y": row_y
                }
                x_offset += width + 0.5

            current_y += max_depth_in_zone + 1.0

        return layout

    def _no_overlap(
        self,
        x1: float, y1: float, w1: float, d1: float,
        x2: float, y2: float, w2: float, d2: float
    ) -> bool:
        left1, right1 = x1 - w1/2, x1 + w1/2
        bottom1, top1 = y1 - d1/2, y1 + d1/2

        left2, right2 = x2 - w2/2, x2 + w2/2
        bottom2, top2 = y2 - d2/2, y2 + d2/2

        return not (left1 < right2 and right1 > left2 and bottom1 < top2 and top1 > bottom2)

    def _group_spaces_by_floor(self, space_designs: List[Dict]) -> Dict[int, List[Dict]]:
        floors_dict = {}

        for space in space_designs:
            floor_num = space["floor_number"]
            if floor_num not in floors_dict:
                floors_dict[floor_num] = []
            floors_dict[floor_num].append(space)

        return floors_dict

    def _generate_exterior_walls(
        self,
        building_width: float,
        building_depth: float,
        arch_params: Dict[str, Any],
        materials: Dict[str, Any],
        floor_num: int = 1
    ) -> List[WallData]:
        wall_thickness = arch_params["wall_thickness_exterior"]
        floor_height = arch_params["floor_to_ceiling"]
        material = materials["walls"]["exterior"]

        # Calculate z offset based on floor number
        if floor_num == 1:
            z = 0
        else:
            # For floor 2+, start_z = height of previous floors
            z = arch_params["floor_height_ground"] * (floor_num - 1)

        return [
            WallData(
                name=f"Wall_Front_Floor{floor_num}",
                wall_type="exterior",
                start_x=-building_width/2,
                start_y=building_depth/2,
                start_z=z,
                end_x=building_width/2,
                end_y=building_depth/2,
                end_z=z + floor_height,
                thickness_m=wall_thickness,
                height_m=floor_height,
                material=material
            ),
            WallData(
                name=f"Wall_Back_Floor{floor_num}",
                wall_type="exterior",
                start_x=-building_width/2,
                start_y=-building_depth/2,
                start_z=z,
                end_x=building_width/2,
                end_y=-building_depth/2,
                end_z=z + floor_height,
                thickness_m=wall_thickness,
                height_m=floor_height,
                material=material
            ),
            WallData(
                name=f"Wall_Left_Floor{floor_num}",
                wall_type="exterior",
                start_x=-building_width/2,
                start_y=-building_depth/2,
                start_z=z,
                end_x=-building_width/2,
                end_y=building_depth/2,
                end_z=z + floor_height,
                thickness_m=wall_thickness,
                height_m=floor_height,
                material=material
            ),
            WallData(
                name=f"Wall_Right_Floor{floor_num}",
                wall_type="exterior",
                start_x=building_width/2,
                start_y=-building_depth/2,
                start_z=z,
                end_x=building_width/2,
                end_y=building_depth/2,
                end_z=z + floor_height,
                thickness_m=wall_thickness,
                height_m=floor_height,
                material=material
            )
        ]

    def _generate_staircase(
        self,
        num_floors: int,
        building_width: float,
        building_depth: float,
        arch_params: Dict[str, Any]
    ) -> Optional[Dict]:
        if num_floors <= 1:
            return None

        staircase_width = arch_params["staircase_width"]
        floor_height = arch_params["floor_to_ceiling"]

        riser_height = settings.riser_height
        riser_count = int(floor_height / riser_height)
        tread_depth = settings.tread_depth

        return {
            "name": "Staircase",
            "room_type": "staircase",
            "ifc_class": "IfcSpace",
            "center_x": building_width/2 - staircase_width/2 - 0.5,
            "center_y": -building_depth/2 + staircase_width/2 + 0.5,
            "width_m": staircase_width,
            "length_m": staircase_width * 1.25,
            "height_m": floor_height,
            "area_sqm": staircase_width * staircase_width * 1.25,
            "stair_details": {
                "present": True,
                "direction": "straight",
                "width_m": staircase_width - 0.2,
                "riser_count": riser_count,
                "tread_depth_m": tread_depth,
                "handrail": "both sides"
            }
        }

    def _build_room_requirements_for_layout(
        self,
        rooms: List[Dict],
        circulation: Dict,
        arch_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        room_requirements = []

        for room in rooms:
            room_type = canonical_space_type_key(room["room_type"])
            count = room["count"]

            for i in range(count):
                room_requirements.append({
                    "space_type": room_type,
                    "instance_id": i,
                    "min_width_m": room["min_width_m"],
                    "min_length_m": room["min_length_m"],
                    "min_area_m2": room["min_area_m2"],
                    "preferred_floor": room["preferred_floor"],
                    "adjacent_to": room["adjacent_to"],
                    "exterior_access": room["exterior_access"],
                    "private": room["private"],
                    "width_m": room["min_width_m"],
                    "length_m": room["min_length_m"]
                })

        return room_requirements

    async def _generate_layout_with_llm(
        self,
        building_width: float,
        building_depth: float,
        room_requirements: List[Dict[str, Any]],
        layout_optimization: Dict[str, Any],
        constraints: Dict,
        zoning: Dict,
        environment_context: Dict[str, Any],
        style: str
    ) -> Dict[str, Any]:
        self.log("Generating layout with LLM...")
        strategy = layout_optimization["strategy"]
        primary_orientation = layout_optimization["primary_orientation"]
        climate_zone = environment_context["climate_zone"]
        sun_orientation = environment_context["sun_orientation"]

        rooms_json = []
        required_keys = []
        for req in room_requirements:
            key = f"{req['space_type']}_{req['instance_id']}"
            required_keys.append(key)
            rooms_json.append({
                "layout_key": key,
                "space_type": req["space_type"],
                "instance_id": req["instance_id"],
                "min_width_m": req["min_width_m"],
                "min_length_m": req["min_length_m"],
                "preferred_floor": req["preferred_floor"],
                "adjacent_to": req["adjacent_to"],
                "exterior_access": req["exterior_access"]
            })

        prompt = f"""You are an expert architect designing a {style} building layout for {climate_zone} climate.
Sun orientation: {sun_orientation}, Layout strategy: {strategy}, Primary orientation: {primary_orientation}.

BUILDING: {building_width}m wide x {building_depth}m deep
STYLE: {style}
CLIMATE: {climate_zone}

ROOMS TO PLACE (use layout_key as the key in layout_spec):
{json.dumps(rooms_json, indent=2)}

REQUIRED KEYS in layout_spec: {json.dumps(required_keys)}

ZONING RULES:
- Public zones (living_room, dining_room, kitchen) should be on lower floors near the front (south).
- Private zones (bedroom, master_bedroom) should be on upper floors or rear (north).
- Service zones (bathroom) should be grouped near private zones.
- Rooms with exterior_access=true must touch the building perimeter.
- Respect adjacency preferences where possible.

LAYOUT RULES:
- Place rooms in a realistic 2D grid within the building bounds.
- Building origin is at (0,0). Bounds: x=[-{building_width/2}, {building_width/2}], y=[-{building_depth/2}, {building_depth/2}].
- Leave at least 1.0m corridor space between room clusters.
- No two rooms may overlap.
- Each room must use at least its min_width_m and min_length_m.

Return ONLY JSON with this exact structure:
{{
    "layout_spec": {{
        "living_room_0": {{
            "center_x": -2.0,
            "center_y": 3.0,
            "width_m": 5.0,
            "length_m": 4.5,
            "height_m": 3.0,
            "floor_number": 1
        }}
    }}
}}

CRITICAL: Every layout_key from ROOMS TO PLACE MUST appear as a key in layout_spec.
The REQUIRED KEYS are: {json.dumps(required_keys)}. Do not skip any.
"""

        response = await self.gemini_client.generate_content(prompt)
        layout_spec = response["layout_spec"]

        validated_spec = {}
        missing_rooms = []
        for req in room_requirements:
            key = f"{req['space_type']}_{req['instance_id']}"
            if key not in layout_spec:
                missing_rooms.append(key)
                continue
            spec = layout_spec[key]
            spec["width_m"] = max(spec["width_m"], req["min_width_m"])
            spec["length_m"] = max(spec["length_m"], req["min_length_m"])
            spec["floor_number"] = spec["floor_number"]
            validated_spec[key] = spec

        if missing_rooms:
            raise ValueError(
                f"LLM layout_spec missing {len(missing_rooms)} rooms: {missing_rooms}. "
                f"LLM returned keys: {list(layout_spec.keys())}"
            )

        return validated_spec

    async def get_workflow_status(self, task: Task) -> Dict[str, Any]:
        return {
            "task_id": task.id,
            "status": task.status.value,
            "progress": task.progress,
            "completed_agents": [],
            "failed_agents": [],
            "revision_number": task.revision_number,
        }

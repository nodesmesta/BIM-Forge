import ifcopenshell
import math
import random
import string
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from ..models.task import Task, TaskStatus
from ..core.config import settings
from .base import BaseAgent
from ..models.ifc_data import (
    WallData,
    DoorData,
    WindowData,
    SpaceData,
    RoofData,
    FloorData,
    BuildingData,
    ArchitecturalDesignData
)


def _material_dict_from_agent(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        t = raw.strip()
        return {"floor": t, "walls": t}
    raise TypeError(f"space materials must be dict or str, got {type(raw).__name__}")


def create_guid() -> str:
    chars = string.ascii_letters + string.digits + "_$"
    return "".join(random.choice(chars) for _ in range(22))


def rel_defines_by_properties(file, element, property_set) -> None:
    file.createIfcRelDefinesByProperties(
        GlobalId=create_guid(),
        OwnerHistory=None,
        Name=None,
        Description=None,
        RelatedObjects=[element],
        RelatingPropertyDefinition=property_set,
    )


def create_material_properties(file, element, material_name, color, finish, thermal_conductivity=None, density=None, specific_heat=None):
    material = file.createIfcMaterial(material_name)

    material_layer = file.createIfcMaterialLayer(material, 0.0, None)
    material_layer_set = file.createIfcMaterialLayerSet([material_layer], f"{material_name}_Assembly")
    material_layer_set_usage = file.createIfcMaterialLayerSetUsage(material_layer_set, "AXIS2", "POSITIVE", 0.0)

    properties = []
    properties.append(file.createIfcPropertySingleValue("Color", "Color", file.createIfcLabel(color), None))
    properties.append(file.createIfcPropertySingleValue("Finish", "Surface Finish", file.createIfcLabel(finish), None))

    if thermal_conductivity:
        properties.append(file.createIfcPropertySingleValue("ThermalConductivity", "Thermal Conductivity",
                                                          file.createIfcReal(thermal_conductivity), None))
    if density:
        properties.append(file.createIfcPropertySingleValue("Density", "Density",
                                                          file.createIfcReal(density), None))
    if specific_heat:
        properties.append(file.createIfcPropertySingleValue("SpecificHeat", "Specific Heat Capacity",
                                                          file.createIfcReal(specific_heat), None))

    material_property_set = file.createIfcPropertySet(
        GlobalId=create_guid(),
        Name=f"{material_name}_Properties",
        HasProperties=properties
    )

    file.createIfcRelAssociatesMaterial(
        GlobalId=create_guid(),
        OwnerHistory=None,
        Name=None,
        Description=None,
        RelatedObjects=[element],
        RelatingMaterial=material_layer_set_usage,
    )
    rel_defines_by_properties(file, element, material_property_set)

    return material

def create_ifc_file_instance(schema: str) -> ifcopenshell.file:
    return ifcopenshell.file(schema=schema)

def create_project_and_context(file: ifcopenshell.file, project_name: str) -> Tuple[Any, Any, Any]:
    context = file.createIfcGeometricRepresentationContext(
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=settings.ifc_precision,
        WorldCoordinateSystem=create_default_axis2_placement_3d(file)
    )
    metre = file.createIfcSIUnit(UnitType="LENGTHUNIT", Name="METRE")
    area = file.createIfcSIUnit(UnitType="AREAUNIT", Name="SQUARE_METRE")
    volume = file.createIfcSIUnit(UnitType="VOLUMEUNIT", Name="CUBIC_METRE")
    unit_assignment = file.createIfcUnitAssignment([metre, area, volume])

    project = file.createIfcProject(
        GlobalId=create_guid(),
        OwnerHistory=None,
        Name=project_name,
        RepresentationContexts=[context],
        UnitsInContext=unit_assignment
    )

    project_placement = create_default_local_placement(file)

    return project, context, project_placement

def create_site(file: ifcopenshell.file, name: str, placement: Any, elevation: float, coords: Optional[Tuple[float, float]] = None) -> Any:
    site = file.createIfcSite(
        GlobalId=create_guid(),
        OwnerHistory=None,
        Name=name,
        ObjectPlacement=placement,
        RefElevation=elevation
    )
    if coords:
        lat, lng = coords
        lat_abs = abs(lat)
        lng_abs = abs(lng)

        lat_deg = int(lat_abs)
        lat_min = int((lat_abs - lat_deg) * 60)
        lat_sec = int(((lat_abs - lat_deg - lat_min/60) * 3600))

        lng_deg = int(lng_abs)
        lng_min = int((lng_abs - lng_deg) * 60)
        lng_sec = int(((lng_abs - lng_deg - lng_min/60) * 3600))

        site.RefLatitude = [lat_deg, lat_min, lat_sec]
        site.RefLongitude = [lng_deg, lng_min, lng_sec]
    return site

def create_building(file: ifcopenshell.file, building_data: BuildingData, project_placement: Any) -> Tuple[Any, Any]:
    building_placement = file.createIfcLocalPlacement(
        PlacementRelTo=project_placement,
        RelativePlacement=create_default_axis2_placement_3d(file)
    )
    building = file.createIfcBuilding(
        GlobalId=create_guid(),
        OwnerHistory=None,
        Name=building_data.name,
        ObjectPlacement=building_placement
    )
    return building, building_placement

def create_floor(file: ifcopenshell.file, geom_context: Any, floor_data: FloorData, building_placement: Any, space_designs: List[Dict], arch_params: Dict[str, Any], coordinator_materials: Dict[str, Any]) -> Tuple[Any, List[Any]]:
    floor_z = (floor_data.floor_number - 1) * floor_data.height_m
    storey_placement = file.createIfcLocalPlacement(
        PlacementRelTo=building_placement,
        RelativePlacement=create_default_axis2_placement_3d(file, location_z=floor_z)
    )
    storey = file.createIfcBuildingStorey(
        GlobalId=create_guid(),
        OwnerHistory=None,
        Name=floor_data.name,
        ObjectPlacement=storey_placement,
        Elevation=floor_z
    )

    elements = []
    slab_thickness = arch_params["slab_thickness"]
    floor_slab = create_detailed_slab(
        file, geom_context, f"Floor_Slab_{floor_data.floor_number}", "FLOOR",
        floor_data.exterior_bounds['width_m'], floor_data.exterior_bounds['depth_m'],
        slab_thickness, floor_z, building_placement, coordinator_materials
    )
    elements.append(floor_slab)

    wall_thickness_exterior = arch_params["wall_thickness_exterior"]
    wall_thickness_interior = arch_params["wall_thickness_interior"]

    for wall_data in floor_data.walls:
        thickness = wall_thickness_exterior if wall_data.wall_type == "exterior" else wall_thickness_interior
        elements.append(create_wall(file, geom_context, wall_data, building_placement, thickness))

    for door_data in floor_data.doors:
        door, opening = create_door_with_void(file, geom_context, door_data, arch_params, building_placement, coordinator_materials)
        elements.append(door)
        elements.append(opening)

    for window_data in floor_data.windows:
        window, opening = create_window_with_void(file, geom_context, window_data, arch_params, building_placement, coordinator_materials)
        elements.append(window)
        elements.append(opening)

    for space_data in floor_data.spaces:
        space = create_space(file, geom_context, space_data, floor_data.height_m, building_placement)
        elements.append(space)

        matched_design = _match_space_design(space_data, space_designs)
        if matched_design:
            furniture_elements = create_furniture(
                file, geom_context, matched_design["interior"],
                floor_z, building_placement, space_data, matched_design["materials"]
            )
            elements.extend(furniture_elements)

            exterior_elements = create_exterior_elements(
                file, geom_context, matched_design["exterior"],
                floor_z, building_placement, space_data,
                matched_design["materials"]
            )
            elements.extend(exterior_elements)

    mep_elements = create_mep_systems(
        file, geom_context, floor_data, floor_z, building_placement, space_designs
    )
    elements.extend(mep_elements)

    ceiling_elements = create_ceiling_with_lighting(
        file, geom_context, floor_data, floor_z + floor_data.height_m, building_placement, space_designs, coordinator_materials
    )
    elements.extend(ceiling_elements)

    return storey, elements


def _match_space_design(space_data: SpaceData, space_designs: List[Dict]) -> Optional[Dict]:
    space_type_lower = space_data.room_type.lower()
    for design in space_designs:
        design_type = design["space_type"].lower()
        if design_type and design_type in space_type_lower:
            return design
    return None

def create_detailed_slab(file, geom_context, name, predefined_type, width, depth, thickness, z_offset, placement_context, coordinator_materials: Dict[str, Any]) -> Any:
    slab_placement = file.createIfcLocalPlacement(
        PlacementRelTo=placement_context,
        RelativePlacement=create_default_axis2_placement_3d(file, location_z=z_offset)
    )

    slab = file.createIfcSlab(
        GlobalId=create_guid(),
        Name=name,
        PredefinedType=predefined_type,
        ObjectPlacement=slab_placement
    )

    base_profile = create_rectangle_profile_def(file, "Slab_Structure", width, depth)
    base_extrusion = create_extruded_area_solid(file, base_profile, thickness * 0.7)

    finish_profile = create_rectangle_profile_def(file, "Slab_Finish", width, depth)
    finish_extrusion = create_extruded_area_solid(
        file, finish_profile, thickness * 0.1,
        location_z=thickness * 0.7
    )

    if predefined_type == "FLOOR":
        insulation_profile = create_rectangle_profile_def(file, "Slab_Insulation", width, depth)
        insulation_extrusion = create_extruded_area_solid(
            file, insulation_profile, thickness * 0.2,
            location_z=thickness * 0.5
        )
        items = [base_extrusion, insulation_extrusion, finish_extrusion]
    else:
        items = [base_extrusion, finish_extrusion]

    representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=items
    )
    slab.Representation = representation

    material_props = coordinator_materials["floors"]
    create_material_properties(
        file, slab, material_props["name"],
        material_props["color"], material_props["finish"],
        material_props["thermal_conductivity"],
        material_props["density"],
        material_props["specific_heat"]
    )

    slab_property_set = file.createIfcPropertySet(
        GlobalId=create_guid(),
        Name="SlabProperties",
        HasProperties=[
            file.createIfcPropertySingleValue("LoadCapacity", "Load capacity (kN/m²)",
                                            file.createIfcReal(5.0), None),
            file.createIfcPropertySingleValue("FireRating", "Fire resistance rating",
                                            file.createIfcLabel(material_props["fire_rating"]), None),
            file.createIfcPropertySingleValue("SoundTransmissionClass", "Sound transmission class",
                                            file.createIfcLabel(material_props["stc"]), None)
        ]
    )
    rel_defines_by_properties(file, slab, slab_property_set)

    return slab

def create_mep_systems(file, geom_context, floor_data, floor_z, placement_context, space_designs) -> List[Any]:
    mep_elements = []

    for space_data in floor_data.spaces:
        matched_design = _match_space_design(space_data, space_designs)
        if not matched_design:
            continue

        room_cx = space_data.center_x
        room_cy = space_data.center_y
        room_w = space_data.width_m
        room_d = space_data.length_m

        mep_raw = matched_design.get("mep")
        mep_data = mep_raw if isinstance(mep_raw, dict) else {}
        electrical_list = mep_data.get("electrical", [])
        if isinstance(electrical_list, str):
            electrical_list = [electrical_list]
        elif not isinstance(electrical_list, list):
            electrical_list = []
        total_elec = len(electrical_list)

        for elec_idx, elec in enumerate(electrical_list):
            cols = min(total_elec, 3)
            row = elec_idx // cols
            col = elec_idx % cols
            spacing_x = room_w / (cols + 1)
            spacing_y = room_d / (max((total_elec + cols - 1) // cols, 1) + 1)
            elec_x = room_cx - room_w / 2 + spacing_x * (col + 1)
            elec_y = room_cy - room_d / 2 + spacing_y * (row + 1)

            outlet = file.createIfcElectricAppliance(
                GlobalId=create_guid(),
                Name=f"Power_Outlet_{space_data.name}_{elec_idx}",
                ObjectPlacement=file.createIfcLocalPlacement(
                    PlacementRelTo=placement_context,
                    RelativePlacement=create_default_axis2_placement_3d(
                        file, location_x=elec_x, location_y=elec_y, location_z=floor_z + 0.3
                    )
                ),
                PredefinedType="NOTDEFINED"
            )
            mep_elements.append(outlet)

        plumbing_list = mep_data.get("plumbing", [])
        if isinstance(plumbing_list, str):
            plumbing_list = [plumbing_list]
        elif not isinstance(plumbing_list, list):
            plumbing_list = []
        total_plumbing = len(plumbing_list)

        for plumbing_idx, plumbing in enumerate(plumbing_list):
            cols = min(total_plumbing, 2)
            row = plumbing_idx // cols
            col = plumbing_idx % cols
            spacing_x = room_w / (cols + 1)
            pl_x = room_cx - room_w / 2 + spacing_x * (col + 1)
            pl_y = room_cy - room_d / 2 + room_d * 0.3

            fixture = file.createIfcSanitaryTerminal(
                GlobalId=create_guid(),
                Name=f"{plumbing}_{space_data.name}",
                ObjectPlacement=file.createIfcLocalPlacement(
                    PlacementRelTo=placement_context,
                    RelativePlacement=create_default_axis2_placement_3d(
                        file, location_x=pl_x, location_y=pl_y, location_z=floor_z
                    )
                ),
                PredefinedType="NOTDEFINED" if "toilet" in str(plumbing).lower() else "SINK"
            )
            mep_elements.append(fixture)

    return mep_elements

def create_ceiling_with_lighting(file, geom_context, floor_data, ceiling_z, placement_context, space_designs, coordinator_materials: Dict[str, Any]) -> List[Any]:
    ceiling_elements = []

    ceiling_slab = file.createIfcSlab(
        GlobalId=create_guid(),
        Name=f"Ceiling_{floor_data.name}",
        ObjectPlacement=file.createIfcLocalPlacement(
            PlacementRelTo=placement_context,
            RelativePlacement=create_default_axis2_placement_3d(file, location_z=ceiling_z - 0.1)
        ),
        PredefinedType="NOTDEFINED"
    )

    ceiling_profile = create_rectangle_profile_def(
        file, "Ceiling",
        floor_data.exterior_bounds['width_m'],
        floor_data.exterior_bounds['depth_m']
    )
    ceiling_extrusion = create_extruded_area_solid(file, ceiling_profile, 0.1)

    ceiling_representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[ceiling_extrusion]
    )
    ceiling_slab.Representation = ceiling_representation

    ceiling_material_props = coordinator_materials["roof"]
    create_material_properties(
        file, ceiling_slab, ceiling_material_props["name"],
        ceiling_material_props["color"], ceiling_material_props["finish"],
        ceiling_material_props["thermal_conductivity"],
        ceiling_material_props["density"],
        ceiling_material_props["specific_heat"]
    )

    ceiling_elements.append(ceiling_slab)

    for space_data in floor_data.spaces:
        matched_design = _match_space_design(space_data, space_designs)
        if not matched_design:
            continue

        room_cx = space_data.center_x
        room_cy = space_data.center_y
        room_w = space_data.width_m
        room_d = space_data.length_m

        interior = matched_design.get("interior")
        if not isinstance(interior, dict):
            continue

        lighting_list = interior.get("lighting", [])
        if isinstance(lighting_list, str):
            lighting_list = [lighting_list]
        elif not isinstance(lighting_list, list):
            lighting_list = []
        total_lights = len(lighting_list)

        for light_idx, light in enumerate(lighting_list):
            if not isinstance(light, dict):
                continue
            if light.get("position_x") is not None and light.get("position_y") is not None:
                light_x = light["position_x"]
                light_y = light["position_y"]
            else:
                cols = min(total_lights, 2)
                row = light_idx // cols
                col = light_idx % cols
                spacing_x = room_w / (cols + 1)
                spacing_y = room_d / (max((total_lights + cols - 1) // cols, 1) + 1)
                light_x = room_cx - room_w / 2 + spacing_x * (col + 1)
                light_y = room_cy - room_d / 2 + spacing_y * (row + 1)

            light_fixture = file.createIfcLightFixture(
                GlobalId=create_guid(),
                Name=f"{light.get('type', 'light')}_Light_{space_data.name}",
                ObjectPlacement=file.createIfcLocalPlacement(
                    PlacementRelTo=placement_context,
                    RelativePlacement=create_default_axis2_placement_3d(
                        file,
                        location_x=light_x,
                        location_y=light_y,
                        location_z=ceiling_z - 0.2
                    )
                ),
                PredefinedType="NOTDEFINED",
            )
            ceiling_elements.append(light_fixture)

    return ceiling_elements

def create_wall(file, geom_context, wall_data: WallData, placement_context, thickness_m: float) -> Any:
    mid_x = (wall_data.start_x + wall_data.end_x) / 2
    mid_y = (wall_data.start_y + wall_data.end_y) / 2
    mid_z = (wall_data.start_z + wall_data.end_z) / 2
    dx = wall_data.end_x - wall_data.start_x
    dy = wall_data.end_y - wall_data.start_y
    length = math.sqrt(dx*dx + dy*dy)
    height = wall_data.end_z - wall_data.start_z

    ref_direction = file.createIfcDirection([dx, dy, 0.0]) if (dx != 0 or dy != 0) else file.createIfcDirection([1.0, 0.0, 0.0])

    wall_rel_placement = file.createIfcAxis2Placement3D(
        Location=file.createIfcCartesianPoint((mid_x, mid_y, mid_z)),
        Axis=file.createIfcDirection([0.0, 0.0, 1.0]),
        RefDirection=ref_direction
    )
    wall_placement = file.createIfcLocalPlacement(PlacementRelTo=placement_context, RelativePlacement=wall_rel_placement)

    wall = file.createIfcWall(GlobalId=create_guid(), Name=wall_data.name, ObjectPlacement=wall_placement)

    base_profile = create_rectangle_profile_def(file, "Wall_Base", length, thickness_m)
    base_extrusion = create_extruded_area_solid(file, base_profile, height, location_z=-height/2)

    trim_profile = create_molding_profile_def(file, "Wall_Top_Trim", length, 0.15)
    trim_extrusion = create_extruded_area_solid(file, trim_profile, 0.1, location_z=height/2 - 0.05)

    baseboard_profile = create_molding_profile_def(file, "Wall_Baseboard", length, 0.1)
    baseboard_extrusion = create_extruded_area_solid(file, baseboard_profile, 0.15, location_z=-height/2 + 0.075)

    representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body", RepresentationType="SweptSolid",
        Items=[base_extrusion, trim_extrusion, baseboard_extrusion]
    )
    wall.Representation = representation

    if hasattr(wall_data, 'material') and wall_data.material:
        material_props = wall_data.material
        create_material_properties(
            file, wall, material_props["name"],
            material_props["color"], material_props["finish"],
            material_props["thermal_conductivity"],
            material_props["density"],
            material_props["specific_heat"]
        )

        wall_property_set = file.createIfcPropertySet(
            GlobalId=create_guid(),
            Name="WallConstructionProperties",
            HasProperties=[
                file.createIfcPropertySingleValue("FireRating", "Fire resistance rating",
                                                file.createIfcLabel(material_props["fire_rating"]), None),
                file.createIfcPropertySingleValue("SoundTransmissionClass", "Sound transmission class",
                                                file.createIfcLabel(material_props["stc"]), None),
                file.createIfcPropertySingleValue("UValue", "Thermal transmittance",
                                                file.createIfcReal(material_props["u_value"]), None)
            ]
        )
        rel_defines_by_properties(file, wall, wall_property_set)

    return wall

def create_door_with_void(file, geom_context, door_data: DoorData, arch_params: Dict[str, Any], placement_context, coordinator_materials: Dict[str, Any]) -> Tuple[Any, Any]:
    """
    Create door with proper orientation based on wall_segment and rotation.
    
    Smart placement:
    - Respects door_data.rotation_deg for door swing direction
    - Respects door_data.wall_orientation (horizontal/vertical)
    - Respects door_data.is_entrance for main building entrance
    - Creates proper IfcOpeningElement for wall void
    """
    door_width = door_data.width_m if door_data.width_m else arch_params["door_width_m"]
    door_height = door_data.height_m if door_data.height_m else arch_params["door_height_m"]
    door_thickness = door_data.thickness_m if door_data.thickness_m else arch_params["door_thickness_m"]
    wall_thickness = arch_params["wall_thickness_interior"]

    # Determine extrusion direction based on rotation
    rotation_deg = door_data.rotation_deg if door_data.rotation_deg else 0
    
    # Calculate extrusion direction vector
    # rotation_deg 0 = Y+ direction (horizontal wall)
    # rotation_deg 90 = X+ direction (vertical wall)
    # rotation_deg 180 = Y- direction
    # rotation_deg 270 = X- direction
    import math
    angle_rad = math.radians(rotation_deg)
    extrude_x = math.sin(angle_rad)  # Y direction component
    extrude_y = math.cos(angle_rad)  # X direction component
    
    # Sill height from floor
    sill_height = door_data.center_z - door_height / 2

    # Create placement with proper orientation
    door_rel_placement = create_default_axis2_placement_3d(
        file, door_data.center_x, door_data.center_y, sill_height
    )
    door_placement = file.createIfcLocalPlacement(PlacementRelTo=placement_context, RelativePlacement=door_rel_placement)

    # Create IfcDoor with proper predefined type
    if door_data.is_entrance:
        door_predefined_type = "DOOR"
        door_name = f"MAIN_ENTRANCE ({door_data.name})"
    elif door_data.swing_direction == "double-swing":
        door_predefined_type = "DOOR"
        door_name = f"DOUBLE_SWING_{door_data.name}"
    elif door_data.swing_direction == "single-swing-out":
        door_predefined_type = "DOOR"
        door_name = f"SINGLE_OUT_{door_data.name}"
    else:
        door_predefined_type = "DOOR"
        door_name = door_data.name

    door = file.createIfcDoor(
        GlobalId=create_guid(),
        Name=door_name,
        ObjectPlacement=door_placement,
        PredefinedType=door_predefined_type,
        OverallHeight=door_height,
        OverallWidth=door_width
    )

    # Create door panel with proper orientation
    door_panel_profile = create_rectangle_profile_def(file, "DoorPanel", door_width - 0.1, door_height - 0.1)
    
    # Extrusion position: offset slightly from wall
    panel_offset_x = 0.05
    panel_offset_y = 0.05
    
    # Adjust position based on wall orientation
    if door_data.wall_orientation == "vertical":
        # Vertical wall: door extends in X direction
        door_panel_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=door_panel_profile,
            Position=create_default_axis2_placement_3d(
                file, 
                location_x=panel_offset_y,  # Offset perpendicular to wall
                location_y=panel_offset_x
            ),
            ExtrudedDirection=file.createIfcDirection([1.0, 0.0, 0.0]),  # X direction
            Depth=door_thickness * 0.8
        )
    else:
        # Horizontal wall: door extends in Y direction
        door_panel_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=door_panel_profile,
            Position=create_default_axis2_placement_3d(
                file,
                location_x=panel_offset_x,  # Offset perpendicular to wall
                location_y=panel_offset_y
            ),
            ExtrudedDirection=file.createIfcDirection([0.0, 1.0, 0.0]),  # Y direction
            Depth=door_thickness * 0.8
        )

    frame_thickness = 0.05
    frame_profile = create_rectangle_profile_def(file, "DoorFrame", door_width, door_height)
    
    # Frame extrusion direction matches panel
    if door_data.wall_orientation == "vertical":
        frame_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=frame_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([1.0, 0.0, 0.0]),  # X direction
            Depth=frame_thickness
        )
    else:
        frame_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=frame_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([0.0, 1.0, 0.0]),  # Y direction
            Depth=frame_thickness
        )

    door_representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[frame_extrusion, door_panel_extrusion]
    )
    door.Representation = door_representation

    # Material properties
    door_material_props = coordinator_materials["walls"]["interior"]
    create_material_properties(
        file, door, door_material_props["name"],
        door_material_props["color"], door_material_props["finish"],
        door_material_props["thermal_conductivity"],
        door_material_props["density"],
        door_material_props["specific_heat"]
    )

    # Property set with door-specific properties
    swing_type = door_data.swing_direction if door_data.swing_direction else "NOTDEFINED"
    door_property_set = file.createIfcPropertySet(
        GlobalId=create_guid(),
        Name="DoorProperties",
        HasProperties=[
            file.createIfcPropertySingleValue("FireRating", "Fire rating", file.createIfcLabel(door_material_props["fire_rating"]), None),
            file.createIfcPropertySingleValue("AcousticRating", "Acoustic rating", file.createIfcLabel(door_material_props["stc"]), None),
            file.createIfcPropertySingleValue("UValue", "Thermal transmittance", file.createIfcReal(door_material_props["u_value"]), None),
            file.createIfcPropertySingleValue("SwingType", "Door swing direction", file.createIfcLabel(swing_type), None),
            file.createIfcPropertySingleValue("IsEntrance", "Main building entrance", file.createIfcBoolean(door_data.is_entrance), None),
            file.createIfcPropertySingleValue("ConnectsSpaces", "Spaces connected by this door", 
                file.createIfcText(str(door_data.connects_spaces) if door_data.connects_spaces else "Outside"), None)
        ]
    )
    rel_defines_by_properties(file, door, door_property_set)

    # Create IfcOpeningElement for wall void
    opening_placement = file.createIfcLocalPlacement(PlacementRelTo=placement_context, RelativePlacement=door_rel_placement)
    opening = file.createIfcOpeningElement(
        GlobalId=create_guid(),
        Name=f"Opening_{door_data.name}",
        ObjectPlacement=opening_placement
    )

    opening_profile = create_rectangle_profile_def(file, "DoorOpening", door_width, door_height)
    
    # Opening extrusion direction matches door
    if door_data.wall_orientation == "vertical":
        opening_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=opening_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([1.0, 0.0, 0.0]),  # X direction
            Depth=wall_thickness * 1.5
        )
    else:
        opening_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=opening_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([0.0, 1.0, 0.0]),  # Y direction
            Depth=wall_thickness * 1.5
        )

    opening_representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[opening_extrusion]
    )
    opening.Representation = opening_representation

    # Connect door to opening
    file.createIfcRelFillsElement(
        GlobalId=create_guid(),
        RelatingOpeningElement=opening,
        RelatedBuildingElement=door
    )
    
    # Create IfcRelVoidsElement to properly void the wall
    # Note: The actual wall-void connection should be done during building structure creation
    # by mapping door_data.wall_segment to the corresponding wall
    
    return door, opening

def create_staircase(file, geom_context, floor_count: int, floor_height: float, building_width: float, building_depth: float, placement_context) -> List[Any]:
    """
    Create a proper staircase connecting multiple floors.
    
    Indonesian terminology:
    - Anak tangga = stair tread (the horizontal part you step on)
    - Injakan = tread depth
    - tinggi injakan = riser height
    - Bordes/landing = intermediate landing platform
    
    Returns list of all staircase elements for proper floor assignment.
    """
    elements = []
    
    # Staircase parameters (Indonesian standard)
    tread_depth = 0.28  # Dalam injakan (m)
    riser_height = 0.175  # Tinggi anak tangga (m) - standard residential
    stair_width = 1.0  # Lebar tangga (m)
    
    # Calculate number of steps per flight (max 12 steps per flight for comfort)
    steps_per_flight = 12
    total_riser_height = floor_height
    num_full_flights = int(total_riser_height / (riser_height * steps_per_flight))
    remaining_steps = int((total_riser_height % (riser_height * steps_per_flight)) / riser_height) if num_full_flights > 0 else int(total_riser_height / riser_height)
    
    # For simplicity, create a standard U-shaped or straight staircase
    # Position staircase in building corner
    stair_x = building_width / 2 - stair_width - 0.5
    stair_y = -building_depth / 2 + 0.5
    
    # Create main staircase structure
    stair_placement = file.createIfcLocalPlacement(
        PlacementRelTo=placement_context,
        RelativePlacement=create_default_axis2_placement_3d(file, location_x=stair_x, location_y=stair_y)
    )
    
    # Create IfcStair as container
    staircase = file.createIfcStair(
        GlobalId=create_guid(),
        Name="Tangga Utama",
        ObjectPlacement=stair_placement,
        PredefinedType="NOTDEFINED"
    )
    elements.append(staircase)
    
    # Calculate dimensions for multi-flight staircase
    landing_depth = 1.0  # Kedalaman bordes
    
    # For floor_count = 2:
    # - Flight 1: Ground to half height (with landing)
    # - Flight 2: Half height to full height
    
    flights_per_floor = 2  # U-shaped staircase
    total_flights = (floor_count - 1) * flights_per_floor
    
    # Create each flight
    current_z = 0.0
    flight_counter = 0
    
    for floor_idx in range(floor_count - 1):
        for flight_in_floor in range(flights_per_floor):
            # Determine flight direction (alternating for U-shape)
            if flight_in_floor % 2 == 0:
                # Going up
                direction = 1
                x_offset = 0
            else:
                # Going up (opposite direction after landing)
                direction = 1
                x_offset = stair_width + 0.1  # Gap for U-turn
            
            # Create stair flight
            flight_placement = file.createIfcLocalPlacement(
                PlacementRelTo=stair_placement,
                RelativePlacement=create_default_axis2_placement_3d(
                    file, 
                    location_x=x_offset, 
                    location_y=flight_in_floor * (landing_depth + 0.1)
                )
            )
            
            flight = file.createIfcStairFlight(
                GlobalId=create_guid(),
                Name=f"Bordes_{floor_idx + 1}_{flight_in_floor + 1}",
                ObjectPlacement=flight_placement,
                PredefinedType="STRAIGHT"
            )
            
            # Create tread (anak tangga) representation
            num_treads = steps_per_flight
            
            # Create composite profile for tread with riser
            tread_items = []
            
            # Tread (horizontal part) - anak tangga datar
            tread_profile = create_rectangle_profile_def(file, "Tread", stair_width, tread_depth)
            tread_extrusion = file.createIfcExtrudedAreaSolid(
                SweptArea=tread_profile,
                Position=create_default_axis2_placement_3d(file),
                ExtrudedDirection=file.createIfcDirection([0.0, 0.0, 1.0]),
                Depth=riser_height  # Tread thickness
            )
            
            # Riser (vertical part) - anak tangga tegak
            riser_profile = create_rectangle_profile_def(file, "Riser", stair_width, riser_height)
            riser_extrusion = file.createIfcExtrudedAreaSolid(
                SweptArea=riser_profile,
                Position=create_default_axis2_placement_3d(file, location_z=tread_depth),
                ExtrudedDirection=file.createIfcDirection([0.0, 0.0, 1.0]),
                Depth=0.02  # Riser thickness
            )
            
            # Create representation for flight
            flight_representation = file.createIfcShapeRepresentation(
                ContextOfItems=geom_context,
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=[tread_extrusion, riser_extrusion]
            )
            flight.Representation = flight_representation
            
            # Set NumberOfTreads and NumberOfRisers
            flight.NumberOfTreads = num_treads
            flight.NumberOfRisers = num_treads
            
            elements.append(flight)
            flight_counter += 1
    
    # Create landing (bordes) if multiple floors
    if floor_count > 1:
        landing_height = floor_height / 2
        
        # Main landing between floors
        landing_placement = file.createIfcLocalPlacement(
            PlacementRelTo=stair_placement,
            RelativePlacement=create_default_axis2_placement_3d(
                file,
                location_x=0,
                location_y=landing_depth + 0.1
            )
        )
        
        landing = file.createIfcSlab(
            GlobalId=create_guid(),
            Name="Bordes Tangga",
            ObjectPlacement=landing_placement,
            PredefinedType="LANDING"
        )
        
        landing_profile = create_rectangle_profile_def(file, "Landing", stair_width, landing_depth)
        landing_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=landing_profile,
            Position=create_default_axis2_placement_3d(file),
            ExtrudedDirection=file.createIfcDirection([0.0, 0.0, 1.0]),
            Depth=0.1  # Landing thickness
        )
        
        landing_representation = file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[landing_extrusion]
        )
        landing.Representation = landing_representation
        elements.append(landing)
    
    # Create handrails (pagar tangga) on both sides
    handrail_height = 0.9  # meters
    handrail_offset = 0.05  # offset from stair edge
    
    for side in ["left", "right"]:
        x_offset = 0 if side == "left" else stair_width + handrail_offset
        
        # Handrail balustrade
        handrail_placement = file.createIfcLocalPlacement(
            PlacementRelTo=stair_placement,
            RelativePlacement=create_default_axis2_placement_3d(
                file,
                location_x=x_offset,
                location_y=0
            )
        )
        
        handrail = file.createIfcRailing(
            GlobalId=create_guid(),
            Name=f"Pagar Tangga ({'Kiri' if side == 'left' else 'Kanan'})",
            ObjectPlacement=handrail_placement,
            PredefinedType="HANDRAIL"
        )
        
        # Create railing profile
        railing_profile = create_rectangle_profile_def(file, "Handrail", 0.05, 0.05)
        railing_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=railing_profile,
            Position=create_default_axis2_placement_3d(file, location_z=handrail_height - 0.05),
            ExtrudedDirection=file.createIfcDirection([0.0, 0.0, 1.0]),
            Depth=total_riser_height + 0.5
        )
        
        railing_representation = file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[railing_extrusion]
        )
        handrail.Representation = railing_representation
        elements.append(handrail)
    
    return elements


def create_window_with_void(file, geom_context, window_data: WindowData, arch_params: Dict[str, Any], placement_context, coordinator_materials: Dict[str, Any]) -> Tuple[Any, Any]:
    """
    Create window with proper orientation based on wall_segment and rotation.
    
    Smart placement:
    - Respects window_data.wall_orientation (horizontal/vertical)
    - Respects window_data.rotation_deg for proper extrusion direction
    - Respects window_data.wall_side for naming (north/south/east/west)
    - Creates proper IfcOpeningElement for wall void
    """
    window_width = window_data.width_m if window_data.width_m else arch_params["window_width_m"]
    window_height = window_data.height_m if window_data.height_m else arch_params["window_height_m"]
    window_thickness = window_data.thickness_m if window_data.thickness_m else arch_params["window_thickness_m"]
    wall_thickness = arch_params["wall_thickness_exterior"]
    
    # Determine extrusion direction based on wall orientation
    wall_orientation = window_data.wall_orientation if window_data.wall_orientation else "horizontal"

    # Create placement at sill height
    window_rel_placement = create_default_axis2_placement_3d(
        file, window_data.center_x, window_data.center_y, window_data.sill_height_m
    )
    window_placement = file.createIfcLocalPlacement(PlacementRelTo=placement_context, RelativePlacement=window_rel_placement)

    # Window type based on window_data
    window_type = window_data.window_type if window_data.window_type else "double-glazed"
    if window_type == "double-glazed":
        predefined_type = "DOUBLE_GLAZED"
    elif window_type == "single-glazed":
        predefined_type = "SINGLE_GLAZED"
    elif window_type == "triple-glazed":
        predefined_type = "TRIPLE_GLAZED"
    else:
        predefined_type = "WINDOW"

    window_name = f"{window_data.wall_side.upper()}_{window_data.name}" if window_data.wall_side else window_data.name

    window = file.createIfcWindow(
        GlobalId=create_guid(),
        Name=window_name,
        ObjectPlacement=window_placement,
        PredefinedType=predefined_type
    )

    # Create frame with orientation based on wall type
    frame_profile = create_rectangle_profile_def(file, "WindowFrame", window_width, window_height)
    
    if wall_orientation == "vertical":
        # Vertical wall (east/west): window extends in X direction
        frame_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=frame_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([1.0, 0.0, 0.0]),  # X direction
            Depth=0.08
        )
        glazing_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=create_rectangle_profile_def(file, "WindowGlazing", window_width - 0.1, window_height - 0.1),
            Position=create_default_axis2_placement_3d(file, location_x=0.05, location_y=0.05),
            ExtrudedDirection=file.createIfcDirection([1.0, 0.0, 0.0]),  # X direction
            Depth=0.01
        )
    else:
        # Horizontal wall (north/south): window extends in Y direction
        frame_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=frame_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([0.0, 1.0, 0.0]),  # Y direction
            Depth=0.08
        )
        glazing_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=create_rectangle_profile_def(file, "WindowGlazing", window_width - 0.1, window_height - 0.1),
            Position=create_default_axis2_placement_3d(file, location_x=0.05, location_y=0.05),
            ExtrudedDirection=file.createIfcDirection([0.0, 1.0, 0.0]),  # Y direction
            Depth=0.01
        )

    window_representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[frame_extrusion, glazing_extrusion]
    )
    window.Representation = window_representation

    window_material_props = coordinator_materials["windows"]
    create_material_properties(
        file, window, window_material_props["name"],
        window_material_props["color"], window_material_props["finish"],
        window_material_props["thermal_conductivity"],
        window_material_props["density"],
        window_material_props["specific_heat"]
    )

    # Window properties with orientation info
    window_property_set = file.createIfcPropertySet(
        GlobalId=create_guid(),
        Name="WindowProperties",
        HasProperties=[
            file.createIfcPropertySingleValue("UValue", "Thermal transmittance", file.createIfcReal(window_material_props["u_value"]), None),
            file.createIfcPropertySingleValue("SolarHeatGainCoeff", "Solar heat gain coefficient", file.createIfcReal(0.4), None),
            file.createIfcPropertySingleValue("VisibleTransmittance", "Visible transmittance", file.createIfcReal(0.7), None),
            file.createIfcPropertySingleValue("WallSide", "Orientation of wall", file.createIfcLabel(window_data.wall_side if window_data.wall_side else "unknown"), None),
            file.createIfcPropertySingleValue("WallOrientation", "Wall orientation", file.createIfcLabel(wall_orientation), None),
            file.createIfcPropertySingleValue("WindowType", "Window glazing type", file.createIfcLabel(window_type), None)
        ]
    )
    rel_defines_by_properties(file, window, window_property_set)

    # Create IfcOpeningElement for wall void
    opening_placement = file.createIfcLocalPlacement(PlacementRelTo=placement_context, RelativePlacement=window_rel_placement)
    opening = file.createIfcOpeningElement(
        GlobalId=create_guid(),
        Name=f"Opening_{window_name}",
        ObjectPlacement=opening_placement
    )

    opening_profile = create_rectangle_profile_def(file, "WindowOpening", window_width, window_height)
    
    # Opening extrusion direction matches window
    if wall_orientation == "vertical":
        opening_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=opening_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([1.0, 0.0, 0.0]),  # X direction
            Depth=wall_thickness * 1.5
        )
    else:
        opening_extrusion = file.createIfcExtrudedAreaSolid(
            SweptArea=opening_profile,
            Position=create_default_axis2_placement_3d(file, location_x=0, location_y=0),
            ExtrudedDirection=file.createIfcDirection([0.0, 1.0, 0.0]),  # Y direction
            Depth=wall_thickness * 1.5
        )

    opening_representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[opening_extrusion]
    )
    opening.Representation = opening_representation

    # Connect window to opening
    file.createIfcRelFillsElement(
        GlobalId=create_guid(),
        RelatingOpeningElement=opening,
        RelatedBuildingElement=window
    )
    
    return window, opening

def create_space(file, geom_context, space_data: SpaceData, height: float, placement_context) -> Any:
    space_rel_placement = create_default_axis2_placement_3d(
        file, space_data.center_x, space_data.center_y, 0.0
    )
    space_placement = file.createIfcLocalPlacement(PlacementRelTo=placement_context, RelativePlacement=space_rel_placement)

    space = file.createIfcSpace(
        GlobalId=create_guid(),
        Name=space_data.name,
        LongName=space_data.room_type,
        ObjectPlacement=space_placement
    )

    profile = create_rectangle_profile_def(file, "Space", space_data.width_m, space_data.length_m)
    extrusion = create_extruded_area_solid(file, profile, height)

    representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )

    space.Representation = representation
    return space

def create_roof_slab(file, geom_context, roof_data: RoofData, building_data: BuildingData, num_floors: int, floor_height: float, placement_context, coordinator_materials: Dict[str, Any]) -> Any:
    width = building_data.width_m + roof_data.overhang_m * 2
    depth = building_data.depth_m + roof_data.overhang_m * 2
    floor_z = num_floors * floor_height

    roof_placement = file.createIfcLocalPlacement(
        PlacementRelTo=placement_context,
        RelativePlacement=create_default_axis2_placement_3d(file, location_z=floor_z)
    )

    roof = file.createIfcSlab(
        GlobalId=create_guid(),
        Name=roof_data.name,
        ObjectPlacement=roof_placement,
        PredefinedType="ROOF"
    )

    profile = create_rectangle_profile_def(file, "Roof", width, depth)

    if roof_data.slope_deg > 5:
        slope_rad = math.radians(roof_data.slope_deg)
        height_diff = width * math.tan(slope_rad) / 2
        position = create_default_axis2_placement_3d(file, location_z=-height_diff/2)
    else:
        position = create_default_axis2_placement_3d(file)

    extrusion = file.createIfcExtrudedAreaSolid(
        SweptArea=profile,
        Position=position,
        ExtrudedDirection=file.createIfcDirection([0.0, 0.0, 1.0]),
        Depth=roof_data.thickness_m
    )

    representation = file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )

    roof.Representation = representation

    roof_material_props = coordinator_materials["roof"]
    create_material_properties(
        file, roof, roof_material_props["name"],
        roof_material_props["color"], roof_material_props["finish"],
        roof_material_props["thermal_conductivity"],
        roof_material_props["density"],
        roof_material_props["specific_heat"]
    )

    return roof


def create_default_axis2_placement_3d(file, location_x=0.0, location_y=0.0, location_z=0.0):
    return file.createIfcAxis2Placement3D(
        Location=file.createIfcCartesianPoint((float(location_x), float(location_y), float(location_z))),
        Axis=file.createIfcDirection([0.0, 0.0, 1.0]),
        RefDirection=file.createIfcDirection([1.0, 0.0, 0.0])
    )

def create_default_local_placement(file):
     return file.createIfcLocalPlacement(
            PlacementRelTo=None,
            RelativePlacement=create_default_axis2_placement_3d(file)
     )

def create_rectangle_profile_def(file, name, width, depth):
    return file.createIfcRectangleProfileDef(ProfileType="AREA", ProfileName=name, XDim=width, YDim=depth)

def create_molding_profile_def(file, name, width, height):
    points = [
        file.createIfcCartesianPoint((0.0, 0.0)),
        file.createIfcCartesianPoint((width, 0.0)),
        file.createIfcCartesianPoint((width, height * 0.3)),
        file.createIfcCartesianPoint((width * 0.8, height * 0.5)),
        file.createIfcCartesianPoint((width * 0.2, height)),
        file.createIfcCartesianPoint((0.0, height))
    ]
    return file.createIfcArbitraryClosedProfileDef(
        ProfileType="AREA",
        ProfileName=name,
        OuterCurve=file.createIfcPolyline(points)
    )

def create_extruded_area_solid(
    file, profile, depth, location_x=0.0, location_y=0.0, location_z=0.0
):
    return file.createIfcExtrudedAreaSolid(
        SweptArea=profile,
        Position=create_default_axis2_placement_3d(
            file, location_x=location_x, location_y=location_y, location_z=location_z
        ),
        ExtrudedDirection=file.createIfcDirection([0.0, 0.0, 1.0]),
        Depth=depth
    )

def _calculate_furniture_position_from_anchor(
    item: Dict,
    idx: int,
    total_items: int,
    room_cx: float,
    room_cy: float,
    room_w: float,
    room_d: float,
    north_y: float,
    south_y: float,
    east_x: float,
    west_x: float
) -> Tuple[float, float]:
    """
    Calculate furniture position based on wall_anchor.
    
    wall_anchor can be:
    - "north": against north wall (y = north_y - offset)
    - "south": against south wall (y = south_y + offset)
    - "east": against east wall (x = east_x - offset)
    - "west": against west wall (x = west_x + offset)
    - "center": in the center of the room
    """
    wall_anchor = item.get("wall_anchor", "center")
    placement_hint = item.get("placement_hint", "")
    item_width = item.get("width_m", 1.0)
    item_depth = item.get("depth_m", 1.0)
    
    # Default offset from wall (half of furniture depth)
    wall_offset = item_depth / 2 + 0.1  # 10cm gap from wall
    
    # Parse placement_hint for offset customization
    offset_from_hint = _parse_offset_from_hint(placement_hint, wall_offset)
    
    if wall_anchor == "north":
        # Against north wall (positive Y direction)
        pos_x = room_cx  # Default center
        pos_y = north_y - offset_from_hint
        # For items against north wall, we might want to center or spread them
        if "center" in placement_hint.lower():
            pos_x = room_cx
        elif "left" in placement_hint.lower():
            pos_x = west_x + item_width / 2 + 0.1
        elif "right" in placement_hint.lower():
            pos_x = east_x - item_width / 2 - 0.1
            
    elif wall_anchor == "south":
        # Against south wall (negative Y direction)
        pos_x = room_cx
        pos_y = south_y + offset_from_hint
        if "center" in placement_hint.lower():
            pos_x = room_cx
        elif "left" in placement_hint.lower():
            pos_x = west_x + item_width / 2 + 0.1
        elif "right" in placement_hint.lower():
            pos_x = east_x - item_width / 2 - 0.1
            
    elif wall_anchor == "east":
        # Against east wall (positive X direction)
        pos_x = east_x - offset_from_hint
        pos_y = room_cy
        if "center" in placement_hint.lower():
            pos_y = room_cy
        elif "front" in placement_hint.lower():
            pos_y = north_y - item_depth / 2 - 0.1
        elif "back" in placement_hint.lower():
            pos_y = south_y + item_depth / 2 + 0.1
            
    elif wall_anchor == "west":
        # Against west wall (negative X direction)
        pos_x = west_x + offset_from_hint
        pos_y = room_cy
        if "center" in placement_hint.lower():
            pos_y = room_cy
        elif "front" in placement_hint.lower():
            pos_y = north_y - item_depth / 2 - 0.1
        elif "back" in placement_hint.lower():
            pos_y = south_y + item_depth / 2 + 0.1
            
    else:  # "center" or unknown
        # Center placement with grid fallback
        cols = min(total_items, 3)
        row = idx // cols
        col = idx % cols
        spacing_x = room_w / (cols + 1)
        spacing_y = room_d / (max((total_items + cols - 1) // cols, 1) + 1)
        pos_x = room_cx - room_w / 2 + spacing_x * (col + 1)
        pos_y = room_cy - room_d / 2 + spacing_y * (row + 1)
    
    return pos_x, pos_y


def _parse_offset_from_hint(hint: str, default_offset: float) -> float:
    """Parse offset distance from placement hint."""
    if not hint:
        return default_offset
    
    hint_lower = hint.lower()
    
    # Look for distance patterns like "0.5m from wall" or "50cm from wall"
    import re
    # Match patterns like "0.5m", "50cm", "1 meter"
    meter_match = re.search(r'(\d+\.?\d*)\s*m', hint_lower)
    if meter_match:
        return float(meter_match.group(1))
    
    cm_match = re.search(r'(\d+\.?\d*)\s*cm', hint_lower)
    if cm_match:
        return float(cm_match.group(1)) / 100
    
    return default_offset


def create_furniture(file, geom_context, furniture_data, floor_z, placement_context, space_data, space_materials) -> List[Any]:
    furniture_elements = []

    if not isinstance(furniture_data, dict):
        return furniture_elements
    space_materials = _material_dict_from_agent(space_materials)

    room_cx = space_data.center_x
    room_cy = space_data.center_y
    room_w = space_data.width_m
    room_d = space_data.length_m

    # Get wall bounds if available (from wall_bounds in space_design)
    wall_bounds = getattr(space_data, 'wall_bounds', {}) or {}
    bounds = wall_bounds.get("bounds", {}) if wall_bounds else {}
    
    # Room boundary coordinates
    north_y = bounds.get("north", room_cy + room_d / 2)
    south_y = bounds.get("south", room_cy - room_d / 2)
    east_x = bounds.get("east", room_cx + room_w / 2)
    west_x = bounds.get("west", room_cx - room_w / 2)

    furniture_list = furniture_data.get("furniture", [])
    if not isinstance(furniture_list, list):
        return furniture_elements

    total_items = len(furniture_list)

    for idx, item in enumerate(furniture_list):
        if not isinstance(item, dict):
            continue
        required = ("type", "width_m", "depth_m", "height_m")
        if not all(k in item for k in required):
            continue
        display_name = str(item.get("name") or item["type"])
        
        # Calculate position based on wall_anchor
        pos_x, pos_y = _calculate_furniture_position_from_anchor(
            item, idx, total_items,
            room_cx, room_cy, room_w, room_d,
            north_y, south_y, east_x, west_x
        )

        furniture_placement = file.createIfcLocalPlacement(
            PlacementRelTo=placement_context,
            RelativePlacement=create_default_axis2_placement_3d(
                file,
                location_x=pos_x,
                location_y=pos_y,
                location_z=floor_z + item.get("position_z", 0.1)
            )
        )

        if item["type"] in ["bed", "wardrobe", "desk", "dresser"]:
            element = file.createIfcFurnishingElement(
                GlobalId=create_guid(),
                Name=f"{item['type'].title()}_{display_name}",
                ObjectPlacement=furniture_placement
            )
        else:
            element = file.createIfcBuildingElementProxy(
                GlobalId=create_guid(),
                Name=f"{item['type'].title()}_{display_name}",
                ObjectPlacement=furniture_placement
            )

        geometry = create_furniture_geometry(file, geom_context, item)
        element.Representation = geometry

        material_name = str(item.get("material", "unspecified"))
        color = str(item.get("color", "neutral"))
        finish = space_materials["floor"]
        create_material_properties(file, element, material_name, color, finish)

        furniture_property_set = file.createIfcPropertySet(
            GlobalId=create_guid(),
            Name="FurnitureProperties",
            HasProperties=[
                file.createIfcPropertySingleValue("Type", "Furniture Type", file.createIfcLabel(item["type"]), None),
                file.createIfcPropertySingleValue("Material", "Material", file.createIfcLabel(material_name), None),
                file.createIfcPropertySingleValue("Color", "Color", file.createIfcLabel(color), None),
                file.createIfcPropertySingleValue("Width", "Width (m)", file.createIfcReal(item["width_m"]), None),
                file.createIfcPropertySingleValue("Depth", "Depth (m)", file.createIfcReal(item["depth_m"]), None),
                file.createIfcPropertySingleValue("Height", "Height (m)", file.createIfcReal(item["height_m"]), None)
            ]
        )
        rel_defines_by_properties(file, element, furniture_property_set)

        furniture_elements.append(element)

    return furniture_elements

def create_furniture_geometry(file, geom_context, item):
    width = item["width_m"]
    depth = item["depth_m"]
    height = item["height_m"]
    furniture_type = item["type"]
    
    items = []
    
    if furniture_type == "bed":
        # Bed platform
        profile = create_rectangle_profile_def(file, "Bed_Base", width, depth)
        extrusion = create_extruded_area_solid(file, profile, height * 0.2)
        items.append(extrusion)
        
        # Headboard
        headboard_profile = create_rectangle_profile_def(file, "Bed_Headboard", width * 0.9, 0.05)
        headboard_extrusion = create_extruded_area_solid(
            file, headboard_profile, height * 0.6,
            location_z=height * 0.2 + 0.1
        )
        items.append(headboard_extrusion)
        
        # Footboard (smaller)
        footboard_profile = create_rectangle_profile_def(file, "Bed_Footboard", width * 0.9, 0.05)
        footboard_extrusion = create_extruded_area_solid(
            file, footboard_profile, height * 0.2,
            location_z=height * 0.2 + 0.1
        )
        items.append(footboard_extrusion)
    
    elif furniture_type == "wardrobe":
        # Main wardrobe body
        profile = create_rectangle_profile_def(file, "Wardrobe_Base", width, depth)
        extrusion = create_extruded_area_solid(file, profile, height)
        items.append(extrusion)
        
        # Doors (two doors)
        door_width = width * 0.45
        door_profile = create_rectangle_profile_def(file, "Wardrobe_Door", door_width, 0.02)
        # Left door
        door_extrusion1 = create_extruded_area_solid(
            file, door_profile, height * 0.9,
            location_x=-width/2 + door_width/2
        )
        items.append(door_extrusion1)
        # Right door
        door_extrusion2 = create_extruded_area_solid(
            file, door_profile, height * 0.9,
            location_x=width/2 - door_width/2
        )
        items.append(door_extrusion2)
        
        # Handle/knob (simple protrusion)
        handle_profile = create_rectangle_profile_def(file, "Wardrobe_Handle", 0.02, 0.02)
        handle_extrusion = create_extruded_area_solid(
            file, handle_profile, height * 0.1,
            location_x=width/2 - door_width/2 + 0.02,
            location_y=depth/2 - 0.02
        )
        items.append(handle_extrusion)
    
    elif furniture_type == "desk":
        # Desktop
        profile = create_rectangle_profile_def(file, "Desk_Top", width, depth)
        extrusion = create_extruded_area_solid(file, profile, height * 0.05, location_z=height * 0.7)
        items.append(extrusion)
        
        # Desk legs (four legs)
        leg_size = 0.06
        leg_profile = create_rectangle_profile_def(file, "Desk_Leg", leg_size, leg_size)
        leg_positions = [
            (-width/2 + leg_size, -depth/2 + leg_size),
            (width/2 - leg_size*2, -depth/2 + leg_size),
            (-width/2 + leg_size, depth/2 - leg_size*2),
            (width/2 - leg_size*2, depth/2 - leg_size*2)
        ]
        for leg_x, leg_y in leg_positions:
            leg_extrusion = create_extruded_area_solid(
                file, leg_profile, height * 0.7,
                location_x=leg_x, location_y=leg_y
            )
            items.append(leg_extrusion)
    
    elif furniture_type == "sofa":
        # Sofa base/seat
        profile = create_rectangle_profile_def(file, "Sofa_Seat", width, depth * 0.6)
        extrusion = create_extruded_area_solid(file, profile, height * 0.4, location_z=height * 0.3)
        items.append(extrusion)
        
        # Sofa back
        back_profile = create_rectangle_profile_def(file, "Sofa_Back", width, depth * 0.2)
        back_extrusion = create_extruded_area_solid(
            file, back_profile, height * 0.5,
            location_z=height * 0.5,
            location_y=-depth * 0.2
        )
        items.append(back_extrusion)
        
        # Sofa arms (optional - simplified)
        arm_width = width * 0.1
        arm_profile = create_rectangle_profile_def(file, "Sofa_Arm", arm_width, depth * 0.5)
        # Left arm
        arm_extrusion1 = create_extruded_area_solid(
            file, arm_profile, height * 0.35,
            location_x=-width/2 + arm_width/2,
            location_z=height * 0.3
        )
        items.append(arm_extrusion1)
        # Right arm
        arm_extrusion2 = create_extruded_area_solid(
            file, arm_profile, height * 0.35,
            location_x=width/2 - arm_width/2,
            location_z=height * 0.3
        )
        items.append(arm_extrusion2)
    
    elif furniture_type == "chair":
        # Chair seat
        profile = create_rectangle_profile_def(file, "Chair_Seat", width, depth)
        extrusion = create_extruded_area_solid(file, profile, height * 0.05, location_z=height * 0.6)
        items.append(extrusion)
        
        # Chair back
        back_profile = create_rectangle_profile_def(file, "Chair_Back", width, depth * 0.1)
        back_extrusion = create_extruded_area_solid(
            file, back_profile, height * 0.4,
            location_z=height * 0.65,
            location_y=-depth * 0.05
        )
        items.append(back_extrusion)
        
        # Chair legs (four legs)
        leg_size = 0.04
        leg_profile = create_rectangle_profile_def(file, "Chair_Leg", leg_size, leg_size)
        leg_positions = [
            (-width/2 + leg_size, -depth/2 + leg_size),
            (width/2 - leg_size*2, -depth/2 + leg_size),
            (-width/2 + leg_size, depth/2 - leg_size*2),
            (width/2 - leg_size*2, depth/2 - leg_size*2)
        ]
        for leg_x, leg_y in leg_positions:
            leg_extrusion = create_extruded_area_solid(
                file, leg_profile, height * 0.55,
                location_x=leg_x, location_y=leg_y
            )
            items.append(leg_extrusion)
    
    elif furniture_type == "table":
        # Table top
        profile = create_rectangle_profile_def(file, "Table_Top", width, depth)
        extrusion = create_extruded_area_solid(file, profile, height * 0.05, location_z=height * 0.8)
        items.append(extrusion)
        
        # Table legs (four legs at corners)
        leg_size = 0.06
        leg_profile = create_rectangle_profile_def(file, "Table_Leg", leg_size, leg_size)
        leg_positions = [
            (-width/2 + leg_size, -depth/2 + leg_size),
            (width/2 - leg_size*2, -depth/2 + leg_size),
            (-width/2 + leg_size, depth/2 - leg_size*2),
            (width/2 - leg_size*2, depth/2 - leg_size*2)
        ]
        for leg_x, leg_y in leg_positions:
            leg_extrusion = create_extruded_area_solid(
                file, leg_profile, height * 0.75,
                location_x=leg_x, location_y=leg_y
            )
            items.append(leg_extrusion)
    
    else:
        # Default: simple extruded block for unknown furniture types
        profile = create_rectangle_profile_def(file, f"{furniture_type}_Base", width, depth)
        extrusion = create_extruded_area_solid(file, profile, height)
        items.append(extrusion)
    
    return file.createIfcShapeRepresentation(
        ContextOfItems=geom_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=items
    )


def _normalize_wall_position_label(position: str) -> str:
    p = (position or "").lower()
    for key in ("north", "south", "east", "west"):
        if key in p:
            return key
    raise ValueError(f"Unrecognized wall position: {position!r}")


def _exterior_position_offset(position: str, width: float, depth: float) -> Tuple[float, float]:
    offsets = {
        "north": (0, depth / 2),
        "south": (0, -depth / 2),
        "east": (width / 2, 0),
        "west": (-width / 2, 0),
    }
    key = _normalize_wall_position_label(position)
    return offsets[key]


def create_exterior_elements(file, geom_context, exterior_data, floor_z, placement_context, space_data, space_materials) -> List[Any]:
    elements = []

    space_materials = _material_dict_from_agent(space_materials)
    exterior_finishes = space_materials

    windows = exterior_data.get("windows", [])
    for win in windows:
        win_width = win["width_m"]
        win_height = win["height_m"]
        position = win["position"]

        ox, oy = _exterior_position_offset(position, space_data.width_m, space_data.length_m)

        win_x = space_data.center_x + ox
        win_y = space_data.center_y + oy
        sill_height = floor_z + 1.0

        window = file.createIfcWindow(
            GlobalId=create_guid(),
            Name=f"Window_{space_data.name}_{position}",
            ObjectPlacement=file.createIfcLocalPlacement(
                PlacementRelTo=placement_context,
                RelativePlacement=create_default_axis2_placement_3d(file, location_x=win_x, location_y=win_y, location_z=sill_height)
            ),
            PredefinedType="WINDOW",
            OverallHeight=win_height,
            OverallWidth=win_width
        )

        frame_material = exterior_finishes["walls"]
        frame_color = exterior_finishes["walls"]
        create_material_properties(file, window, frame_material, frame_color, "Smooth", 160.0, 2700.0, 900.0)

        frame_profile = create_rectangle_profile_def(file, "ExtWindowFrame", win_width, win_height)
        frame_extrusion = create_extruded_area_solid(file, frame_profile, 0.08)
        glazing_profile = create_rectangle_profile_def(file, "ExtWindowGlazing", win_width - 0.1, win_height - 0.1)
        glazing_extrusion = create_extruded_area_solid(file, glazing_profile, 0.01, location_x=0.05, location_y=0.05)

        window.Representation = file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[frame_extrusion, glazing_extrusion]
        )

        window_property_set = file.createIfcPropertySet(
            GlobalId=create_guid(),
            Name="ExteriorWindowProperties",
            HasProperties=[
                file.createIfcPropertySingleValue("UValue", "Thermal transmittance", file.createIfcReal(1.8), None),
                file.createIfcPropertySingleValue("SolarHeatGainCoeff", "Solar heat gain coefficient", file.createIfcReal(0.4), None),
                file.createIfcPropertySingleValue("VisibleTransmittance", "Visible transmittance", file.createIfcReal(0.7), None)
            ]
        )
        rel_defines_by_properties(file, window, window_property_set)

        elements.append(window)

    doors = exterior_data.get("doors", [])
    for dr in doors:
        dr_width = dr["width_m"]
        dr_height = dr["height_m"]
        position = dr["position"]

        ox, oy = _exterior_position_offset(position, space_data.width_m, space_data.length_m)

        dr_x = space_data.center_x + ox
        dr_y = space_data.center_y + oy

        door = file.createIfcDoor(
            GlobalId=create_guid(),
            Name=f"Door_{space_data.name}_{position}",
            ObjectPlacement=file.createIfcLocalPlacement(
                PlacementRelTo=placement_context,
                RelativePlacement=create_default_axis2_placement_3d(file, location_x=dr_x, location_y=dr_y, location_z=floor_z)
            ),
            PredefinedType="DOOR",
            OverallHeight=dr_height,
            OverallWidth=dr_width
        )

        door_material = dr.get("material", exterior_finishes["walls"])
        door_color = exterior_finishes["walls"]
        create_material_properties(file, door, door_material, door_color, "Smooth")

        door_profile = create_rectangle_profile_def(file, "ExtDoorPanel", dr_width - 0.1, dr_height - 0.1)
        door_extrusion = create_extruded_area_solid(file, door_profile, 0.04, location_x=0.05, location_y=0.05)
        frame_profile = create_rectangle_profile_def(file, "ExtDoorFrame", dr_width, dr_height)
        frame_extrusion = create_extruded_area_solid(file, frame_profile, 0.05)

        door.Representation = file.createIfcShapeRepresentation(
            ContextOfItems=geom_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[frame_extrusion, door_extrusion]
        )

        door_property_set = file.createIfcPropertySet(
            GlobalId=create_guid(),
            Name="ExteriorDoorProperties",
            HasProperties=[
                file.createIfcPropertySingleValue("FireRating", "Fire rating", file.createIfcLabel("30 min"), None),
                file.createIfcPropertySingleValue("AcousticRating", "Acoustic rating", file.createIfcLabel("30 dB"), None),
                file.createIfcPropertySingleValue("UValue", "Thermal transmittance", file.createIfcReal(2.5), None)
            ]
        )
        rel_defines_by_properties(file, door, door_property_set)

        elements.append(door)

    return elements


class IFCGeometryAgentV2(BaseAgent):
    def __init__(self, output_dir: str):
        super().__init__("IFCGeometryAgentV2")
        self.output_dir = Path(output_dir)

    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        task.status = TaskStatus.IFC_GENERATING
        task.progress = 10

        design: ArchitecturalDesignData = context["llm_design"]
        site_params = context["ifc_site_parameters"]
        space_designs = context["space_designs"]
        arch_params = context["arch_params"]
        coordinator_materials = context["materials"]

        file = create_ifc_file_instance(settings.ifc_schema.value)

        project, geom_context, project_placement = create_project_and_context(file, "Building_Project")

        site = create_site(file, design.site.name, project_placement, site_params['elevation'], site_params.get('coordinates'))
        building, building_placement = create_building(file, design.building, project_placement)

        storeys = []
        floor_elements = []
        for floor_data in design.floors:
            floor_space_designs = [
                sd for sd in space_designs
                if sd["floor_number"] == floor_data.floor_number
            ]

            storey, elements = create_floor(
                file, geom_context, floor_data, building_placement,
                floor_space_designs, arch_params, coordinator_materials
            )
            storeys.append(storey)
            floor_elements.append((storey, elements))

        if design.roof:
            total_height = sum(f.height_m for f in design.floors)
            roof_slab = create_roof_slab(file, geom_context, design.roof, design.building, len(design.floors), total_height / len(design.floors), building_placement, coordinator_materials)
            if storeys:
                floor_elements[-1][1].append(roof_slab)

        for storey, elements in floor_elements:
            if elements:
                file.createIfcRelContainedInSpatialStructure(
                    GlobalId=create_guid(), OwnerHistory=None,
                    RelatingStructure=storey, RelatedElements=elements
                )

        if len(design.floors) > 1:
            total_height = sum(f.height_m for f in design.floors)
            avg_floor_height = total_height / len(design.floors)
            staircase_elements = create_staircase(file, geom_context, len(design.floors), avg_floor_height,
                                       design.building.width_m, design.building.depth_m, building_placement)
            
            # Staircase connects all floors - use IfcRelReferencedInSpatialStructure
            # This allows staircase to be referenced in ALL floors it connects
            if staircase_elements:
                # Main staircase container
                main_stair = staircase_elements[0]  # IfcStair
                other_elements = staircase_elements[1:]  # Flights, landings, railings
                
                # Reference in BOTH floors using IfcRelReferencedInSpatialStructure
                for storey in storeys:
                    file.createIfcRelReferencedInSpatialStructure(
                        GlobalId=create_guid(), OwnerHistory=None,
                        RelatingStructure=storey, 
                        RelatedElements=[main_stair] + other_elements
                    )

        if storeys:
            file.createIfcRelAggregates(
                GlobalId=create_guid(), OwnerHistory=None,
                RelatingObject=building, RelatedObjects=storeys
            )

        file.createIfcRelAggregates(
            GlobalId=create_guid(), OwnerHistory=None,
            RelatingObject=site, RelatedObjects=[building]
        )

        task_id = task.id
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure parent directories exist
        ifc_path = self.output_dir / f"{task_id}.ifc"
        ifc_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.log(f"Writing IFC file to {ifc_path}")
            file.write(str(ifc_path))
            self.log(f"IFC file written successfully: {ifc_path.stat().st_size} bytes")
            context["ifc_path"] = str(ifc_path)
        except Exception as e:
            self.log(f"ERROR writing IFC file: {e}")
            raise
        context["ifc_file"] = file
        context["ifc_entities"] = len(list(file))

        task.status = TaskStatus.IFC_COMPLETE
        task.progress = 100

        return context

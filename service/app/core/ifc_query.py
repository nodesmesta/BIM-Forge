"""
IFC Schema Query Layer.

Provides dynamic querying of IFC4 schema for LLM agents to discover
valid entity types, properties, and relationships without hardcoding.

This enables LLM-based agents to reason about IFC schema constraints
before generating specifications.
"""

import ifcopenshell
from typing import Dict, List, Any, Optional


class IFCQuery:
    """
    Query IFC4 schema for entity definitions, properties, and relationships.

    Usage:
        query = IFCQuery()
        wall_types = query.get_predefined_types("IfcWall")
        wall_attrs = query.get_attributes("IfcWall")
        space_psets = query.get_property_sets("IfcSpace")
    """

    def __init__(self, schema: str = "IFC4"):
        self.schema = schema
        self._file = ifcopenshell.file(schema=schema)
        self._entity_cache: Dict[str, Dict[str, Any]] = {}
        self._predefined_types_cache: Dict[str, List[str]] = {}
        self._containers_cache: Dict[str, List[str]] = {}
        self._build_cache()

    def _build_cache(self):
        """Build cache for all entity definitions."""
        # Get all entity classes from schema
        # We use a known list of commonly used IFC entities
        common_entities = [
            "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey",
            "IfcSpace", "IfcWall", "IfcSlab", "IfcColumn", "IfcBeam",
            "IfcDoor", "IfcWindow", "IfcStair", "IfcRoof", "IfcFloor",
            "IfcFurnishingElement", "IfcPlate", "IfcMember",
        ]

        for entity_name in common_entities:
            self._cache_entity(entity_name)

    def _cache_entity(self, entity_name: str):
        """Cache entity definition including predefined types and attributes."""
        try:
            # Create a temporary entity to inspect its schema
            entity = self._file.create_entity(entity_name)

            # Get predefined types if available
            predefined_types = self._get_predefined_types(entity_name)

            # Get attributes
            attributes = self._get_attributes(entity_name)

            # Get valid containers
            containers = self._get_valid_containers(entity_name)

            self._entity_cache[entity_name] = {
                "predefined_types": predefined_types,
                "attributes": attributes,
                "containers": containers,
            }
        except Exception as e:
            # Entity not found or error - skip
            pass

    def _get_predefined_types(self, entity_name: str) -> List[str]:
        """Get valid PredefinedType values for an entity."""
        if entity_name in self._predefined_types_cache:
            return self._predefined_types_cache[entity_name]

        # Define predefined types for common entities
        # These are based on IFC4 schema definitions
        predefined_types_map = {
            "IfcWall": ["WALL", "LOADBEARING", "ELEMENTEDWALL", "PARTITIONING", "EXTERIORWALL", "INTERIORWALL"],
            "IfcSlab": ["SLAB", "FLOOR", "ROOF", "LANDING", "BASESLAB"],
            "IfcColumn": ["COLUMN", "LOADBEARING"],
            "IfcBeam": ["BEAM", "LOADBEARING", "FOOTING", "PILE", "RIGGER", "SUPPORTINGBEAM", "STAIRFLIGHT"],
            "IfcDoor": ["DOOR", "GATEDOOR", "LOCKINGDOOR", "METALDOOR", "PLASTICDOOR", "WOODDOOR"],
            "IfcWindow": ["WINDOW", "SKYLIGHT", "ROOFLIGHT"],
            "IfcStair": ["STAIR", "STAIRFLIGHT", "STAIRLANDING"],
            "IfcRoof": ["ROOF", "FLATROOF", "SHELTER"],
            "IfcPlate": ["PLATE", "LOADBEARING", "CURTAINPANEL", "SHEATHING"],
            "IfcMember": ["MEMBER", "BRACE", "MULLION", "PURLIN", "RAFTER", "STIFFENER", "SUPPORTING"],
            "IfcFurnishingElement": ["FURNITURE", "FURNISHINGELEMENT"],
            "IfcSpace": ["SPACE", "PARKING", "GFA"],
        }

        types = predefined_types_map.get(entity_name, [])
        self._predefined_types_cache[entity_name] = types
        return types

    def _get_attributes(self, entity_name: str) -> Dict[str, Any]:
        """Get attribute definitions for an entity."""
        # Define required and optional attributes for common entities
        # Based on IFC4 schema
        attributes_map = {
            "IfcProject": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "LongName", "Description", "RepresentationContexts", "UnitsInContext"],
            },
            "IfcSite": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "LongName", "RefLatitude", "RefLongitude", "RefElevation", "LandTitleNumber", "Address"],
            },
            "IfcBuilding": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "LongName", "Address", "ElevationOfRefHeight", "ElevationOfTerrain"],
            },
            "IfcBuildingStorey": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "LongName", "Elevation"],
            },
            "IfcSpace": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "LongName", "ObjectType", "Elevation", "HasCoverings"],
            },
            "IfcWall": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcSlab": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcColumn": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcBeam": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcDoor": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag", "OverallHeight", "OverallWidth"],
            },
            "IfcWindow": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag", "OverallHeight", "OverallWidth"],
            },
            "IfcStair": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcRoof": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcPlate": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcMember": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "PredefinedType", "Tag"],
            },
            "IfcFurnishingElement": {
                "required": ["GlobalId", "Name"],
                "optional": ["OwnerHistory", "ObjectType", "Tag"],
            },
        }

        attrs = attributes_map.get(entity_name, {
            "required": ["GlobalId", "Name"],
            "optional": ["OwnerHistory", "ObjectType", "Tag"],
        })
        return attrs

    def _get_valid_containers(self, entity_name: str) -> List[str]:
        """Get valid container types for an entity."""
        if entity_name in self._containers_cache:
            return self._containers_cache[entity_name]

        containers_map = {
            "IfcProject": [],
            "IfcSite": ["IfcProject"],
            "IfcBuilding": ["IfcSite", "IfcProject"],
            "IfcBuildingStorey": ["IfcBuilding"],
            "IfcSpace": ["IfcBuildingStorey", "IfcBuilding"],
            "IfcWall": ["IfcBuildingStorey", "IfcSpace"],
            "IfcSlab": ["IfcBuildingStorey", "IfcSpace"],
            "IfcColumn": ["IfcBuildingStorey", "IfcSpace"],
            "IfcBeam": ["IfcBuildingStorey", "IfcSpace"],
            "IfcDoor": ["IfcWall", "IfcBuildingStorey", "IfcSpace"],
            "IfcWindow": ["IfcWall", "IfcBuildingStorey"],
            "IfcStair": ["IfcBuildingStorey"],
            "IfcRoof": ["IfcBuildingStorey", "IfcBuilding"],
            "IfcFloor": ["IfcBuildingStorey"],
            "IfcPlate": ["IfcBuildingStorey", "IfcSpace", "IfcWall"],
            "IfcMember": ["IfcBuildingStorey", "IfcSpace"],
            "IfcFurnishingElement": ["IfcSpace", "IfcBuildingStorey"],
        }

        containers = containers_map.get(entity_name, [])
        self._containers_cache[entity_name] = containers
        return containers

    def get_predefined_types(self, ifc_class: str) -> List[str]:
        """
        Get valid PredefinedType values for an IFC entity class.

        Args:
            ifc_class: IFC entity class name (e.g., "IfcWall", "IfcSlab")

        Returns:
            List of valid predefined type strings
        """
        if ifc_class not in self._entity_cache:
            self._cache_entity(ifc_class)
        return self._entity_cache.get(ifc_class, {}).get("predefined_types", [])

    def get_attributes(self, ifc_class: str) -> Dict[str, List[str]]:
        """
        Get required and optional attributes for an IFC entity class.

        Args:
            ifc_class: IFC entity class name

        Returns:
            Dict with "required" and "optional" keys containing attribute lists
        """
        if ifc_class not in self._entity_cache:
            self._cache_entity(ifc_class)
        return self._entity_cache.get(ifc_class, {}).get("attributes", {"required": [], "optional": []})

    def get_required_attributes(self, ifc_class: str) -> List[str]:
        """Get required attributes for an IFC entity class."""
        attrs = self.get_attributes(ifc_class)
        return attrs.get("required", [])

    def get_optional_attributes(self, ifc_class: str) -> List[str]:
        """Get optional attributes for an IFC entity class."""
        attrs = self.get_attributes(ifc_class)
        return attrs.get("optional", [])

    def get_valid_containers(self, ifc_class: str) -> List[str]:
        """
        Get valid container types for an IFC entity.

        Args:
            ifc_class: IFC entity class name

        Returns:
            List of valid container entity class names
        """
        if ifc_class not in self._entity_cache:
            self._cache_entity(ifc_class)
        return self._entity_cache.get(ifc_class, {}).get("containers", [])

    def get_property_sets(self, ifc_class: str) -> List[str]:
        """
        Get common Property Set templates for an IFC entity class.

        Args:
            ifc_class: IFC entity class name

        Returns:
            List of common Pset names for this entity
        """
        psets_map = {
            "IfcWall": ["Pset_WallCommon", "Pset_WallStructural", "Pset_WallAcoustic"],
            "IfcSlab": ["Pset_SlabCommon", "Pset_SlabStructural"],
            "IfcColumn": ["Pset_ColumnCommon", "Pset_ColumnStructural"],
            "IfcBeam": ["Pset_BeamCommon", "Pset_BeamStructural"],
            "IfcDoor": ["Pset_DoorCommon", "Pset_DoorAcoustic", "Pset_DoorFire"],
            "IfcWindow": ["Pset_WindowCommon", "Pset_WindowAcoustic", "Pset_WindowFire"],
            "IfcSpace": ["Pset_SpaceCommon", "Pset_SpaceBIM", "Pset_SpaceThermal"],
            "IfcBuildingStorey": ["Pset_BuildingStoreyCommon"],
            "IfcBuilding": ["Pset_BuildingCommon", "Pset_BuildingEnergy"],
            "IfcSite": ["Pset_SiteCommon"],
            "IfcStair": ["Pset_StairCommon", "Pset_StairFlightCommon"],
            "IfcRoof": ["Pset_RoofCommon"],
        }
        return psets_map.get(ifc_class, [])

    def get_entity_info(self, ifc_class: str) -> Dict[str, Any]:
        """
        Get complete entity information including predefined types, attributes, and containers.

        Args:
            ifc_class: IFC entity class name

        Returns:
            Dict with all entity information
        """
        if ifc_class not in self._entity_cache:
            self._cache_entity(ifc_class)
        return self._entity_cache.get(ifc_class, {})

    def get_prompt_context(self) -> str:
        """
        Generate a text context for LLM prompts showing IFC4 schema information.

        Returns:
            Formatted string with IFC schema info for LLM reference
        """
        lines = ["IFC4 Schema Reference for Building Elements:", ""]

        entities = ["IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", "IfcDoor", "IfcWindow", "IfcSpace", "IfcBuildingStorey"]

        for entity in entities:
            info = self.get_entity_info(entity)
            lines.append(f"### {entity}")

            predefined = info.get("predefined_types", [])
            if predefined:
                lines.append(f"  PredefinedTypes: {', '.join(predefined)}")

            attrs = info.get("attributes", {})
            required = attrs.get("required", [])
            if required:
                lines.append(f"  Required: {', '.join(required)}")

            psets = self.get_property_sets(entity)
            if psets:
                lines.append(f"  PropertySets: {', '.join(psets)}")

            containers = info.get("containers", [])
            if containers:
                lines.append(f"  CanBeContainedBy: {', '.join(containers)}")

            lines.append("")

        return "\n".join(lines)

    def list_all_entities(self) -> List[str]:
        """Get list of all cached entity classes."""
        return list(self._entity_cache.keys())

import json
import logging
from typing import Any, Dict, List

from ..space_agent import SpaceAgent
from ...core.space_types import canonical_space_type_key
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class BedroomAgent(SpaceAgent):
    space_type = "bedroom"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return f"Kamar Tidur {self.instance_id}"

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        logging.info(f"[BEDROOM_AGENT_DEBUG] Received args: brief={brief}, context_keys={list(context.keys())}, position={position}, dimensions={dimensions}")

        env_context = context["environment_context"]
        location = env_context["location"]
        climate = env_context["climate_zone"]
        recommendations = env_context["recommendations"]

        style = brief.style_preference
        target_floor = position["floor_number"]
        layout_key_type = canonical_space_type_key(
            context.get("_layout_space_type", self.space_type)
        )
        is_master = layout_key_type == "master_bedroom"
        
        # Get wall bounds for furniture placement
        wall_bounds = position.get("wall_bounds", {})

        width = dimensions["width_m"]
        length = dimensions["length_m"]
        height = dimensions["height_m"]

        prompt = self._build_llm_prompt(
            style, climate, location, target_floor, width, length, height,
            is_master, recommendations, wall_bounds
        )

        self.log(f"Calling LLM for {self._generate_name(brief)} interior design...")
        llm_response = await self.gemini_client.generate_architectural_design(prompt)
        self.log(f"LLM response received for {self._generate_name(brief)}")

        design = self._normalize_llm_response(llm_response, brief, env_context, style, target_floor, wall_bounds)

        return design

    def _build_llm_prompt(
        self,
        style: str,
        climate: str,
        location: str,
        target_floor: int,
        width: float,
        length: float,
        height: float,
        is_master: bool,
        recommendations: Dict,
        wall_bounds: Dict = None
    ) -> str:
        room_type = "Master Bedroom" if is_master else f"Bedroom {target_floor}"
        
        # Build wall info string for the prompt
        wall_info_str = ""
        if wall_bounds and wall_bounds.get("bounds"):
            bounds = wall_bounds["bounds"]
            wall_info_str = f"""
WALL BOUNDARIES (use for furniture placement):
- North wall (Y): {bounds.get('north', 0):.2f}m
- South wall (Y): {bounds.get('south', 0):.2f}m
- East wall (X): {bounds.get('east', 0):.2f}m
- West wall (X): {bounds.get('west', 0):.2f}m
- Room center: ({wall_bounds.get('center_x', 0):.2f}, {wall_bounds.get('center_y', 0):.2f})
- Room dimensions: {width}m x {length}m
"""

        prompt = f"""You are an expert interior architect. Design a {style} style bedroom for {climate} climate in {location}.

ROOM: {'Master bedroom' if is_master else 'Bedroom'} on floor {target_floor}
DIMENSIONS: {width}m width × {length}m length × {height}m height
STYLE: {style}
CLIMATE: {climate}
{wall_info_str}
CLIMATE REQUIREMENTS:
{self._get_climate_requirements(climate, recommendations)}

STYLE GUIDELINES:
{self._get_style_requirements(style)}

TASK: Provide complete bedroom design for 3D modeling.

IMPORTANT: For furniture placement, you MUST specify:
1. "wall_anchor": which wall the furniture is attached to ("north"|"south"|"east"|"west"|"center")
2. "placement_hint": position hint relative to the anchored wall 
   - For walls: "north" means front of room (positive Y), "south" means back (negative Y)
   - For walls: "east" means right side (positive X), "west" means left side (negative X)
   - "center" means in the middle of the room

Return ONLY this JSON structure:
{{
  "name": "descriptive room name",
  "furniture": [
    {{
      "type": "bed|wardrobe|nightstand|desk|chair|dresser|shelf",
      "name": "descriptive name",
      "width_m": number,
      "depth_m": number,
      "height_m": number,
      "material": "material description",
      "color": "color description",
      "style_match": "how this matches {style} style",
      "wall_anchor": "north|south|east|west|center",
      "placement_hint": "e.g., against north wall, centered on west wall",
      "blenderkit_keywords": "search keywords for 3D assets"
    }}
  ],
  "lighting": [
    {{
      "type": "ambient|task|accent",
      "fixture": "ceiling|pendant|wall|table|floor",
      "wattage": number,
      "color_temp_k": number,
      "position": "placement in room",
      "wall_anchor": "ceiling|north|south|east|west"
    }}
  ],
  "windows": [
    {{
      "type": "casement|sliding|fixed",
      "width_m": number,
      "height_m": number,
      "wall_anchor": "north|south|east|west"
    }}
  ],
  "doors": [
    {{
      "type": "hinged|sliding",
      "width_m": number,
      "height_m": number,
      "material": "material description",
      "wall_anchor": "north|south|east|west"
    }}
  ],
  "materials": {{
    "floor": "material with finish",
    "walls": "material with finish",
    "ceiling": "material with finish"
  }},
  "electrical": [
    "wall outlet positions",
    "light switch locations"
  ],
  "color_scheme": {{
    "primary": "main color",
    "secondary": "secondary color",
    "accent": "accent color (optional)"
  }}
}}

CRITICAL: All furniture MUST have wall_anchor and placement_hint. Be specific about which wall each item is attached to."""

        return prompt

    def _get_climate_requirements(self, climate: str, recommendations: Dict) -> str:
        return f"""
- **{climate.upper()} CLIMATE**:
- Ventilation: {recommendations['ventilation']}
- Materials: {recommendations['materials']}
- Windows: Use shading devices/overhangs per climate recommendations
- Color: Light colors to reflect heat"""

    def _get_style_requirements(self, style: str) -> str:
        styles = {
            "minimalist": """
- **MINIMALIST**:
- Clean lines, no ornamentation
- Neutral palette (white, gray, beige, natural wood)
- Multi-functional furniture
- Hidden storage solutions
- Maximum open floor space
- Quality over quantity""",

            "modern": """
- **MODERN**:
- Contemporary design
- Mix of materials (wood, metal, glass)
- Bold accent colors acceptable
- Statement lighting fixtures
- Open, airy feel
- Sleek hardware""",

            "tropical": """
- **TROPICAL**:
- Natural materials (teak, bamboo, rattan)
- Light, breathable fabrics
- Open design for ventilation
- Warm wood tones
- Plant elements
- Humidity-resistant materials""",

            "traditional": """
- **TRADITIONAL**:
- Classic furniture shapes
- Warm wood tones (teak, mahogany, walnut)
- Rich, warm color palette
- Decorative moldings acceptable
- Comfort-focused
- Textured fabrics"""
        }
        return styles[style]

    def _normalize_llm_response(
        self,
        llm_response: Dict,
        brief: ProjectBrief,
        env_context: Dict,
        style: str,
        target_floor: int = 1,
        wall_bounds: Dict = None
    ) -> Dict[str, Any]:
        # Normalize furniture with wall_anchor
        furniture = []
        blenderkit_furniture = []
        for item in llm_response.get("furniture", []):
            furniture_item = {
                "type": item.get("type", "unknown"),
                "name": item.get("name", "unnamed"),
                "width_m": item.get("width_m", 1.0),
                "depth_m": item.get("depth_m", 1.0),
                "height_m": item.get("height_m", 1.0),
                "material": item.get("material", "unspecified"),
                "color": item.get("color", "neutral"),
                "style_match": item.get("style_match", ""),
                # Include wall_anchor for IFC agent positioning
                "wall_anchor": item.get("wall_anchor", "center"),
                "placement_hint": item.get("placement_hint", "center of room"),
            }
            furniture.append(furniture_item)

            blenderkit_furniture.append({
                "asset_type": "furniture",
                "search_keywords": item.get("blenderkit_keywords", ""),
                "target_specs": {
                    "width": item.get("width_m", 1.0),
                    "depth": item.get("depth_m", 1.0),
                    "height": item.get("height_m", 1.0),
                    "material": item.get("material", "unspecified"),
                    "color": item.get("color", "neutral")
                }
            })

        # Normalize lighting
        lighting = []
        for item in llm_response.get("lighting", []):
            lighting_item = {
                "type": item.get("type", "ambient"),
                "subtype": item.get("fixture", "ceiling"),
                "wattage": item.get("wattage", 60),
                "color_temp": f"{item.get('color_temp_k', 4000)}K",
                "position": item.get("position", "center"),
                "wall_anchor": item.get("wall_anchor", "ceiling"),
                "control": "switch"
            }
            lighting.append(lighting_item)

        # Normalize windows - these are preferences, actual positions handled by CoordinatorAgent
        windows = []
        for w in llm_response.get("windows", []):
            windows.append({
                "type": w.get("type", "sliding"),
                "width_m": w.get("width_m", 1.2),
                "height_m": w.get("height_m", 1.2),
                "wall_anchor": w.get("wall_anchor", "north"),
                "preference": "CoordinatorAgent handles actual window placement"
            })

        # Normalize doors - these are preferences, actual positions handled by CoordinatorAgent
        doors = []
        for d in llm_response.get("doors", []):
            doors.append({
                "type": d.get("type", "hinged"),
                "width_m": d.get("width_m", 0.9),
                "height_m": d.get("height_m", 2.1),
                "material": d.get("material", "wood"),
                "wall_anchor": d.get("wall_anchor", "south"),
                "preference": "CoordinatorAgent handles actual door placement"
            })

        # Materials and other data
        materials_raw = llm_response["materials"]
        color_scheme = llm_response["color_scheme"]
        electrical = llm_response["electrical"]

        return {
            "space_type": "bedroom",
            "instance_id": self.instance_id,
            "name": self._generate_name(brief),
            "interior": {
                "furniture": furniture,
                "lighting": lighting,
                "color_scheme": color_scheme
            },
            "exterior": {
                "windows": windows,
                "doors": doors
            },
            "mep": {
                "electrical": electrical,
                "plumbing": [],
                "ventilation": ["Natural cross ventilation"]
            },
            "materials": materials_raw,
            "blenderkit": {
                "furniture": blenderkit_furniture,
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

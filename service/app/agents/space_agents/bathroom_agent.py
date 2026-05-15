from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


def _perimeter_wall_cardinal(
    center_x: float,
    center_y: float,
    width_m: float,
    length_m: float,
    building_width_m: float,
    building_depth_m: float,
) -> str:
    hw = building_width_m * 0.5
    hd = building_depth_m * 0.5
    protrusion = {
        "north": (center_y + length_m * 0.5) - hd,
        "south": (-hd) - (center_y - length_m * 0.5),
        "east": (center_x + width_m * 0.5) - hw,
        "west": (-hw) - (center_x - width_m * 0.5),
    }
    return max(protrusion, key=protrusion.get)


class BathroomAgent(SpaceAgent):
    space_type = "bathroom"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return f"Kamar Mandi {self.instance_id}"

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        env_context = context["environment_context"]
        location = env_context["location"]
        climate = env_context["climate_zone"]
        recommendations = env_context["recommendations"]

        style = brief.style_preference
        target_floor = position["floor_number"]
        is_master = self.instance_id == 0

        width = dimensions["width_m"]
        length = dimensions["length_m"]
        height = dimensions["height_m"]

        prompt = self._build_llm_prompt(style, climate, location, is_master, recommendations, width, length, height)

        self.log(f"Calling LLM for {self._generate_name(brief)} design...")
        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        return self._normalize_llm_response(
            llm_response,
            brief,
            style,
            is_master,
            target_floor,
            position,
            dimensions,
            context["specification"],
        )

    def _build_llm_prompt(self, style: str, climate: str, location: str, is_master: bool, recommendations: Dict, width: float, length: float, height: float) -> str:
        room_type = "Master Bathroom" if is_master else "Standard Bathroom"

        return f"""You are an expert bathroom designer specializing in {style} style bathrooms for {climate} climate.

Design a {room_type} with dimensions: {width}m x {length}m x {height}m.

CONTEXT:
- Style: {style}
- Climate: {climate}
- Location: {location}
- Dimensions: {width}m x {length}m x {height}m
- {'MASTER BATHROOM - premium fixtures, larger size, bathtub optional' if is_master else 'Standard bathroom - efficient, functional'}

CLIMATE CONSIDERATIONS ({climate}):
- Ventilation: {recommendations['ventilation']}
- Materials: {recommendations['materials']}
- Waterproofing: Essential in all wet zones
- Drainage: Proper slope to drain

STYLE REQUIREMENTS ({style}):
{self._get_style_requirements(style)}

TASK:
Provide complete specifications:
1. Room dimensions (optimal for fixture placement)
2. Fixtures (toilet, sink, shower, bathtub if applicable)
3. Materials (floor, walls - must be waterproof)
4. Lighting (wet-rated fixtures)
5. Ventilation (exhaust fan requirements)
6. Plumbing requirements
7. BlenderKit search parameters

Return ONLY JSON with schema:
{{
    "name": "Kamar Mandi",
    "dimensions": {{
        "width_m": {width},
        "length_m": {length},
        "height_m": {height}
    }},
    "bathroom_type": "powder_room|half_bath|full_bath|master_bath",
    "fixtures": [
        {{
            "type": "toilet|sink|shower|bathtub|bidet",
            "subtype": "specific type",
            "width_m": float,
            "depth_m": float,
            "height_m": float,
            "material": "ceramic|stone|metal|etc",
            "finish": "finish description",
            "position": "where to place",
            "blenderkit_search": "keywords for BlenderKit"
        }}
    ],
    "zones": {{
        "dry_zone": {{
            "area": "description",
            "fixtures": ["toilet", "sink"]
        }},
        "wet_zone": {{
            "area": "description",
            "fixtures": ["shower", "bathtub"],
            "drainage": "drain type and location",
            "waterproofing": "membrane description"
        }}
    }},
    "materials": {{
        "floor": {{
            "description": "anti-slip tile description",
            "blenderkit_search": "keywords"
        }},
        "walls": {{
            "description": "waterproof tile/paint description",
            "blenderkit_search": "keywords"
        }},
        "ceiling": {{
            "description": "moisture-resistant ceiling",
            "blenderkit_search": "keywords"
        }}
    }},
    "lighting": [
        {{
            "type": "ambient|task",
            "fixture_type": "ceiling|wall|vanity",
            "wattage": int,
            "color_temp_k": int,
            "rating": "IP44|IP65",
            "position": "where to place",
            "blenderkit_search": "keywords"
        }}
    ],
    "ventilation": {{
        "exhaust_fan": {{
            "required": true,
            "cfm": int,
            "position": "ceiling/wall location",
            "blenderkit_search": "exhaust fan bathroom"
        }},
        "natural_ventilation": {{
            "window": true|false,
            "size": "description"
        }}
    }},
    "plumbing": {{
        "water_supply": ["cold", "hot to sink", "hot to shower"],
        "drainage": ["floor drain", "fixture drains"],
        "vent_stack": "required"
    }},
    "color_palette": {{
        "primary": "main color",
        "secondary": "accent color",
        "reasoning": "why these colors for {climate} and {style}"
    }},
    "exterior": {{ "windows": [], "doors": [] }},
    "mep": {{ "electrical": [], "plumbing": [], "ventilation": [] }}
}}

Be specific. All fixtures must be realistic sizes. All materials must be waterproof/water-resistant."""

    def _get_style_requirements(self, style: str) -> str:
        styles = {
            "minimalist": """
- MINIMALIST:
- Clean lines, no ornamentation
- Floating vanity for open feel
- Frameless glass shower enclosure
- Large format tiles (minimal grout)
- White or light gray palette
- Hidden storage""",

            "modern": """
- MODERN:
- Contemporary fixtures
- Mixed materials (stone, metal, glass)
- Bold accent possible
- Statement lighting
- Sleek hardware""",

            "traditional": """
- TRADITIONAL:
- Classic fixture shapes
- Warm materials (stone, wood-look tile)
- Decorative elements acceptable
- Clawfoot or freestanding tub if master
- Warm color palette"""
        }
        return styles[style]

    def _normalize_llm_response(
        self,
        llm_response: Dict,
        brief: ProjectBrief,
        style: str,
        is_master: bool,
        target_floor: int,
        position: Dict[str, Any],
        dimensions: Dict[str, float],
        specification: Dict[str, Any],
    ) -> Dict[str, Any]:
        dims = llm_response["dimensions"]
        dimensions = {
            "width_m": dims["width_m"],
            "length_m": dims["length_m"],
            "height_m": dims["height_m"]
        }

        bathroom_type = llm_response["bathroom_type"]

        fixtures = []
        blenderkit_fixtures = []
        for item in llm_response["fixtures"]:
            fixture = {
                "type": item["type"],
                "subtype": item["subtype"],
                "width_m": item["width_m"],
                "depth_m": item["depth_m"],
                "height_m": item["height_m"],
                "material": item["material"],
                "finish": item["finish"],
                "position": item["position"]
            }
            fixtures.append(fixture)

            blenderkit_fixtures.append({
                "asset_type": "fixture",
                "search_keywords": item["blenderkit_search"],
                "target_specs": {
                    "width": item["width_m"],
                    "depth": item["depth_m"],
                    "height": item["height_m"]
                }
            })

        mat_raw = llm_response["materials"]
        blenderkit_materials = {
            "floor": {
                "description": mat_raw["floor"]["description"],
                "search_keywords": mat_raw["floor"]["blenderkit_search"]
            },
            "walls": {
                "description": mat_raw["walls"]["description"],
                "search_keywords": mat_raw["walls"]["blenderkit_search"]
            },
            "ceiling": {
                "description": mat_raw["ceiling"]["description"],
                "search_keywords": mat_raw["ceiling"]["blenderkit_search"]
            }
        }

        lighting = []
        blenderkit_lighting = []
        for item in llm_response["lighting"]:
            light = {
                "type": item["type"],
                "subtype": item["fixture_type"],
                "wattage": item["wattage"],
                "color_temp": f"{item['color_temp_k']}K",
                "rating": item["rating"],
                "position": item["position"]
            }
            lighting.append(light)

            blenderkit_lighting.append({
                "asset_type": "lighting",
                "search_keywords": item["blenderkit_search"],
                "target_specs": {
                    "wattage": item["wattage"],
                    "rating": item["rating"]
                }
            })

        vent_raw = llm_response["ventilation"]
        exhaust = vent_raw["exhaust_fan"]
        mep = {
            "electrical": [
                f"Exhaust fan ({exhaust['cfm']} CFM)",
                "IP44 lighting circuits",
                "GFCI outlet near sink"
            ],
            "plumbing": llm_response["plumbing"]["water_supply"] + list(vent_raw["natural_ventilation"].keys()),
            "ventilation": [
                f"Exhaust fan: {exhaust['cfm']} CFM minimum",
                "Duct to exterior",
                "Humidistat control recommended"
            ]
        }

        zones = llm_response["zones"]
        interior = {
            "fixtures": fixtures,
            "lighting": lighting,
            "zones": zones,
            "ventilation": exhaust,
            "decor": {
                "color_scheme": llm_response["color_palette"]
            }
        }

        site = specification["site"]
        wall_cardinal = _perimeter_wall_cardinal(
            position["center_x"],
            position["center_y"],
            dimensions["width_m"],
            dimensions["length_m"],
            site["building_width_m"],
            site["building_depth_m"],
        )

        windows = (
            [
                {
                    "type": "frosted",
                    "width_m": 0.6,
                    "height_m": 0.6,
                    "sill_height_m": 1.8,
                    "position": wall_cardinal,
                    "blenderkit_search": "frosted bathroom window",
                }
            ]
            if vent_raw["natural_ventilation"]["window"]
            else []
        )

        return {
            "space_type": "bathroom",
            "instance_id": self.instance_id,
            "name": llm_response["name"],
            "interior": interior,
            "exterior": {
                "windows": windows,
                "doors": [],
            },
            "mep": mep,
            "materials": {
                "floor": blenderkit_materials["floor"]["description"],
                "walls": blenderkit_materials["walls"]["description"],
                "ceiling": blenderkit_materials["ceiling"]["description"]
            },
            "blenderkit": {
                "fixtures": blenderkit_fixtures,
                "lighting": blenderkit_lighting,
                "materials": blenderkit_materials,
                "style": style,
                "bathroom_type": bathroom_type
            },
            "ifc_class": "IfcSpace"
        }

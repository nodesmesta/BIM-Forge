from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class DiningRoomAgent(SpaceAgent):
    space_type = "dining_room"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return "Ruang Makan"

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        style = brief.style_preference
        target_floor = position["floor_number"]

        width = dimensions["width_m"]
        length = dimensions["length_m"]
        height = dimensions["height_m"]

        prompt = f"""You are an expert dining room designer for {style} style.

Design a dining room with dimensions: {width}m x {length}m x {height}m.

Return COMPLETE valid JSON only - no markdown, no code fences:
{{
    "name": "Ruang Makan",
    "dimensions": {{ "width_m": {width}, "length_m": {length}, "height_m": {height} }},
    "table": {{
        "width_m": 0.9,
        "length_m": {min(2.0, length * 0.5)},
        "seating_capacity": 6,
        "material": "Solid oak wood top with black powder-coated steel legs",
        "blenderkit_search": "modern dining table oak black metal"
    }},
    "chairs": {{
        "count": 6,
        "width_m": 0.5,
        "material": "Grey fabric upholstery with black powder-coated frame",
        "blenderkit_search": "modern dining chair grey fabric"
    }},
    "lighting": [
        {{
            "type": "pendant",
            "wattage": 40,
            "color_temp_k": 3000,
            "blenderkit_search": "modern pendant light dining room"
        }}
    ],
    "materials": {{
        "floor": {{
            "description": "Light oak hardwood floor",
            "blenderkit_search": "hardwood floor oak light"
        }},
        "walls": {{
            "description": "White matte paint with white wood trim",
            "blenderkit_search": "white wall paint modern"
        }}
    }}
}}"""

        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        dims = llm_response["dimensions"]
        table = llm_response["table"]
        chairs = llm_response["chairs"]
        mat_raw = llm_response["materials"]

        return {
            "space_type": "dining_room",
            "instance_id": self.instance_id,
            "name": llm_response["name"],
            "interior": {
                "furniture": [
                    {"type": "dining_table", "width_m": table["width_m"], "length_m": table["length_m"], "seating": table["seating_capacity"]},
                    {"type": "dining_chair", "count": chairs["count"], "width_m": chairs["width_m"]}
                ],
                "lighting": llm_response["lighting"]
            },
            "exterior": {"windows": [], "doors": [], "finishes": {"floor": mat_raw["floor"]["description"], "walls": mat_raw["walls"]["description"]}},
            "mep": {"electrical": ["Pendant lighting with dimmer", "Power outlet"], "plumbing": [], "ventilation": ["Cross ventilation"]},
            "materials": {"floor": mat_raw["floor"]["description"], "walls": mat_raw["walls"]["description"]},
            "blenderkit": {
                "furniture": [
                    {"search_keywords": table["blenderkit_search"], "type": "table"},
                    {"search_keywords": chairs["blenderkit_search"], "type": "chair"}
                ],
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

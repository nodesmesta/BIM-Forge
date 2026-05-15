from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class LivingRoomAgent(SpaceAgent):
    space_type = "living_room"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return "Ruang Tamu"

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        env_context = context["environment_context"]
        style = brief.style_preference
        climate = env_context["climate_zone"]
        target_floor = position["floor_number"]

        width = dimensions["width_m"]
        length = dimensions["length_m"]
        height = dimensions["height_m"]

        self.log(f"Calling LLM for {self._generate_name(brief)} design...")

        prompt = f"""You are an expert living room designer for {style} style in {climate} climate.

Design a living room with dimensions: {width}m x {length}m x {height}m.

Return ONLY JSON:
{{
    "dimensions": {{ "width_m": float, "length_m": float, "height_m": float }},
    "furniture": [
        {{ "type": "sofa|coffee_table|tv_unit|accent_chair|side_table", "width_m": float, "depth_m": float, "height_m": float, "material": "text", "blenderkit_search": "keywords" }}
    ],
    "lighting": [
        {{ "type": "ambient|task|accent", "fixture": "ceiling|pendant|floor|wall", "wattage": int, "color_temp_k": int, "blenderkit_search": "keywords" }}
    ],
    "materials": {{
        "floor": {{ "description": "text", "blenderkit_search": "keywords" }},
        "walls": {{ "description": "text", "blenderkit_search": "keywords" }},
        "curtains": {{ "description": "text", "blenderkit_search": "keywords" }}
    }},
    "color_palette": {{ "primary": "color", "secondary": "color", "accent": "color" }}
}}"""

        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        dims = llm_response["dimensions"]
        dimensions_out = {
            "width_m": dims["width_m"],
            "length_m": dims["length_m"],
            "height_m": dims["height_m"]
        }

        furniture = []
        blenderkit_furniture = []
        for item in llm_response["furniture"]:
            furniture.append({
                "type": item["type"],
                "width_m": item["width_m"],
                "depth_m": item["depth_m"],
                "height_m": item["height_m"],
                "material": item["material"]
            })
            blenderkit_furniture.append({
                "search_keywords": item["blenderkit_search"],
                "type": item["type"]
            })

        mat_raw = llm_response["materials"]
        blenderkit_materials = {
            "floor": mat_raw["floor"]["description"],
            "walls": mat_raw["walls"]["description"],
            "curtains": mat_raw["curtains"]["description"]
        }

        return {
            "space_type": "living_room",
            "instance_id": self.instance_id,
            "name": self._generate_name(brief),
            "dimensions": dimensions_out,
            "position": {"center_x": 0.0, "center_y": 0.0, "floor_number": target_floor},
            "interior": {
                "furniture": furniture,
                "lighting": llm_response["lighting"],
                "decor": {"color_scheme": llm_response["color_palette"]}
            },
            "exterior": {"windows": [], "doors": [], "finishes": blenderkit_materials},
            "mep": {"electrical": ["Main lighting", "TV outlets", "Power outlets around seating"], "plumbing": [], "ventilation": ["Cross ventilation"]},
            "materials": blenderkit_materials,
            "blenderkit": {"furniture": blenderkit_furniture, "materials": blenderkit_materials, "style": style},
            "ifc_class": "IfcSpace"
        }

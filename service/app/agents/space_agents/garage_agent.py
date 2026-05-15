from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class GarageAgent(SpaceAgent):
    space_type = "garage"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        features = brief.desired_features if brief else []
        return "Carport" if "carport" in features else "Garage"

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        style = brief.style_preference
        features = brief.desired_features if brief else []
        is_carport = "carport" in features
        target_floor = position["floor_number"]

        width = dimensions["width_m"]
        length = dimensions["length_m"]
        height = dimensions["height_m"]

        prompt = f"""You are an expert garage/carport designer for {style} style.

Design a {"carport" if is_carport else "garage"} with dimensions: {width}m x {length}m x {height}m.

Return ONLY JSON:
{{
    "name": "{"Carport" if is_carport else "Garage"}",
    "dimensions": {{ "width_m": float, "length_m": float, "height_m": float }},
    "car_capacity": int,
    "type": "garage|carport",
    "door": {{ "width_m": float, "height_m": float, "type": "up_and_over|sliding|open", "blenderkit_search": "keywords" }},
    "storage": [
        {{ "type": "shelf|cabinet", "width_m": float, "blenderkit_search": "keywords" }}
    ],
    "lighting": [
        {{ "type": "ceiling", "wattage": int, "blenderkit_search": "keywords" }}
    ],
    "materials": {{
        "floor": {{ "description": "text", "blenderkit_search": "keywords" }},
        "walls": {{ "description": "text", "blenderkit_search": "keywords" }}
    }}
}}"""

        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        dims = llm_response["dimensions"]
        door = llm_response["door"]
        mat_raw = llm_response["materials"]

        return {
            "space_type": "garage",
            "instance_id": self.instance_id,
            "name": self._generate_name(brief),
            "interior": {
                "furniture": llm_response["storage"],
                "lighting": llm_response["lighting"],
                "car_capacity": llm_response["car_capacity"],
                "type": llm_response["type"]
            },
            "exterior": {
                "windows": [],
                "doors": [{"type": door["type"], "width_m": door["width_m"], "height_m": door["height_m"]}],
                "finishes": {"floor": mat_raw["floor"]["description"], "walls": mat_raw["walls"]["description"]}
            },
            "mep": {"electrical": ["Main lighting", "Power outlet", "Optional EV charging"], "plumbing": ["Optional floor drain"], "ventilation": ["Natural ventilation"]},
            "materials": {"floor": mat_raw["floor"]["description"], "walls": mat_raw["walls"]["description"]},
            "blenderkit": {
                "door": {"search_keywords": door["blenderkit_search"]},
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class OutdoorAgent(SpaceAgent):
    space_type = "outdoor"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        features = brief.desired_features if brief else []
        if "taman" in features or "garden" in features:
            return "Taman"
        elif "teras" in features or "terrace" in features:
            return "Teras"
        elif "balcony" in features:
            return "Balkon"
        return "Outdoor Space"

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        style = brief.style_preference
        features = brief.desired_features if brief else []
        target_floor = position["floor_number"]

        width = dimensions["width_m"]
        length = dimensions["length_m"]
        height = dimensions["height_m"]

        outdoor_type = "garden" if "taman" in features or "garden" in features else "terrace" if "teras" in features or "terrace" in features else "balcony"

        prompt = f"""You are an expert outdoor space designer for {style} style {outdoor_type}.

Design a {outdoor_type} with dimensions: {width}m x {length}m x {height}m.

Return ONLY JSON:
{{
    "name": "{outdoor_type.capitalize()}",
    "dimensions": {{ "width_m": float, "length_m": float, "height_m": float }},
    "outdoor_type": "garden|terrace|balcony",
    "features": [
        {{ "type": "plants|seating|pathway|water_feature|pergola", "description": "text", "blenderkit_search": "keywords" }}
    ],
    "furniture": [
        {{ "type": "outdoor_sofa|table|chair", "width_m": float, "blenderkit_search": "keywords" }}
    ],
    "lighting": [
        {{ "type": "string_lights|path_light", "blenderkit_search": "keywords" }}
    ],
    "materials": {{
        "floor": {{ "description": "text", "blenderkit_search": "keywords" }},
        "railing": {{ "description": "text", "blenderkit_search": "keywords" }}
    }}
}}"""

        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        dims = llm_response["dimensions"]
        mat_raw = llm_response["materials"]

        return {
            "space_type": "outdoor",
            "instance_id": self.instance_id,
            "name": llm_response["name"],
            "interior": {
                "features": llm_response["features"],
                "furniture": llm_response["furniture"],
                "lighting": llm_response["lighting"],
                "outdoor_type": llm_response["outdoor_type"]
            },
            "exterior": {
                "windows": [],
                "doors": [],
                "finishes": {"floor": mat_raw["floor"]["description"], "railing": mat_raw["railing"]["description"]}
            },
            "mep": {"electrical": ["Outdoor lighting (weatherproof)", "Optional outlet"], "plumbing": ["Optional tap for garden"], "ventilation": ["Natural ventilation"]},
            "materials": {"floor": mat_raw["floor"]["description"], "railing": mat_raw["railing"]["description"]},
            "blenderkit": {
                "features": llm_response["features"],
                "furniture": llm_response["furniture"],
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

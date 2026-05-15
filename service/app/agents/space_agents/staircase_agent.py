from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class StaircaseAgent(SpaceAgent):
    space_type = "staircase"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return f"Tangga {self.instance_id}"

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

        prompt = f"""You are an expert staircase designer for {style} style home.

Design a staircase with dimensions: {width}m x {length}m x {height}m.

Return ONLY JSON:
{{
    "name": "Tangga",
    "dimensions": {{ "width_m": float, "length_m": float, "height_m": float }},
    "stair_type": "straight|L_shaped|U_shaped|winder",
    "geometry": {{
        "riser_height_m": float,
        "tread_depth_m": float,
        "riser_count": int
    }},
    "handrail": {{ "height_m": float, "material": "text", "blenderkit_search": "keywords" }},
    "materials": {{
        "tread": {{ "description": "text", "blenderkit_search": "keywords" }},
        "riser": {{ "description": "text", "blenderkit_search": "keywords" }},
        "handrail": {{ "description": "text", "blenderkit_search": "keywords" }}
    }},
    "lighting": [
        {{ "type": "stair_light", "wattage": int, "blenderkit_search": "keywords" }}
    ]
}}"""

        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        dims = llm_response["dimensions"]
        geometry = llm_response["geometry"]
        handrail = llm_response["handrail"]
        mat_raw = llm_response["materials"]

        return {
            "space_type": "staircase",
            "instance_id": self.instance_id,
            "name": self._generate_name(brief),
            "interior": {
                "stair_type": llm_response["stair_type"],
                "geometry": {
                    "riser_height_m": geometry["riser_height_m"],
                    "tread_depth_m": geometry["tread_depth_m"],
                    "riser_count": geometry["riser_count"]
                },
                "handrail": handrail,
                "lighting": llm_response["lighting"]
            },
            "exterior": {"windows": [], "doors": [], "finishes": {"tread": mat_raw["tread"]["description"], "riser": mat_raw["riser"]["description"]}},
            "mep": {"electrical": ["Stair lighting (top and bottom)", "3-way switches"], "plumbing": [], "ventilation": ["Ensure airflow"]},
            "materials": {"tread": mat_raw["tread"]["description"], "riser": mat_raw["riser"]["description"], "handrail": handrail["material"]},
            "blenderkit": {
                "handrail": {"search_keywords": handrail["blenderkit_search"]},
                "tread": {"search_keywords": mat_raw["tread"]["blenderkit_search"]},
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class OfficeAgent(SpaceAgent):
    space_type = "office"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return f"Kantor {self.instance_id}"

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

        prompt = f"""You are an expert office designer for {style} style.

Design an office with dimensions: {width}m x {length}m x {height}m.

Return ONLY JSON:
{{
    "name": "Kantor",
    "dimensions": {{ "width_m": float, "length_m": float, "height_m": float }},
    "desk": {{ "width_m": float, "depth_m": float, "material": "text", "blenderkit_search": "keywords" }},
    "chair": {{ "type": "ergonomic|executive", "blenderkit_search": "keywords" }},
    "storage": [
        {{ "type": "bookshelf|filing_cabinet", "width_m": float, "blenderkit_search": "keywords" }}
    ],
    "lighting": [
        {{ "type": "ambient|task", "wattage": int, "blenderkit_search": "keywords" }}
    ],
    "materials": {{
        "floor": {{ "description": "text", "blenderkit_search": "keywords" }},
        "walls": {{ "description": "text", "blenderkit_search": "keywords" }}
    }}
}}"""

        llm_response = await self.gemini_client.generate_architectural_design(prompt)

        dims = llm_response["dimensions"]
        desk = llm_response["desk"]
        chair = llm_response["chair"]
        mat_raw = llm_response["materials"]

        return {
            "space_type": "office",
            "instance_id": self.instance_id,
            "name": llm_response["name"],
            "interior": {
                "furniture": [
                    {"type": "desk", "width_m": desk["width_m"], "depth_m": desk["depth_m"]},
                    {"type": "office_chair", "subtype": chair["type"]},
                    *llm_response["storage"]
                ],
                "lighting": llm_response["lighting"]
            },
            "exterior": {"windows": [], "doors": [], "finishes": {"floor": mat_raw["floor"]["description"], "walls": mat_raw["walls"]["description"]}},
            "mep": {"electrical": ["Multiple power outlets", "Data outlet", "Task lighting"], "plumbing": [], "ventilation": ["Cross ventilation", "AC recommended"]},
            "materials": {"floor": mat_raw["floor"]["description"], "walls": mat_raw["walls"]["description"]},
            "blenderkit": {
                "furniture": [
                    {"search_keywords": desk["blenderkit_search"], "type": "desk"},
                    {"search_keywords": chair["blenderkit_search"], "type": "chair"}
                ],
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

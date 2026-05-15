from typing import Any, Dict

from ..space_agent import SpaceAgent
from ...core.gemini_client import GeminiClient
from ...models.brief import ProjectBrief


class KitchenAgent(SpaceAgent):
    space_type = "kitchen"

    def __init__(self, instance_id: int = 0):
        super().__init__(instance_id=instance_id)
        self.gemini_client = GeminiClient()

    def _generate_name(self, brief: ProjectBrief) -> str:
        return "Dapur"

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
        prompt = self._build_llm_prompt(style, climate, width, length, height)
        llm_response = await self.gemini_client.generate_architectural_design(prompt)
        self.log(f"LLM response received for {self._generate_name(brief)}")

        return self._normalize_llm_response(llm_response, brief, style, target_floor)

    def _build_llm_prompt(self, style: str, climate: str, width: float, length: float, height: float) -> str:
        return f"""You are an expert kitchen designer specializing in {style} style kitchens for {climate} climate.

Design a kitchen with dimensions: {width}m x {length}m x {height}m.

CONTEXT:
- Style: {style}
- Climate: {climate}
- Dimensions: {width}m x {length}m x {height}m

REQUIREMENTS:
- Work triangle (sink-cooktop-fridge)
- Adequate counter space
- Storage solutions
- Proper ventilation
- Lighting for task areas

Return ONLY JSON with schema:
{{
    "name": "Dapur",
    "dimensions": {{ "width_m": float, "length_m": float, "height_m": float }},
    "layout_type": "galley|l_shape|u_shape|one_wall|island",
    "appliances": [
        {{ "type": "cooktop|oven|refrigerator|sink|dishwasher", "width_m": float, "depth_m": float, "height_m": float, "blenderkit_search": "keywords" }}
    ],
    "cabinetry": {{
        "base": {{ "linear_m": float, "material": "description", "blenderkit_search": "keywords" }},
        "wall": {{ "linear_m": float, "material": "description", "blenderkit_search": "keywords" }},
        "tall": {{ "count": int, "material": "description" }}
    }},
    "countertop": {{ "material": "description", "thickness_mm": int, "blenderkit_search": "keywords" }},
    "lighting": [
        {{ "type": "ambient|task", "wattage": int, "position": "description", "blenderkit_search": "keywords" }}
    ],
    "materials": {{
        "floor": {{ "description": "text", "blenderkit_search": "keywords" }},
        "walls": {{ "description": "text", "blenderkit_search": "keywords" }},
        "backsplash": {{ "description": "text", "blenderkit_search": "keywords" }}
    }},
    "ventilation": {{ "range_hood": {{ "width_m": float, "extraction_cfm": int, "blenderkit_search": "keywords" }} }},
    "exterior": {{ "windows": [], "doors": [] }},
    "mep": {{ "electrical": [], "plumbing": [], "ventilation": [] }}
}}"""

    def _normalize_llm_response(self, llm_response: Dict, brief: ProjectBrief, style: str, target_floor: int) -> Dict[str, Any]:
        dims = llm_response["dimensions"]
        dimensions = {
            "width_m": dims["width_m"],
            "length_m": dims["length_m"],
            "height_m": dims["height_m"]
        }

        appliances = []
        blenderkit_appliances = []
        for item in llm_response["appliances"]:
            appliances.append({
                "type": item["type"],
                "width_m": item["width_m"],
                "depth_m": item["depth_m"],
                "height_m": item["height_m"]
            })
            blenderkit_appliances.append({
                "search_keywords": item["blenderkit_search"],
                "type": item["type"]
            })

        mat_raw = llm_response["materials"]
        blenderkit_materials = {
            "floor": mat_raw["floor"]["description"],
            "walls": mat_raw["walls"]["description"],
            "countertop": llm_response["countertop"]["material"]
        }

        return {
            "space_type": "kitchen",
            "instance_id": self.instance_id,
            "name": llm_response["name"],
            "interior": {
                "appliances": appliances,
                "cabinetry": llm_response["cabinetry"],
                "countertop": llm_response["countertop"],
                "layout_type": llm_response["layout_type"]
            },
            "exterior": {
                "windows": [],
                "doors": []
            },
            "mep": {
                "electrical": ["Dedicated circuits for appliances", "Under-cabinet lighting"],
                "plumbing": ["Sink water supply", "Drain with P-trap", "Dishwasher connection"],
                "ventilation": [f"Range hood: {llm_response['ventilation']['range_hood']['extraction_cfm']} CFM"]
            },
            "materials": blenderkit_materials,
            "blenderkit": {
                "appliances": blenderkit_appliances,
                "materials": blenderkit_materials,
                "style": style
            },
            "ifc_class": "IfcSpace"
        }

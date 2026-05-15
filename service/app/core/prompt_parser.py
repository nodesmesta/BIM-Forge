from typing import Optional, Dict, Any
from ..models.brief import ProjectBrief
from .gemini_client import GeminiClient
from .retry_orchestrator import RetryOrchestrator
from .errors import PromptUnparseableError, LLMInternalError
from .ifc_query import IFCQuery


class LLMPromptParser:
    def __init__(self, llm_client: GeminiClient = None):
        self.client = llm_client or GeminiClient()
        self.retry = RetryOrchestrator()
        self.ifc_query = IFCQuery()

    async def parse(self, prompt: str, context: Dict[str, Any] = None) -> ProjectBrief:
        if not prompt or not prompt.strip():
            raise PromptUnparseableError("Prompt cannot be empty", prompt=prompt)

        enhanced_prompt = self._build_prompt(prompt, context)
        response = await self.retry.execute(
            self.client.generate_with_schema,
            prompt=enhanced_prompt,
            schema=ProjectBrief.model_json_schema()
        )

        brief = ProjectBrief.model_validate(response)
        brief = self._post_process(brief)

        return brief

    def _build_prompt(self, prompt: str, context: Dict[str, Any] = None) -> str:
        context_str = ""
        if context:
            if context.get("climate_zone"):
                context_str += f"\n\nCLIMATE CONTEXT: {context['climate_zone']} zone.\n"
                context_str += f"Consider: {context.get('recommendations', {})}"

            if context.get("site_constraints"):
                context_str += f"\n\nSITE CONSTRAINTS: {context['site_constraints']}"

        ifc_context = self.ifc_query.get_prompt_context()

        return f"""
You are an expert architectural specification parser. Extract ALL requirements from the user's description and convert them into a structured project brief.

USER PROMPT:
{prompt}

{context_str}

{ifc_context}

CRITICAL CONSTRAINTS:
- Floor count: 1-5 (integer)
- Room area: 2-100 m² per room
- If floor_count > 1, MUST include staircase
- All dimensions must be realistic and buildable
- Consider climate-appropriate design if climate context provided
- Use PredefinedType values from IFC4 schema above when specifying wall/slab/door/window types

OUTPUT:
Return a valid JSON object matching the ProjectBrief schema.

IMPORTANT: The output MUST be valid JSON that matches the schema exactly.
"""

    def _post_process(self, brief: ProjectBrief) -> ProjectBrief:
        if brief.floor_count and brief.floor_count > 1:
            if "staircase" not in brief.room_requirements:
                brief.room_requirements["staircase"] = {"count": 1, "min_area_m2": 5.0}

        defaults = {
            "kitchen": {"count": 1, "min_area_m2": 6.0},
            "bathroom": {"count": 1, "min_area_m2": 4.0},
            "living_room": {"count": 1, "min_area_m2": 16.0}
        }

        for room_type, default in defaults.items():
            if room_type not in brief.room_requirements:
                brief.room_requirements[room_type] = default

        if not brief.title:
            prefix = "Residential" if brief.project_type.value == "residential" else "Building"
            brief.title = f"{prefix} Project"

        if brief.floor_count is None:
            brief.floor_count = 1

        return brief

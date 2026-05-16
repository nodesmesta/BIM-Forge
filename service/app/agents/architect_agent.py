
import asyncio
from typing import Any, Dict, List

from ..models.task import Task, TaskStatus
from ..core.gemini_client import GeminiClient
from ..core.ifc_query import IFCQuery
from ..core.specification_converter import SpecificationConverter
from ..core.event_bus import get_event_bus, EventType
from .base import BaseAgent
from .space_agent_registry import SpaceAgentRegistry
from .environment_agent import EnvironmentAgent
from .coordinator_agent import CoordinatorAgent


class ArchitectAgent(BaseAgent):

    def __init__(self, coordinator_agent: "CoordinatorAgent" = None):
        super().__init__("ArchitectAgent")
        self.converter = SpecificationConverter()
        self.registry = SpaceAgentRegistry()
        self.environment_agent = EnvironmentAgent()
        self.coordinator_agent = coordinator_agent
        self.gemini_client = GeminiClient()
        self.ifc_query = IFCQuery()

    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        task.status = TaskStatus.SPEC_GENERATING
        task.progress = 10

        self.log("Step 1: Converting structured specification to ProjectBrief...")
        specification = context["specification"]

        brief = self.converter.specification_to_brief(specification)
        context["project_brief"] = brief.model_dump()
        task.progress = 20

        self.log(f"Project brief created: {brief.title}, {brief.floor_count} floors, style: {brief.style_preference}")

        self.log("Step 2: Environment analysis (querying ClimateAPI)...")
        env_context = await self.environment_agent.execute(task, context)
        context.update(env_context)
        task.progress = 30

        ifc_site_params = self.environment_agent.get_ifc_site_parameters(context)
        context["ifc_site_parameters"] = ifc_site_params

        self.log("Step 3: Requesting layout from Coordinator Agent...")
        layout_spec = await self.coordinator_agent.generate_layout(task, context)
        arch_params = context["arch_params"]
        for space_key, layout_info in layout_spec.items():
            floor_num = layout_info["floor_number"]
            if floor_num == 1:
                layout_info["height_m"] = arch_params["floor_height_ground"]
            else:
                layout_info["height_m"] = arch_params["floor_height_upper"]
        context["layout_spec"] = layout_spec
        task.progress = 50

        self.log(f"Layout generated: {len(layout_spec)} spaces positioned")

        self.log("Step 4: Spawning space agents with layout specification...")
        agents_config = self.registry.create_agents_for_layout(layout_spec)
        space_designs = await self._spawn_agents_with_layout(
            agents_config, task, context, layout_spec
        )
        task.progress = 70

        self.log("Step 5: Merging space designs with Coordinator Agent...")
        context = await self.coordinator_agent.merge_space_designs(
            task, context, space_designs
        )
        task.progress = 90

        context["ifc_query"] = self.ifc_query
        context["ifc_predefined_types"] = {
            "IfcWall": self.ifc_query.get_predefined_types("IfcWall"),
            "IfcSlab": self.ifc_query.get_predefined_types("IfcSlab"),
            "IfcDoor": self.ifc_query.get_predefined_types("IfcDoor"),
            "IfcWindow": self.ifc_query.get_predefined_types("IfcWindow"),
            "IfcSpace": self.ifc_query.get_predefined_types("IfcSpace"),
        }

        self.log(f"ArchitectAgent complete: {len(context['space_designs'])} spaces merged")

        return context

    async def _spawn_agents_with_layout(
        self,
        agents_config: List[Dict[str, Any]],
        task: Task,
        context: Dict[str, Any],
        layout_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        event_bus = get_event_bus()
        self.log(f"Spawning {len(agents_config)} space agents with layout...")

        # Broadcast space agents spawning event
        space_agents_info = [
            {"name": f"{cfg['type']}_{cfg['instance_id']}", "type": cfg["type"], "floor": cfg["layout_config"]["floor_number"]}
            for cfg in agents_config
        ]
        await event_bus.publish(
            EventType.AGENT_PROGRESS,
            payload={
                "task_id": task.id,
                "agent_name": "ArchitectAgent",
                "progress": 70,
                "phase": "Spawning Space Agents",
                "message": f"Spawning {len(agents_config)} space agents",
                "space_agents": space_agents_info
            },
            source_agent="ArchitectAgent"
        )

        semaphore = asyncio.Semaphore(5)  # Allow up to 5 agents to run concurrently

        async def run_agent(config: Dict[str, Any]) -> Dict[str, Any]:
            agent = self.registry.create_agent(config["type"], config["instance_id"])

            agent_context = context.copy()
            agent_context["layout_config"] = config["layout_config"]
            agent_context["target_floor"] = config["layout_config"]["floor_number"]
            agent_context["_layout_space_type"] = config["type"]

            agent_name = f"{config['type']}_{config['instance_id']}"

            # Publish space agent started
            await event_bus.publish(
                EventType.AGENT_STARTED,
                payload={
                    "task_id": task.id,
                    "agent_name": agent_name,
                    "progress": 0,
                    "phase": f"Designing {config['type']}",
                    "message": f"{agent_name} started on floor {config['layout_config']['floor_number']}"
                },
                source_agent=agent_name
            )

            async with semaphore:
                self.log(f"[{agent_name}] Starting with position ({config['layout_config']['center_x']}, {config['layout_config']['center_y']})...")
                result = await agent.execute(task, agent_context)
                self.log(f"[{agent_name}] Completed")

            # Publish space agent complete
            await event_bus.publish(
                EventType.AGENT_COMPLETE,
                payload={
                    "task_id": task.id,
                    "agent_name": agent_name,
                    "progress": 100,
                    "duration": 0,
                    "message": f"{agent_name} design complete"
                },
                source_agent=agent_name
            )

            return result

        tasks = [run_agent(cfg) for cfg in agents_config]
        results = await asyncio.gather(*tasks)

        return results


    
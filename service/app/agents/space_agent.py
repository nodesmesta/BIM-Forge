from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..models.task import Task, TaskStatus
from ..models.brief import ProjectBrief
from ..core.space_types import canonical_space_type_key
from .base import BaseAgent


class SpaceAgent(BaseAgent, ABC):
    space_type: str = "base"

    def __init__(self, instance_id: int = 0):
        super().__init__(f"{self.space_type.capitalize()}Agent")
        self.instance_id = instance_id
        self.name = f"{self.space_type.capitalize()}Agent_{instance_id}" if instance_id > 0 else f"{self.space_type.capitalize()}Agent"

    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        task.status = TaskStatus.PENDING
        task.progress = 20

        layout_config = context["layout_config"]
        brief_dict = context["project_brief"]
        brief = ProjectBrief(**brief_dict)
        
        # Get wall bounds from CoordinatorAgent - this tells us where the walls are
        wall_bounds_by_space = context.get("wall_bounds_by_space", {})
        space_key = f"{canonical_space_type_key(self.space_type)}_{self.instance_id}"
        wall_bounds = wall_bounds_by_space.get(space_key, {})

        position = {
            "center_x": layout_config["center_x"],
            "center_y": layout_config["center_y"],
            "floor_number": layout_config["floor_number"],
            "wall_bounds": wall_bounds  # Include wall info for furniture placement
        }

        dimensions = {
            "width_m": layout_config["width_m"],
            "length_m": layout_config["length_m"],
            "height_m": layout_config["height_m"]
        }

        design = await self._generate_interior_details(brief, context, position, dimensions)

        layout_st = context.get("_layout_space_type")
        resolved_type = (
            canonical_space_type_key(layout_st)
            if layout_st is not None
            else self.space_type
        )

        result = {
            "space_type": resolved_type,
            "instance_id": self.instance_id,
            "name": design["name"],
            "interior": design["interior"],
            "exterior": design["exterior"],
            "mep": design["mep"],
            "materials": design["materials"],
            "wall_bounds": wall_bounds  # Include wall bounds in result for IFC agent
        }

        task.progress = 100
        task.status = TaskStatus.SPEC_COMPLETE

        self.log(f"Generated {result['name']} at ({position['center_x']}, {position['center_y']}) with wall_anchor support")

        return result

    async def _generate_interior_details(
        self,
        brief: ProjectBrief,
        context: Dict[str, Any],
        position: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _generate_interior_details()"
        )

    @abstractmethod
    def _generate_name(self, brief: ProjectBrief) -> str:
        pass

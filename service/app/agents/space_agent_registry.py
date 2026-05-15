from typing import Any, Dict, List, Type

from ..core.space_types import canonical_space_type_key
from .space_agent import SpaceAgent
from .space_agents.bedroom_agent import BedroomAgent
from .space_agents.bathroom_agent import BathroomAgent
from .space_agents.kitchen_agent import KitchenAgent
from .space_agents.living_room_agent import LivingRoomAgent
from .space_agents.dining_room_agent import DiningRoomAgent
from .space_agents.office_agent import OfficeAgent
from .space_agents.garage_agent import GarageAgent
from .space_agents.staircase_agent import StaircaseAgent
from .space_agents.outdoor_agent import OutdoorAgent


class SpaceAgentRegistry:
    DEFAULT_COUNTS = {
        "bedroom": 2,
        "bathroom": 1,
        "kitchen": 1,
        "living_room": 1,
        "dining_room": 1,
        "office": 1,
        "garage": 1,
        "staircase": 1,
        "outdoor": 1,
    }

    AGENT_MAP: Dict[str, Type[SpaceAgent]] = {
        "bedroom": BedroomAgent,
        "master_bedroom": BedroomAgent,  
        "bathroom": BathroomAgent,
        "kitchen": KitchenAgent,
        "living_room": LivingRoomAgent,
        "dining_room": DiningRoomAgent,
        "office": OfficeAgent,
        "garage": GarageAgent,
        "staircase": StaircaseAgent,
        "outdoor": OutdoorAgent,
        "terrace": OutdoorAgent,
        "balcony": OutdoorAgent,
        "garden": OutdoorAgent,
    }

    def __init__(self):
        self._agents: Dict[str, SpaceAgent] = {}
        self._agent_counts: Dict[str, int] = {}

    def create_agent(self, space_type: str, instance_id: int = 0) -> SpaceAgent:
        space_type_lower = canonical_space_type_key(space_type)

        if space_type_lower not in self.AGENT_MAP:
            available = ", ".join(self.AGENT_MAP.keys())
            raise ValueError(f"Unknown space type: {space_type}. Available: {available}")

        agent_class = self.AGENT_MAP[space_type_lower]
        key = f"{space_type_lower}_{instance_id}"
        agent = agent_class(instance_id=instance_id)

        return agent

    def create_agents_for_layout(self, layout_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        agents_config = []

        for space_key, layout_info in layout_spec.items():
            parts = space_key.rsplit("_", 1)
            space_type = parts[0]
            instance_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            space_type = canonical_space_type_key(space_type)

            agents_config.append({
                "type": space_type,
                "instance_id": instance_id,
                "layout_config": layout_info
            })

        return agents_config

    def create_agents_for_brief(self, brief_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        agents_to_spawn = []

        room_reqs = brief_dict["room_requirements"]
        floor_count = brief_dict["floor_count"]

        def get_room_count(room_type: str) -> int:
            room_req = room_reqs[room_type]
            if isinstance(room_req, dict):
                return room_req["count"]
            return room_req

        bedroom_count = get_room_count("bedroom")
        for i in range(bedroom_count):
            agents_to_spawn.append({
                "type": "bedroom",
                "instance_id": i,
                "target_floor": self._assign_floor(i, bedroom_count, floor_count)
            })

        bathroom_count = get_room_count("bathroom")
        for i in range(bathroom_count):
            agents_to_spawn.append({
                "type": "bathroom",
                "instance_id": i,
                "target_floor": self._assign_floor(i, bathroom_count, floor_count)
            })

        agents_to_spawn.append({
            "type": "kitchen",
            "instance_id": 0,
            "target_floor": 1
        })

        agents_to_spawn.append({
            "type": "living_room",
            "instance_id": 0,
            "target_floor": 1
        })

        if "dining_room" in room_reqs:
            agents_to_spawn.append({
                "type": "dining_room",
                "instance_id": 0,
                "target_floor": 1
            })

        if "office" in room_reqs:
            office_count = get_room_count("office")
            for i in range(office_count):
                agents_to_spawn.append({
                    "type": "office",
                    "instance_id": i,
                    "target_floor": 2 if floor_count > 1 else 1
                })

        features = brief_dict["desired_features"]
        if "carport" in features or "garage" in features:
            agents_to_spawn.append({
                "type": "garage",
                "instance_id": 0,
                "target_floor": 1
            })

        if floor_count > 1:
            for i in range(floor_count - 1):
                agents_to_spawn.append({
                    "type": "staircase",
                    "instance_id": i,
                    "target_floor": i + 1
                })

        if any(f in features for f in ["taman", "garden", "terrace", "teras", "balcony"]):
            agents_to_spawn.append({
                "type": "outdoor",
                "instance_id": 0,
                "target_floor": 1
            })

        return agents_to_spawn

    def _assign_floor(self, instance_id: int, total_count: int, floor_count: int) -> int:
        if floor_count == 1:
            return 1

        if total_count <= floor_count:
            return (instance_id % floor_count) + 1
        else:
            return (instance_id // (total_count // floor_count + 1)) + 1

    def get_agent_info(self, space_type: str) -> Dict[str, Any]:
        key = canonical_space_type_key(space_type)
        if key not in self.AGENT_MAP:
            return {"error": f"Unknown space type: {space_type}"}

        agent_class = self.AGENT_MAP[key]
        return {
            "type": space_type,
            "class": agent_class.__name__,
            "min_width": agent_class.min_width,
            "min_length": agent_class.min_length,
            "max_width": agent_class.max_width,
            "max_length": agent_class.max_length,
            "default_height": agent_class.default_height
        }

    def list_available_types(self) -> List[str]:
        return list(self.AGENT_MAP.keys())

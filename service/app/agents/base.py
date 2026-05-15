from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import logging

from ..models.task import Task, TaskStatus
from ..core.retry import RetryHandler, RetryConfig, CircuitBreakerConfig
from ..core.event_bus import get_event_bus, EventType

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, name: str, config: RetryConfig = None):
        self.name = name
        self.retry_handler = RetryHandler(config or RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=10.0
        ))
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

    @abstractmethod
    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    async def execute_with_events(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        event_bus = get_event_bus()

        await event_bus.publish(
            EventType.AGENT_STARTED,
            payload={"task_id": task.id, "agent_name": self.name, "progress": task.progress},
            source_agent=self.name
        )

        self._started_at = datetime.now()

        try:
            result = await self.execute(task, context)
            self._completed_at = datetime.now()

            await event_bus.publish(
                EventType.AGENT_COMPLETE,
                payload={
                    "task_id": task.id,
                    "agent_name": self.name,
                    "progress": task.progress,
                    "duration": (self._completed_at - self._started_at).total_seconds()
                },
                source_agent=self.name
            )

            return result

        except Exception as e:
            await event_bus.publish(
                EventType.AGENT_FAILED,
                payload={"task_id": task.id, "agent_name": self.name, "error": str(e)},
                source_agent=self.name
            )
            raise

    def log(self, message: str):
        # Use logger only - print can cause BrokenPipeError in background processes
        logger.info(f"[{self.name}] {message}")

    async def publish_progress(self, task: Task, progress: int, message: str = None):
        event_bus = get_event_bus()
        await event_bus.publish(
            EventType.AGENT_PROGRESS,
            payload={"task_id": task.id, "agent_name": self.name, "progress": progress, "message": message},
            source_agent=self.name
        )

    async def request_revision(self, task: Task, reason: str, affected_agents: list = None):
        event_bus = get_event_bus()
        await event_bus.publish(
            EventType.REVISION_REQUEST,
            payload={"task_id": task.id, "reason": reason, "requesting_agent": self.name, "affected_agents": affected_agents or []},
            source_agent=self.name
        )

    async def request_coordination(self, task: Task, target_agents: list, request: Dict[str, Any]) -> Dict[str, Any]:
        event_bus = get_event_bus()
        response = await event_bus.publish_and_wait(
            EventType.COORDINATION_REQUEST,
            payload={"task_id": task.id, "request": request, "requesting_agent": self.name, "target_agents": target_agents},
            source_agent=self.name,
            timeout=30.0
        )
        return response.payload if response else {}

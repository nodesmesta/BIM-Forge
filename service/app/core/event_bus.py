"""
Event bus for multi-agent message passing.

This module implements an in-memory event bus for agent-to-agent communication.
In production, this can be replaced with Redis Pub/Sub or RabbitMQ.
"""

import asyncio
from typing import Callable, Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import uuid
import logging
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events that can be published."""
    # Task lifecycle
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"

    # Agent-specific
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETE = "agent_complete"
    AGENT_FAILED = "agent_failed"
    AGENT_PROGRESS = "agent_progress"

    # Revision and quality
    REVISION_REQUEST = "revision_request"
    REVISION_STARTED = "revision_started"
    REVISION_COMPLETE = "revision_complete"
    QUALITY_CHECK = "quality_check"
    QUALITY_PASSED = "quality_passed"
    QUALITY_FAILED = "quality_failed"

    # Approval workflow
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"

    # Coordination
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"

    # Alerts
    ALERT = "alert"
    WARNING = "warning"


class Event(BaseModel):
    """Event structure for message passing."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    source_agent: Optional[str] = None
    target_agent: Optional[str] = None
    payload: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: int = 0  # Higher = more urgent

    class Config:
        arbitrary_types_allowed = True


class EventBus:
    """
    In-memory event bus for agent communication.

    Usage:
        event_bus = EventBus()

        # Subscribe to events
        event_bus.subscribe(EventType.TASK_COMPLETE, my_handler)

        # Publish events
        event_bus.publish(EventType.TASK_COMPLETE, {"task_id": "123"})
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any]
    ) -> Callable:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: The type of event to subscribe to
            handler: Async or sync function that takes an Event

        Returns:
            The handler (for decorator usage)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")
        return handler

    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable
    ):
        """Unsubscribe a handler from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Handler unsubscribed from {event_type.value}")
            except ValueError:
                pass

    async def publish(
        self,
        event_type: EventType,
        payload: Dict[str, Any] = {},
        source_agent: Optional[str] = None,
        target_agent: Optional[str] = None,
        priority: int = 0
    ) -> Event:
        """
        Publish an event to all subscribers.

        Args:
            event_type: The type of event
            payload: Event data
            source_agent: Agent that published the event
            target_agent: Specific target agent (optional)
            priority: Event priority (higher = more urgent)

        Returns:
            The published event
        """
        event = Event(
            type=event_type,
            source_agent=source_agent,
            target_agent=target_agent,
            payload=payload,
            priority=priority
        )

        # Store in history
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

        # Get subscribers for this event type
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(f"No subscribers for {event_type.value}")
            return event

        # Dispatch to all handlers concurrently
        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    # Run sync handler in executor
                    tasks.append(asyncio.get_event_loop().run_in_executor(
                        None, lambda h=handler: h(event)
                    ))
            except Exception as e:
                logger.error(f"Error creating handler task: {e}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Handler error: {result}")

        logger.debug(f"Published {event_type.value} with {len(handlers)} handlers")
        return event

    async def publish_and_wait(
        self,
        event_type: EventType,
        payload: Dict[str, Any] = {},
        source_agent: Optional[str] = None,
        timeout: float = 30.0
    ) -> Optional[Event]:
        """
        Publish an event and wait for a response.

        This is useful for request-response patterns between agents.

        Args:
            event_type: The type of event
            payload: Event data
            source_agent: Agent that published the event
            timeout: Maximum time to wait for response

        Returns:
            Response event or None if timeout
        """
        response_event = asyncio.Event()
        response_data = {}

        def response_handler(event: Event):
            # Match response to this request
            if event.payload.get("request_id") == payload.get("request_id"):
                response_data["event"] = event
                response_event.set()

        # Subscribe to response
        response_type = f"{event_type.value}_response"
        try:
            response_event_type = EventType(response_type)
            self.subscribe(response_event_type, response_handler)
        except ValueError:
            # Custom response type
            self.subscribe(EventType.COORDINATION_RESPONSE, response_handler)

        # Publish request
        payload["request_id"] = str(uuid.uuid4())
        await self.publish(
            event_type=event_type,
            payload=payload,
            source_agent=source_agent
        )

        # Wait for response
        try:
            await asyncio.wait_for(response_event.wait(), timeout=timeout)
            return response_data.get("event")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to {event_type.value}")
            return None
        finally:
            # Unsubscribe
            try:
                response_event_type = EventType(response_type)
                self.unsubscribe(response_event_type, response_handler)
            except ValueError:
                self.unsubscribe(EventType.COORDINATION_RESPONSE, response_handler)

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history, optionally filtered by type."""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.type == event_type]

        return events[-limit:]

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus():
    """Reset the global event bus (for testing)."""
    global _event_bus
    _event_bus = None

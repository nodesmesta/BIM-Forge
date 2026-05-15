"""
Agent registry for managing agent lifecycle and dependencies.

This module provides a registry system for registering, discovering, and
managing agents in the multi-agent architecture.
"""

from typing import Dict, List, Any, Optional, Type, Callable, TYPE_CHECKING
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import logging

if TYPE_CHECKING:
    from ..agents.base import BaseAgent


logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"


class AgentCapabilities(BaseModel):
    """Capabilities that an agent provides."""
    name: str
    description: str
    phase: str  # e.g., "schematic_design", "design_development"
    input_types: List[str] = []
    output_types: List[str] = []
    dependencies: List[str] = []  # Other agent names this agent depends on
    can_request_revision: bool = False
    can_perform_revisions: bool = False


class AgentRegistration(BaseModel):
    """Registration information for an agent."""
    agent_id: str
    agent_class: Type
    instance: Optional[Any] = None
    capabilities: AgentCapabilities
    status: AgentStatus = AgentStatus.IDLE
    registered_at: datetime = Field(default_factory=datetime.now)
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    execution_count: int = 0
    error_count: int = 0
    max_concurrent: int = 1
    current_executions: int = 0


class AgentRegistry:
    """
    Registry for managing agent lifecycle and dependencies.

    Features:
    - Register/unregister agents
    - Agent discovery by capability
    - Dependency resolution
    - Health monitoring
    - Execution tracking
    """

    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._capabilities: Dict[str, str] = {}  # capability -> agent_id

    def register(
        self,
        agent: Any,
        capabilities: AgentCapabilities
    ) -> str:
        """
        Register an agent with the registry.

        Args:
            agent: The agent instance to register
            capabilities: The capabilities this agent provides

        Returns:
            The agent ID
        """
        agent_id = agent.name or agent.__class__.__name__

        registration = AgentRegistration(
            agent_id=agent_id,
            agent_class=agent.__class__,
            instance=agent,
            capabilities=capabilities
        )

        self._agents[agent_id] = registration

        # Index by capabilities
        self._capabilities[capabilities.name] = agent_id

        logger.info(f"Registered agent: {agent_id} with capabilities: {capabilities.name}")
        return agent_id

    def unregister(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self._agents:
            registration = self._agents[agent_id]
            # Remove capability indices
            for cap, aid in list(self._capabilities.items()):
                if aid == agent_id:
                    del self._capabilities[cap]

            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get an agent by ID."""
        registration = self._agents.get(agent_id)
        return registration.instance if registration else None

    def get_agent_by_capability(self, capability: str) -> Optional[Any]:
        """Get an agent that provides a specific capability."""
        agent_id = self._capabilities.get(capability)
        if agent_id:
            return self.get_agent(agent_id)
        return None

    def get_agents_for_phase(self, phase: str) -> List[Any]:
        """Get all agents that operate in a specific phase."""
        agents = []
        for registration in self._agents.values():
            if registration.capabilities.phase == phase:
                agents.append(registration.instance)
        return agents

    def resolve_dependencies(self, agent_id: str) -> List[str]:
        """
        Resolve all dependencies for an agent.

        Returns a list of agent IDs that must complete before this agent can run.
        """
        registration = self._agents.get(agent_id)
        if not registration:
            return []

        dependencies = []
        for dep_name in registration.capabilities.dependencies:
            dep_agent_id = self._capabilities.get(dep_name)
            if dep_agent_id:
                dependencies.append(dep_agent_id)

        return dependencies

    def get_execution_order(self, agent_ids: List[str]) -> List[str]:
        """
        Get the correct execution order for a list of agents based on dependencies.

        Uses topological sort to determine order.

        Args:
            agent_ids: List of agent IDs to order

        Returns:
            Ordered list of agent IDs
        """
        # Build dependency graph
        graph: Dict[str, set] = {}
        for agent_id in agent_ids:
            deps = set(self.resolve_dependencies(agent_id))
            graph[agent_id] = deps

        # Topological sort (Kahn's algorithm)
        ordered = []
        no_deps = [a for a in agent_ids if not graph[a]]

        while no_deps:
            node = no_deps.pop(0)
            ordered.append(node)

            for other in agent_ids:
                if node in graph[other]:
                    graph[other].remove(node)
                    if not graph[other]:
                        no_deps.append(other)

        # Check for cycles
        if len(ordered) != len(agent_ids):
            logger.error("Circular dependency detected!")
            return []

        return ordered

    def mark_agent_running(self, agent_id: str):
        """Mark an agent as running."""
        registration = self._agents.get(agent_id)
        if registration:
            registration.status = AgentStatus.RUNNING
            registration.current_executions += 1
            registration.last_heartbeat = datetime.now()

    def mark_agent_idle(self, agent_id: str):
        """Mark an agent as idle."""
        registration = self._agents.get(agent_id)
        if registration:
            registration.status = AgentStatus.IDLE
            registration.current_executions = max(0, registration.current_executions - 1)
            registration.execution_count += 1
            registration.last_heartbeat = datetime.now()

    def mark_agent_unhealthy(self, agent_id: str):
        """Mark an agent as unhealthy."""
        registration = self._agents.get(agent_id)
        if registration:
            registration.status = AgentStatus.UNHEALTHY
            registration.error_count += 1

    def is_agent_available(self, agent_id: str) -> bool:
        """Check if an agent is available for execution."""
        registration = self._agents.get(agent_id)
        if not registration:
            return False

        if registration.status in [AgentStatus.UNHEALTHY, AgentStatus.DISABLED]:
            return False

        if registration.current_executions >= registration.max_concurrent:
            return False

        return True

    def get_all_agents(self) -> List[Any]:
        """Get all registered agents."""
        return [r.instance for r in self._agents.values() if r.instance]

    def get_agent_statuses(self) -> Dict[str, AgentStatus]:
        """Get status of all agents."""
        return {
            agent_id: reg.status
            for agent_id, reg in self._agents.items()
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get a health report for all agents."""
        return {
            agent_id: {
                "status": reg.status.value,
                "execution_count": reg.execution_count,
                "error_count": reg.error_count,
                "last_heartbeat": reg.last_heartbeat.isoformat(),
                "capabilities": reg.capabilities.model_dump()
            }
            for agent_id, reg in self._agents.items()
        }


# Global registry instance
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get or create the global agent registry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def reset_registry():
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None

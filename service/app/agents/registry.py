from ..core.agent_registry import get_registry, AgentCapabilities
from ..core.config import settings
from .ifc_geometry_agent_v2 import IFCGeometryAgentV2
from .architect_agent import ArchitectAgent
from .render_agent import RenderAgent
from .coordinator_agent import CoordinatorAgent


def register_all_agents():
    registry = get_registry()

    # Create CoordinatorAgent first (used by ArchitectAgent)
    coordinator_agent = CoordinatorAgent()
    registry.register(coordinator_agent, AgentCapabilities(
        name="CoordinatorAgent",
        description="Merge space designs into complete building layout with climate-aware decisions",
        phase="design_development",
        input_types=["space_designs"],
        output_types=["building_layout", "coordinated_design"],
        dependencies=[],
        can_request_revision=False,
        can_perform_revisions=True
    ))

    # Create ArchitectAgent with CoordinatorAgent dependency
    architect_agent = ArchitectAgent(coordinator_agent=coordinator_agent)
    registry.register(architect_agent, AgentCapabilities(
        name="ArchitectAgent",
        description="Generate architectural design from building brief with floor plans, walls, doors, windows",
        phase="schematic_design",
        input_types=["user_prompt", "project_brief"],
        output_types=["architectural_design", "building_specification"],
        dependencies=["CoordinatorAgent"],
        can_request_revision=False,
        can_perform_revisions=True
    ))

    ifc_geometry_agent = IFCGeometryAgentV2(settings.output_dir)
    registry.register(ifc_geometry_agent, AgentCapabilities(
        name="IFCGeometryAgentV2",
        description="Create IFC file with complete geometric representation (walls, slabs, columns, windows, doors)",
        phase="design_development",
        input_types=["architectural_design", "project_specification"],
        output_types=["ifc_file", "ifc_geometry"],
        dependencies=[],
        can_request_revision=False,
        can_perform_revisions=True
    ))

    render_agent = RenderAgent(settings.output_dir)
    registry.register(render_agent, AgentCapabilities(
        name="RenderAgent",
        description="Render 3D image from IFC file using Blender",
        phase="schematic_design",
        input_types=["ifc_file"],
        output_types=["rendered_image", "thumbnail"],
        dependencies=["IFCGeometryAgent"],
        can_request_revision=False,
        can_perform_revisions=True
    ))

    return registry


def get_workflow_agents() -> list:
    return [
        "ArchitectAgent",
        "IFCGeometryAgentV2",
        "RenderAgent"
    ]

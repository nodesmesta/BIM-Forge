"""
Project context management for multi-agent collaboration.

This module defines the ProjectContext model that serves as the shared state
between all agents in the architectural construction production pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class BuildingDesign(BaseModel):
    """Architectural design data."""
    specification: Optional[Dict[str, Any]] = None
    floor_plans: List[Dict[str, Any]] = []
    elevations: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []
    materials: List[Dict[str, Any]] = []
    design_notes: List[str] = []
    version: str = "1.0.0"


class StructuralDesign(BaseModel):
    """Structural engineering data."""
    system_type: Optional[str] = None
    foundation_design: Optional[Dict[str, Any]] = None
    framing_plan: Optional[Dict[str, Any]] = None
    load_calculations: Optional[Dict[str, Any]] = None
    member_specifications: List[Dict[str, Any]] = []
    reinforcement_details: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"


class MEPDesign(BaseModel):
    """MEP (Mechanical, Electrical, Plumbing) design data."""
    hvac_system: Optional[Dict[str, Any]] = None
    electrical_system: Optional[Dict[str, Any]] = None
    plumbing_system: Optional[Dict[str, Any]] = None
    fire_protection: Optional[Dict[str, Any]] = None
    equipment_schedule: List[Dict[str, Any]] = []
    version: str = "1.0.0"


class ConstructionPlan(BaseModel):
    """Construction planning data."""
    phases: List[Dict[str, Any]] = []
    timeline: Optional[Dict[str, Any]] = None
    critical_path: List[str] = []
    resource_allocation: Dict[str, Any] = {}
    milestones: List[Dict[str, Any]] = []
    gantt_data: List[Dict[str, Any]] = []
    version: str = "1.0.0"


class CostEstimation(BaseModel):
    """RAB (Rencana Anggaran Biaya) data."""
    total_cost: Optional[float] = None
    cost_breakdown: Dict[str, float] = {}
    material_summary: Dict[str, Any] = {}
    labor_summary: Dict[str, Any] = {}
    equipment_summary: Dict[str, Any] = {}
    contingency: float = 0
    cash_flow_projection: List[Dict[str, Any]] = []
    cost_per_square_meter: Optional[float] = None
    version: str = "1.0.0"


class ComplianceReport(BaseModel):
    """Code compliance data."""
    overall_status: str = "pending"  # compliant, conditional, non_compliant
    code_checks: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    required_documents: List[str] = []
    permit_checklist: Dict[str, Any] = {}
    version: str = "1.0.0"


class ConstructionReview(BaseModel):
    """Builder/construction review data."""
    constructability_rating: str = "pending"  # excellent, good, fair, poor
    construction_methods: List[Dict[str, Any]] = []
    sequence_recommendations: List[Dict[str, Any]] = []
    risk_assessment: Optional[Dict[str, Any]] = None
    issues: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []
    version: str = "1.0.0"


class FilePaths(BaseModel):
    """File paths generated during the workflow."""
    ifc_path: Optional[str] = None
    render_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    structural_drawings: List[str] = []
    mep_drawings: List[str] = []
    rab_document: Optional[str] = None
    compliance_report: Optional[str] = None


class ProjectContext(BaseModel):
    """
    Shared context between all agents in the architectural construction pipeline.

    This model serves as the central data store that all agents read from and
    write to during the workflow. It maintains version history and tracks
    the state of all design and planning data.
    """
    # Project metadata
    project_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Design data from various agents
    building_design: BuildingDesign = Field(default_factory=BuildingDesign)
    structural_design: StructuralDesign = Field(default_factory=StructuralDesign)
    mep_design: MEPDesign = Field(default_factory=MEPDesign)

    # Planning and cost data
    construction_plan: ConstructionPlan = Field(default_factory=ConstructionPlan)
    cost_estimation: CostEstimation = Field(default_factory=CostEstimation)
    compliance_report: ComplianceReport = Field(default_factory=ComplianceReport)
    construction_review: ConstructionReview = Field(default_factory=ConstructionReview)

    # File outputs
    file_paths: FilePaths = Field(default_factory=FilePaths)

    # Workflow state
    current_phase: str = "pre_design"
    completed_agents: List[str] = []
    pending_agents: List[str] = []
    failed_agents: List[Dict[str, Any]] = []

    # Revision tracking
    revision_count: int = 0
    last_revision_reason: Optional[str] = None

    # Quality metrics
    overall_quality_score: Optional[float] = None
    quality_checks_passed: int = 0
    quality_checks_failed: int = 0

    # Raw data storage (for backward compatibility)
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    # Agent-specific context (free-form data per agent)
    agent_context: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def mark_agent_complete(self, agent_name: str):
        """Mark an agent as completed."""
        if agent_name not in self.completed_agents:
            self.completed_agents.append(agent_name)
        if agent_name in self.pending_agents:
            self.pending_agents.remove(agent_name)
        self.updated_at = datetime.now()

    def mark_agent_pending(self, agent_name: str):
        """Mark an agent as pending."""
        if agent_name not in self.pending_agents:
            self.pending_agents.append(agent_name)

    def mark_agent_failed(self, agent_name: str, error: str):
        """Mark an agent as failed."""
        self.failed_agents.append({
            "agent_name": agent_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()

    def increment_revision(self, reason: str):
        """Increment revision counter and record reason."""
        self.revision_count += 1
        self.last_revision_reason = reason
        self.updated_at = datetime.now()

    def update_quality_score(self, score: float):
        """Update overall quality score."""
        self.overall_quality_score = score
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return self.model_dump(mode='json')

    @classmethod
    def create(cls, project_id: str) -> "ProjectContext":
        """Create a new project context."""
        return cls(project_id=project_id)

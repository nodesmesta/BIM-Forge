from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class GenerateRequest(BaseModel):
    """Request model for generating building renders."""
    prompt: str
    max_revisions: int = 3
    quality: str = "high"  # high, medium, low
    priority: str = "normal"  # low, normal, high
    budget_limit: Optional[float] = None


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    SPEC_GENERATING = "spec_generating"
    SPEC_COMPLETE = "spec_complete"
    VALIDATING = "validating"
    IFC_GENERATING = "ifc_generating"
    IFC_COMPLETE = "ifc_complete"
    RENDERING = "rendering"
    REVISION_IN_PROGRESS = "revision_in_progress"
    REVISION_COMPLETE = "revision_complete"
    QUALITY_CHECK = "quality_check"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class RevisionStatus(str, Enum):
    """Revision status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QualityStatus(str, Enum):
    """Quality check status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"


class AgentResult(BaseModel):
    """Result from a single agent execution."""
    agent_name: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_summary: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = Field(None, ge=0, le=100)
    warnings: List[str] = []
    progress: int = 0  # Progress within this agent's execution
    current_phase: Optional[str] = None  # Current sub-phase being executed


class RevisionRecord(BaseModel):
    """Record of a revision cycle."""
    revision_id: str
    revision_number: int
    status: RevisionStatus = RevisionStatus.PENDING
    triggered_by: str  # Which agent or system triggered this revision
    reason: str
    affected_agents: List[str] = []
    phase: str = "design"  # "design" or "render"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    changes_made: List[Dict[str, Any]] = []
    quality_check_result: Optional[QualityStatus] = None


class ValidationIssue(BaseModel):
    """A validation issue found during quality checks."""
    issue_id: str
    severity: str = Field(..., pattern="^(critical|major|minor|info)$")
    agent_name: str
    category: str
    description: str
    location: Optional[str] = None
    recommended_action: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class Task(BaseModel):
    """Task model for building generation workflow."""
    id: str
    prompt: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0
    quality_status: QualityStatus = QualityStatus.PENDING
    validation_issues: List[ValidationIssue] = []
    agent_results: List[AgentResult] = []
    revision_history: List[RevisionRecord] = []
    current_revision: Optional[RevisionRecord] = None
    revision_number: int = 0
    max_revisions: int = 3
    retry_count: int = 0
    max_retries: int = 3
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None  # For structured specs and other metadata

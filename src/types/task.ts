export type TaskStatus =
  | "pending"
  | "spec_generating"
  | "spec_complete"
  | "ifc_generating"
  | "ifc_complete"
  | "rendering"
  | "completed"
  | "failed"
  | "validating"
  | "quality_check"
  | "approved"
  | "rejected"
  | "revision_in_progress"
  | "revision_complete";

export type QualityStatus = "pending" | "in_progress" | "passed" | "failed" | "conditional";

export type RevisionStatus = "pending" | "in_progress" | "completed" | "cancelled";

export interface AgentResult {
  agent_name: string;
  status: TaskStatus;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  output_summary?: Record<string, any>;
  quality_score?: number;
  warnings: string[];
}

export interface RevisionRecord {
  revision_id: string;
  revision_number: number;
  status: RevisionStatus;
  triggered_by: string;
  reason: string;
  affected_agents: string[];
  phase: string;
  started_at?: string;
  completed_at?: string;
  changes_made: Record<string, any>[];
  quality_check_result?: QualityStatus;
}

export interface ValidationIssue {
  issue_id: string;
  severity: "critical" | "major" | "minor" | "info";
  agent_name: string;
  category: string;
  description: string;
  location?: string;
  recommended_action?: string;
  resolved: boolean;
  resolved_at?: string;
  resolution_notes?: string;
}

export interface WorkflowStatus {
  task_id: string;
  status: string;
  progress: number;
  completed_agents: string[];
  failed_agents: string[];
  revision_number: number;
  phase_1_complete?: boolean;
  current_phase?: string;
  agent_statuses?: Record<string, { status: string; progress: number; current_action?: string }>;
}

export interface Task {
  id: string;
  prompt: string;
  status: TaskStatus;
  progress: number;
  result?: {
    render_path?: string;
    ifc_path?: string;
    thumbnail_path?: string;
  };
  error_message?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  quality_score?: number;
  quality_status?: QualityStatus;
  validation_issues?: ValidationIssue[];
  agent_results?: AgentResult[];
  revision_history?: RevisionRecord[];
  current_revision?: RevisionRecord;
  revision_number?: number;
  max_revisions?: number;
  retry_count?: number;
  max_retries?: number;
  context?: Record<string, any>;
  workflow_status?: WorkflowStatus;
}

export interface GalleryItem {
  id: string;
  thumbnail: string;
  image: string;
  ifc: string;
  status: TaskStatus;
  created_at: string;
}

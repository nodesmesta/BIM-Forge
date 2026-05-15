"use client";

import { useState, useEffect, useCallback } from "react";
import { TaskStatus } from "@/types/task";
import { AgentFlowTimeline, AgentState } from "../AgentFlowTimeline";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TaskDetailModalProps {
  taskId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

interface AgentResultData {
  agent_name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  quality_score?: number;
  warnings?: string[];
  output_summary?: Record<string, any>;
  error_message?: string;
}

interface WorkflowStatusData {
  task_id: string;
  status: string;
  progress: number;
  completed_agents: string[];
  failed_agents: string[];
  current_phase?: string;
  agent_statuses?: Record<string, { status: string; progress: number; current_action?: string }>;
}

interface TaskDetailData {
  id: string;
  status: string;
  progress: number;
  error_message?: string;
  result?: {
    render_path?: string;
    ifc_path?: string;
    thumbnail_path?: string;
  };
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  retry_count?: number;
  max_retries?: number;
  quality_score?: number;
  quality_status?: string;
  validation_issues?: Array<{
    severity: string;
    category: string;
    description: string;
    location?: string;
    recommended_action?: string;
  }>;
  agent_results?: AgentResultData[];
  workflow_status?: WorkflowStatusData;
}

export default function TaskDetailModal({
  taskId,
  isOpen,
  onClose,
}: TaskDetailModalProps) {
  const [task, setTask] = useState<TaskDetailData | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"flow" | "details" | "results">("flow");

  const fetchTaskDetails = useCallback(async () => {
    if (!taskId) return;

    setLoading(true);

    const response = await fetch(`${API_URL}/api/status/${taskId}`);
    const data = await response.json();
    setTask(data);
    setLoading(false);
  }, [taskId]);

  // Fetch when modal opens
  useEffect(() => {
    if (isOpen && taskId) {
      fetchTaskDetails();
    }
  }, [isOpen, taskId, fetchTaskDetails]);

  // Auto-refresh when task is still processing
  useEffect(() => {
    if (!isOpen || !taskId || !task) return;

    // Only auto-refresh if task is not completed or failed
    const isProcessing =
      task.status !== "completed" && task.status !== "failed";

    if (isProcessing) {
      const interval = setInterval(() => {
        fetchTaskDetails();
      }, 2000); // Refresh every 2 seconds

      return () => clearInterval(interval);
    }
  }, [isOpen, taskId, task, fetchTaskDetails]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
      case "approved":
        return "text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400";
      case "failed":
      case "rejected":
        return "text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400";
      case "rendering":
      case "ifc_generating":
      case "spec_generating":
      case "validating":
        return "text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400";
      case "pending":
      default:
        return "text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-400";
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className="relative w-full max-w-6xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl transform transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 rounded-t-2xl">
            <div className="flex items-center justify-between p-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
                  Task Details
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  ID: <span className="font-mono">{taskId}</span>
                </p>
              </div>

              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <svg
                  className="w-6 h-6 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Tabs */}
            <div className="flex px-6 gap-4 border-b border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setActiveTab("flow")}
                className={cn(
                  "pb-3 px-1 text-sm font-medium transition-colors border-b-2",
                  activeTab === "flow"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                )}
              >
                🔄 Workflow
              </button>
              <button
                onClick={() => setActiveTab("details")}
                className={cn(
                  "pb-3 px-1 text-sm font-medium transition-colors border-b-2",
                  activeTab === "details"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                )}
              >
                📋 Details
              </button>
              <button
                onClick={() => setActiveTab("results")}
                className={cn(
                  "pb-3 px-1 text-sm font-medium transition-colors border-b-2",
                  activeTab === "results"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                )}
              >
                📊 Results
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {loading && !task ? (
              <div className="flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-gray-500 dark:text-gray-400">
                    Loading task details...
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Status Bar */}
                <div className="flex items-center gap-4 mb-6">
                  <span
                    className={cn(
                      "px-3 py-1 rounded-full text-sm font-medium capitalize",
                      getStatusColor(task?.status || "pending")
                    )}
                  >
                    {task?.status?.replace(/_/g, " ") || "pending"}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400">
                    Progress: {task?.progress || 0}%
                  </span>
                  {task?.quality_score && (
                    <span className="text-gray-500 dark:text-gray-400">
                      Quality: {task.quality_score}%
                    </span>
                  )}
                </div>

                {/* Tab Content */}
                {activeTab === "flow" && (
                  <div className="space-y-6">
                    {/* Agent Flow Timeline */}
                    <AgentFlowTimeline taskId={taskId || undefined} task={task as any} />

                    {/* Agent Timeline List (Alternative View) */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                        Agent Timeline
                      </h3>
                      <div className="space-y-3">
                        {task?.workflow_status?.completed_agents?.map(
                          (agentName, index) => (
                            <div
                              key={agentName}
                              className="flex items-center gap-3 text-sm"
                            >
                              <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-white text-xs">
                                {index + 1}
                              </div>
                              <span className="text-green-600 dark:text-green-400">
                                ✅ {agentName}
                              </span>
                              <span className="text-gray-400">completed</span>
                            </div>
                          )
                        )}
                        {task?.workflow_status?.failed_agents?.map(
                          (agentName) => (
                            <div
                              key={agentName}
                              className="flex items-center gap-3 text-sm"
                            >
                              <div className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center text-white text-xs">
                                ❌
                              </div>
                              <span className="text-red-600 dark:text-red-400">
                                {agentName}
                              </span>
                              <span className="text-gray-400">failed</span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "details" && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Task Info */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6">
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                        Task Information
                      </h3>
                      <div className="space-y-4">
                        <div>
                          <label className="text-sm text-gray-500 dark:text-gray-400">
                            Task ID
                          </label>
                          <p className="font-mono text-sm">{task?.id}</p>
                        </div>
                        <div>
                          <label className="text-sm text-gray-500 dark:text-gray-400">
                            Created At
                          </label>
                          <p className="text-sm">{formatDate(task?.created_at)}</p>
                        </div>
                        <div>
                          <label className="text-sm text-gray-500 dark:text-gray-400">
                            Updated At
                          </label>
                          <p className="text-sm">{formatDate(task?.updated_at)}</p>
                        </div>
                        <div>
                          <label className="text-sm text-gray-500 dark:text-gray-400">
                            Completed At
                          </label>
                          <p className="text-sm">{formatDate(task?.completed_at)}</p>
                        </div>
                        <div>
                          <label className="text-sm text-gray-500 dark:text-gray-400">
                            Retry Count
                          </label>
                          <p className="text-sm">
                            {task?.retry_count || 0} / {task?.max_retries || 0}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Error Message */}
                    {task?.error_message && (
                      <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-6 border border-red-200 dark:border-red-800">
                        <h3 className="text-lg font-semibold text-red-800 dark:text-red-300 mb-4">
                          Error Message
                        </h3>
                        <pre className="text-sm text-red-700 dark:text-red-400 whitespace-pre-wrap font-mono overflow-x-auto">
                          {task.error_message}
                        </pre>
                      </div>
                    )}

                    {/* Validation Issues */}
                    {task?.validation_issues && task.validation_issues.length > 0 && (
                      <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-6 border border-amber-200 dark:border-amber-800 lg:col-span-2">
                        <h3 className="text-lg font-semibold text-amber-800 dark:text-amber-300 mb-4">
                          Validation Issues ({task.validation_issues.length})
                        </h3>
                        <div className="space-y-2">
                          {task.validation_issues.map((issue, index) => (
                            <div
                              key={index}
                              className={cn(
                                "p-3 rounded-lg text-sm",
                                issue.severity === "critical" && "bg-red-100 dark:bg-red-900/30",
                                issue.severity === "major" && "bg-orange-100 dark:bg-orange-900/30",
                                issue.severity === "minor" && "bg-yellow-100 dark:bg-yellow-900/30",
                                issue.severity === "info" && "bg-blue-100 dark:bg-blue-900/30"
                              )}
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-medium capitalize">{issue.severity}</span>
                                <span className="text-gray-500">•</span>
                                <span>{issue.category}</span>
                              </div>
                              <p className="mt-1">{issue.description}</p>
                              {issue.recommended_action && (
                                <p className="mt-1 text-gray-600 dark:text-gray-400">
                                  💡 {issue.recommended_action}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "results" && (
                  <div className="space-y-6">
                    {/* Render Preview */}
                    {task?.result?.render_path && (
                      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6">
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                          Render Preview
                        </h3>
                        <div className="relative aspect-video bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden">
                          <img
                            src={`${API_URL}${task.result.render_path}`}
                            alt="Render"
                            className="w-full h-full object-contain"
                          />
                        </div>
                      </div>
                    )}

                    {/* Output Files */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6">
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                        Output Files
                      </h3>
                      <div className="space-y-3">
                        {task?.result?.ifc_path && (
                          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg">
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">🏗️</span>
                              <div>
                                <p className="font-medium">IFC Model</p>
                                <p className="text-sm text-gray-500">
                                  {task.result.ifc_path}
                                </p>
                              </div>
                            </div>
                            <a
                              href={`${API_URL}${task.result.ifc_path}`}
                              download
                              className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-colors"
                            >
                              Download
                            </a>
                          </div>
                        )}
                        {task?.result?.render_path && (
                          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg">
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">🎨</span>
                              <div>
                                <p className="font-medium">Render Image</p>
                                <p className="text-sm text-gray-500">
                                  {task.result.render_path}
                                </p>
                              </div>
                            </div>
                            <a
                              href={`${API_URL}${task.result.render_path}`}
                              download
                              className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-colors"
                            >
                              Download
                            </a>
                          </div>
                        )}
                        {task?.result?.thumbnail_path && (
                          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg">
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">🖼️</span>
                              <div>
                                <p className="font-medium">Thumbnail</p>
                                <p className="text-sm text-gray-500">
                                  {task.result.thumbnail_path}
                                </p>
                              </div>
                            </div>
                            <a
                              href={`${API_URL}${task.result.thumbnail_path}`}
                              download
                              className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-colors"
                            >
                              Download
                            </a>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Agent Results */}
                    {task?.agent_results && task.agent_results.length > 0 && (
                      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6">
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                          Agent Results
                        </h3>
                        <div className="space-y-4">
                          {task.agent_results.map((result, index) => (
                            <div
                              key={index}
                              className="p-4 bg-white dark:bg-gray-700 rounded-lg"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium">{result.agent_name}</h4>
                                <span
                                  className={cn(
                                    "px-2 py-0.5 rounded text-xs capitalize",
                                    result.status === "completed" &&
                                      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
                                    result.status === "failed" &&
                                      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
                                    result.status === "running" &&
                                      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                                  )}
                                >
                                  {result.status}
                                </span>
                              </div>
                              {result.started_at && (
                                <p className="text-sm text-gray-500">
                                  Started: {formatDate(result.started_at)}
                                </p>
                              )}
                              {result.completed_at && (
                                <p className="text-sm text-gray-500">
                                  Completed: {formatDate(result.completed_at)}
                                </p>
                              )}
                              {result.duration && (
                                <p className="text-sm text-gray-500">
                                  Duration: {(result.duration / 1000).toFixed(2)}s
                                </p>
                              )}
                              {result.quality_score && (
                                <p className="text-sm text-gray-500">
                                  Quality Score: {result.quality_score}%
                                </p>
                              )}
                              {result.warnings && result.warnings.length > 0 && (
                                <div className="mt-2">
                                  <p className="text-sm text-amber-600 dark:text-amber-400 font-medium">
                                    Warnings:
                                  </p>
                                  <ul className="text-sm text-amber-700 dark:text-amber-500 list-disc list-inside">
                                    {result.warnings.map((w, i) => (
                                      <li key={i}>{w}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {result.error_message && (
                                <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                                  Error: {result.error_message}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 rounded-b-2xl p-4">
            <div className="flex items-center justify-between">
              <button
                onClick={fetchTaskDetails}
                disabled={loading}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                🔄 Refresh
              </button>
              <div className="flex gap-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

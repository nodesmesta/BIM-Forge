"use client";

import { useState, useEffect, useCallback } from "react";
import { TaskDetailModal } from "@/app/(admin)/generator/components/TaskDetailModal";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Task {
  id: string;
  status: string;
  progress: number;
  prompt?: string;
  created_at?: string;
  updated_at?: string;
  error_message?: string;
  quality_score?: number;
  retry_count?: number;
  revision_number?: number;
}

interface TaskStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  failed: number;
  by_status: Record<string, number>;
}

type StatusFilter = "all" | "completed" | "failed" | "pending" | "in_progress";

const statusConfig: Record<string, { label: string; color: string; bgColor: string; borderColor: string }> = {
  pending: { label: "Pending", color: "text-gray-600", bgColor: "bg-gray-100", borderColor: "border-gray-300" },
  spec_generating: { label: "Spec Generating", color: "text-blue-600", bgColor: "bg-blue-100", borderColor: "border-blue-300" },
  spec_complete: { label: "Spec Complete", color: "text-cyan-600", bgColor: "bg-cyan-100", borderColor: "border-cyan-300" },
  ifc_generating: { label: "IFC Generating", color: "text-purple-600", bgColor: "bg-purple-100", borderColor: "border-purple-300" },
  ifc_complete: { label: "IFC Complete", color: "text-indigo-600", bgColor: "bg-indigo-100", borderColor: "border-indigo-300" },
  rendering: { label: "Rendering", color: "text-pink-600", bgColor: "bg-pink-100", borderColor: "border-pink-300" },
  completed: { label: "Completed", color: "text-green-600", bgColor: "bg-green-100", borderColor: "border-green-300" },
  failed: { label: "Failed", color: "text-red-600", bgColor: "bg-red-100", borderColor: "border-red-300" },
  validating: { label: "Validating", color: "text-amber-600", bgColor: "bg-amber-100", borderColor: "border-amber-300" },
  approved: { label: "Approved", color: "text-emerald-600", bgColor: "bg-emerald-100", borderColor: "border-emerald-300" },
  rejected: { label: "Rejected", color: "text-red-700", bgColor: "bg-red-200", borderColor: "border-red-400" },
  revision_in_progress: { label: "Revising", color: "text-orange-600", bgColor: "bg-orange-100", borderColor: "border-orange-300" },
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const fetchTasks = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/tasks`);
      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (error) {
      console.error("Error fetching tasks:", error);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchStats();

    const interval = setInterval(() => {
      fetchTasks();
      fetchStats();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchTasks, fetchStats]);

  const filteredTasks = tasks.filter((task) => {
    if (statusFilter === "all") return true;
    if (statusFilter === "completed") return task.status === "completed" || task.status === "approved";
    if (statusFilter === "failed") return task.status === "failed" || task.status === "rejected";
    if (statusFilter === "pending") return task.status === "pending";
    if (statusFilter === "in_progress") return !["pending", "completed", "failed", "approved", "rejected"].includes(task.status);
    return true;
  });

  const handleViewDetails = (taskId: string) => {
    setSelectedTaskId(taskId);
    setDetailModalOpen(true);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString("id-ID", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusInfo = (status: string) => {
    return statusConfig[status] || {
      label: status.replace(/_/g, " "),
      color: "text-gray-600",
      bgColor: "bg-gray-100",
      borderColor: "border-gray-300",
    };
  };

  const getProgressColor = (progress: number, status: string) => {
    if (status === "failed" || status === "rejected") return "bg-red-500";
    if (status === "completed" || status === "approved") return "bg-green-500";
    if (progress > 50) return "bg-blue-500";
    return "bg-blue-400";
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Tasks
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Semua task yang pernah dibuat, berhasil maupun gagal
        </p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <button
            onClick={() => setStatusFilter("all")}
            className={cn(
              "p-4 rounded-lg border-2 transition-all text-left",
              statusFilter === "all"
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300"
            )}
          >
            <p className="text-2xl font-bold text-gray-800 dark:text-white">{stats.total}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total</p>
          </button>

          <button
            onClick={() => setStatusFilter("in_progress")}
            className={cn(
              "p-4 rounded-lg border-2 transition-all text-left",
              statusFilter === "in_progress"
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300"
            )}
          >
            <p className="text-2xl font-bold text-blue-600">{stats.in_progress}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">In Progress</p>
          </button>

          <button
            onClick={() => setStatusFilter("completed")}
            className={cn(
              "p-4 rounded-lg border-2 transition-all text-left",
              statusFilter === "completed"
                ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300"
            )}
          >
            <p className="text-2xl font-bold text-green-600">{stats.completed}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
          </button>

          <button
            onClick={() => setStatusFilter("failed")}
            className={cn(
              "p-4 rounded-lg border-2 transition-all text-left",
              statusFilter === "failed"
                ? "border-red-500 bg-red-50 dark:bg-red-900/20"
                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300"
            )}
          >
            <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Failed</p>
          </button>

          <button
            onClick={() => setStatusFilter("pending")}
            className={cn(
              "p-4 rounded-lg border-2 transition-all text-left",
              statusFilter === "pending"
                ? "border-gray-500 bg-gray-50 dark:bg-gray-900/20"
                : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300"
            )}
          >
            <p className="text-2xl font-bold text-gray-600">{stats.pending}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Pending</p>
          </button>
        </div>
      )}

      {/* Filter Info */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Menampilkan {filteredTasks.length} dari {tasks.length} task
        </p>
        <button
          onClick={() => {
            fetchTasks();
            fetchStats();
          }}
          className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          Refresh
        </button>
      </div>

      {/* Tasks List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400 text-lg">
            {statusFilter === "all" 
              ? "Belum ada task. Mulai dengan membuat bangunan baru!"
              : `Tidak ada task dengan status "${statusFilter.replace(/_/g, " ")}"`}
          </p>
          {statusFilter !== "all" && (
            <button
              onClick={() => setStatusFilter("all")}
              className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors"
            >
              Lihat Semua Task
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => {
            const statusInfo = getStatusInfo(task.status);
            const isProcessing = !["pending", "completed", "failed", "approved", "rejected"].includes(task.status);

            return (
              <div
                key={task.id}
                className={cn(
                  "bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-4 border-l-4 transition-all hover:shadow-theme-lg cursor-pointer",
                  statusInfo.borderColor
                )}
                onClick={() => handleViewDetails(task.id)}
              >
                <div className="flex items-center justify-between">
                  {/* Left: Task Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      {/* Status Badge */}
                      <span className={cn(
                        "px-2 py-1 rounded-full text-xs font-medium",
                        statusInfo.color,
                        statusInfo.bgColor
                      )}>
                        {statusInfo.label}
                      </span>

                      {/* Progress */}
                      {task.status !== "pending" && (
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {task.progress}%
                        </span>
                      )}

                      {/* Quality Score */}
                      {task.quality_score && (
                        <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded-full">
                          Quality: {task.quality_score.toFixed(1)}
                        </span>
                      )}

                      {/* Revision */}
                      {task.revision_number !== undefined && task.revision_number > 0 && (
                        <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 rounded-full">
                          Rev-{task.revision_number}
                        </span>
                      )}
                    </div>

                    {/* Task ID & Date */}
                    <div className="flex items-center gap-4 text-sm">
                      <span className="font-mono text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
                        {task.id.slice(0, 8)}...
                      </span>
                      <span className="text-gray-400 dark:text-gray-500">
                        {formatDate(task.created_at)}
                      </span>
                    </div>

                    {/* Error Message */}
                    {task.error_message && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400 truncate max-w-lg">
                        Error: {task.error_message}
                      </p>
                    )}
                  </div>

                  {/* Right: Progress Bar */}
                  <div className="hidden md:block w-32 ml-4">
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className={cn(
                          "h-2 rounded-full transition-all",
                          getProgressColor(task.progress, task.status)
                        )}
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                  </div>

                  {/* View Button */}
                  <div className="ml-4">
                    <span className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                      →
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Task Detail Modal */}
      <TaskDetailModal
        taskId={selectedTaskId}
        isOpen={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedTaskId(null);
        }}
      />
    </div>
  );
}
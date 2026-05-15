"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { AgentFlowTimeline, AgentState } from "./generator/components/AgentFlowTimeline";

interface Task {
  id: string;
  status: string;
  progress: number;
  prompt?: string;
  created_at?: string;
  updated_at?: string;
  error_message?: string;
  workflow_status?: {
    task_id: string;
    status: string;
    progress: number;
    completed_agents: string[];
    failed_agents: string[];
    revision_number: number;
    phase_1_complete?: boolean;
    current_phase?: string;
    agent_statuses?: Record<string, { status: string; progress: number; current_action?: string }>;
  };
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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const agentIcons: Record<string, { label: string; color: string; bgColor: string }> = {
  EnvironmentAgent: { label: "ENV", color: "text-green-600", bgColor: "bg-green-100 dark:bg-green-900/30" },
  ArchitectAgent: { label: "ARC", color: "text-blue-600", bgColor: "bg-blue-100 dark:bg-blue-900/30" },
  BedroomAgent: { label: "BED", color: "text-purple-600", bgColor: "bg-purple-100 dark:bg-purple-900/30" },
  BathroomAgent: { label: "BATH", color: "text-cyan-600", bgColor: "bg-cyan-100 dark:bg-cyan-900/30" },
  KitchenAgent: { label: "KIT", color: "text-orange-600", bgColor: "bg-orange-100 dark:bg-orange-900/30" },
  LivingRoomAgent: { label: "LIV", color: "text-pink-600", bgColor: "bg-pink-100 dark:bg-pink-900/30" },
  CoordinatorAgent: { label: "COO", color: "text-indigo-600", bgColor: "bg-indigo-100 dark:bg-indigo-900/30" },
  IFCGeometryAgent: { label: "IFC", color: "text-amber-600", bgColor: "bg-amber-100 dark:bg-amber-900/30" },
  RenderAgent: { label: "REN", color: "text-rose-600", bgColor: "bg-rose-100 dark:bg-rose-900/30" },
};

export default function Dashboard() {
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [taskStats, setTaskStats] = useState<TaskStats>({
    total: 0,
    pending: 0,
    in_progress: 0,
    completed: 0,
    failed: 0,
    by_status: {},
  });
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedTaskAgents, setSelectedTaskAgents] = useState<AgentState[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const taskWsRef = useRef<Record<string, WebSocket>>({});

  const fetchActiveTasks = async () => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/active`);
      const data = await response.json();
      setActiveTasks(data.tasks || []);
    } catch (error) {
      console.error("Error fetching active tasks:", error);
    }
  };

  const fetchTaskStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/stats`);
      const data = await response.json();
      setTaskStats(data);
    } catch (error) {
      console.error("Error fetching task stats:", error);
    }
  };

  const fetchRecentTasks = async () => {
    try {
      const response = await fetch(`${API_URL}/api/gallery`);
      const data = await response.json();
      setRecentTasks(
        data.map((item: any) => ({
          id: item.id,
          status: item.status,
          progress: item.status === "completed" ? 100 : 0,
          created_at: item.created_at,
        })).slice(0, 5)
      );
    } catch (error) {
      console.error("Error fetching gallery:", error);
    }
  };

  useEffect(() => {
    fetchActiveTasks();
    fetchTaskStats();
    fetchRecentTasks();

    // Poll for updates every 3 seconds
    pollIntervalRef.current = setInterval(() => {
      fetchActiveTasks();
      fetchTaskStats();
    }, 3000);

    // Connect to WebSocket for dashboard updates
    const wsUrl = `ws://localhost:8000/api/ws/dashboard`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onmessage = (event) => {
      const update = JSON.parse(event.data);
      if (update.type === "task_created" || update.type === "task_update") {
        fetchActiveTasks();
        fetchTaskStats();
      }
    };

    wsRef.current.onerror = () => {
      console.warn("WebSocket error for dashboard (will rely on polling)");
    };

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleViewDetails = async (task: Task) => {
    if (selectedTask?.id === task.id) {
      setSelectedTask(null);
      setSelectedTaskAgents([]);
      // Close WebSocket
      if (taskWsRef.current[task.id]) {
        taskWsRef.current[task.id].close();
        delete taskWsRef.current[task.id];
      }
      return;
    }

    setSelectedTask(task);
    
    // Initialize agent states from task data using the correct AgentState format
    const initialAgents: AgentState[] = [
      { 
        name: "ArchitectAgent", 
        icon: "📐", 
        description: "Generate building blueprint",
        color: "from-blue-500 to-indigo-600",
        bgColor: "bg-blue-50 dark:bg-blue-900/20",
        borderColor: "border-blue-300 dark:border-blue-700",
        status: "pending", 
        progress: 0 
      },
      { 
        name: "CoordinatorAgent", 
        icon: "🔄", 
        description: "Coordinate multi-agent workflow",
        color: "from-indigo-500 to-violet-600",
        bgColor: "bg-indigo-50 dark:bg-indigo-900/20",
        borderColor: "border-indigo-300 dark:border-indigo-700",
        status: "pending", 
        progress: 0 
      },
      { 
        name: "IFCGeometryAgent", 
        icon: "🏗️", 
        description: "Create IFC model",
        color: "from-cyan-500 to-blue-600",
        bgColor: "bg-cyan-50 dark:bg-cyan-900/20",
        borderColor: "border-cyan-300 dark:border-cyan-700",
        status: "pending", 
        progress: 0 
      },
      { 
        name: "RenderAgent", 
        icon: "🎨", 
        description: "Render 3D visualization",
        color: "from-pink-500 to-rose-600",
        bgColor: "bg-pink-50 dark:bg-pink-900/20",
        borderColor: "border-pink-300 dark:border-pink-700",
        status: "pending", 
        progress: 0 
      },
    ];

    // Update from task workflow_status if available
    if (task.workflow_status?.agent_statuses) {
      Object.entries(task.workflow_status.agent_statuses).forEach(([agentName, agent]: [string, any]) => {
        const idx = initialAgents.findIndex(a => a.name === agentName);
        if (idx >= 0) {
          initialAgents[idx] = {
            ...initialAgents[idx],
            status: agent.status === "complete" ? "complete" : agent.status === "running" ? "running" : "pending",
            progress: agent.progress || 0,
            currentAction: agent.current_action || "",
          };
        }
      });
    }

    // Mark completed agents
    if (task.workflow_status?.completed_agents) {
      task.workflow_status.completed_agents.forEach((agentName: string) => {
        const idx = initialAgents.findIndex(a => a.name === agentName);
        if (idx >= 0) {
          initialAgents[idx] = { ...initialAgents[idx], status: "complete", progress: 100 };
        }
      });
    }

    // Mark failed agents
    if (task.workflow_status?.failed_agents) {
      task.workflow_status.failed_agents.forEach((agentName: string) => {
        const idx = initialAgents.findIndex(a => a.name === agentName);
        if (idx >= 0) {
          initialAgents[idx] = { ...initialAgents[idx], status: "failed" };
        }
      });
    }

    setSelectedTaskAgents(initialAgents);

    // Connect to task WebSocket
    if (taskWsRef.current[task.id]) {
      taskWsRef.current[task.id].close();
    }

    const wsUrl = `ws://localhost:8000/api/ws/${task.id}`;
    const ws = new WebSocket(wsUrl);
    taskWsRef.current[task.id] = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.agent_statuses) {
          setSelectedTaskAgents(prev => {
            const updated = [...prev];
            Object.entries(data.agent_statuses).forEach(([agentName, agent]: [string, any]) => {
              const idx = updated.findIndex(a => a.name === agentName);
              if (idx >= 0) {
                updated[idx] = {
                  ...updated[idx],
                  status: agent.status === "complete" ? "complete" : agent.status === "running" ? "running" : "pending",
                  progress: agent.progress || 0,
                  currentAction: agent.current_action || "",
                };
              }
            });
            return updated;
          });
        }
      } catch (e) {
        // Ignore parse errors
      }
    };

    ws.onerror = () => {
      // Silently ignore errors
    };

    // Cleanup on unmount
    return () => {
      if (taskWsRef.current[task.id]) {
        taskWsRef.current[task.id].close();
        delete taskWsRef.current[task.id];
      }
    };
  };

  useEffect(() => {
    // Cleanup all task WebSockets on unmount
    return () => {
      Object.values(taskWsRef.current).forEach(ws => ws.close());
    };
  }, []);

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: "Pending",
      spec_generating: "Generating Specification",
      spec_complete: "Specification Complete",
      validating: "Validating",
      ifc_generating: "Creating IFC Model",
      ifc_complete: "IFC Model Complete",
      rendering: "Rendering",
      quality_check: "Quality Check",
      approved: "Approved",
      rejected: "Rejected",
      revision_in_progress: "Revision In Progress",
      revision_complete: "Revision Complete",
      completed: "Completed",
      failed: "Failed",
    };
    return labels[status] || status;
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: "bg-gray-500",
      spec_generating: "bg-blue-500",
      spec_complete: "bg-cyan-500",
      validating: "bg-purple-500",
      ifc_generating: "bg-indigo-500",
      ifc_complete: "bg-violet-500",
      rendering: "bg-pink-500",
      quality_check: "bg-amber-500",
      approved: "bg-green-500",
      rejected: "bg-red-500",
      revision_in_progress: "bg-orange-500",
      revision_complete: "bg-teal-500",
      completed: "bg-emerald-500",
      failed: "bg-red-600",
    };
    return colors[status] || "bg-gray-500";
  };

  const getAgentInfo = (name: string) => {
    return agentIcons[name] || { label: "??", color: "text-gray-600", bgColor: "bg-gray-100 dark:bg-gray-800" };
  };

  const renderAgentProgress = (task: Task) => {
    const workflowStatus = task.workflow_status;
    if (!workflowStatus || (!workflowStatus.completed_agents.length && !workflowStatus.agent_statuses)) {
      return null;
    }

    const allAgents = [
      ...workflowStatus.completed_agents,
      ...(workflowStatus.failed_agents || []),
    ];

    // If we have agent_statuses, use that for more detailed info
    if (workflowStatus.agent_statuses) {
      return (
        <div className="mt-3 space-y-2">
          {Object.entries(workflowStatus.agent_statuses).map(([agentName, agentData]) => {
            const info = getAgentInfo(agentName);
            const isComplete = agentData.status === "complete";
            const isRunning = agentData.status === "running";
            const isFailed = agentData.status === "failed";

            return (
              <div key={agentName} className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold ${info.bgColor} ${info.color} dark:${info.color}`}>
                      {info.label}
                    </span>
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {agentName}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {agentData.progress || 0}%
                    </span>
                    <span className={`w-2 h-2 rounded-full ${
                      isComplete ? "bg-green-500" : isRunning ? "bg-blue-500 animate-pulse" : isFailed ? "bg-red-500" : "bg-gray-400"
                    }`} />
                  </div>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${
                      isComplete ? "bg-green-500" : isRunning ? "bg-blue-500" : isFailed ? "bg-red-500" : "bg-gray-400"
                    }`}
                    style={{ width: `${agentData.progress || 0}%` }}
                  />
                </div>
                {agentData.current_action && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                    {agentData.current_action}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      );
    }

    // Fallback to simple completed/failed list
    return (
      <div className="mt-3 flex flex-wrap gap-2">
        {workflowStatus.completed_agents.map((agent: string) => {
          const info = getAgentInfo(agent);
          return (
            <span key={agent} className={`px-2 py-1 rounded text-xs font-medium ${info.bgColor} ${info.color} dark:${info.color}`}>
              {info.label} Done
            </span>
          );
        })}
        {workflowStatus.failed_agents.map((agent: string) => {
          const info = getAgentInfo(agent);
          return (
            <span key={agent} className="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              {info.label} Failed
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-12 gap-4 md:gap-6">
      {/* Header Card */}
      <div className="col-span-12">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-4">
            Building Generator
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            AI-powered multi-agent system for generating architectural designs from natural language descriptions.
          </p>

          {/* Task Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Tasks</p>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">{taskStats.total}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Pending</p>
              <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">{taskStats.pending}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">In Progress</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{taskStats.in_progress}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-xs text-green-600 dark:text-green-400 mb-1">Completed</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{taskStats.completed}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <p className="text-xs text-red-600 dark:text-red-400 mb-1">Failed</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{taskStats.failed}</p>
            </div>
          </div>

          <div className="flex gap-4">
            <Link
              href="/generator"
              className="inline-flex items-center justify-center rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 font-medium transition-colors"
            >
              <span>Generate Building</span>
              <svg className="ml-2 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>

            <Link
              href="/gallery"
              className="inline-flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-800 dark:text-white px-6 py-3 font-medium transition-colors"
            >
              View Gallery
            </Link>
          </div>
        </div>
      </div>

      {/* Active Tasks */}
      {activeTasks.length > 0 && (
        <div className="col-span-12">
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
              Active Tasks ({activeTasks.length})
            </h2>
            <div className="space-y-4">
              {activeTasks.map((task) => (
                <div key={task.id} className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-800 dark:text-white">
                          Task {task.id.substring(0, 8)}...
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium text-white ${getStatusColor(task.status)}`}>
                          {getStatusLabel(task.status)}
                        </span>
                      </div>
                      {task.prompt && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate mb-2">
                          {task.prompt}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleViewDetails(task)}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-4"
                    >
                      {selectedTask?.id === task.id ? "Hide Details" : "View Details"}
                    </button>
                  </div>

                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${getStatusColor(task.status)}`}
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-2">
                    <span>Progress: {task.progress}%</span>
                    {task.created_at && (
                      <span>Started: {new Date(task.created_at).toLocaleTimeString()}</span>
                    )}
                  </div>

                  {/* Expanded Details */}
                  {selectedTask?.id === task.id && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      {/* Agent Flow Timeline */}
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">
                        Workflow Visualization:
                      </p>
                      <AgentFlowTimeline
                        taskId={task.id}
                        initialAgents={selectedTaskAgents}
                        compact={true}
                      />

                      {/* Task Stats */}
                      {task.workflow_status && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                          <div className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                            <p className="text-xs text-gray-500 dark:text-gray-400">Agents Done</p>
                            <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                              {task.workflow_status.completed_agents.length}
                            </p>
                          </div>
                          {task.workflow_status.failed_agents.length > 0 && (
                            <div className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                              <p className="text-xs text-gray-500 dark:text-gray-400">Agents Failed</p>
                              <p className="text-lg font-semibold text-red-600 dark:text-red-400">
                                {task.workflow_status.failed_agents.length}
                              </p>
                            </div>
                          )}
                          {task.revision_number && task.revision_number > 0 && (
                            <div className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                              <p className="text-xs text-gray-500 dark:text-gray-400">Revisions</p>
                              <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                                {task.revision_number}
                              </p>
                            </div>
                          )}
                          {task.quality_score !== undefined && task.quality_score > 0 && (
                            <div className="bg-gray-50 dark:bg-gray-900 rounded p-2">
                              <p className="text-xs text-gray-500 dark:text-gray-400">Quality Score</p>
                              <p className="text-lg font-semibold text-indigo-600 dark:text-indigo-400">
                                {task.quality_score.toFixed(0)}%
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Recent Tasks */}
      {recentTasks.length > 0 && (
        <div className="col-span-12">
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
              Recent Builds
            </h2>
            <div className="space-y-3">
              {recentTasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700 last:border-0">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {task.id.substring(0, 8)}...
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium text-white ${getStatusColor(task.status)}`}>
                    {getStatusLabel(task.status)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* How It Works */}
      <div className="col-span-12">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                1
              </div>
              <div>
                <h3 className="font-medium text-gray-800 dark:text-white text-sm">Enter Prompt</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Describe your building requirements
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                2
              </div>
              <div>
                <h3 className="font-medium text-gray-800 dark:text-white text-sm">AI Generation</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Agents work together to design spaces
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                3
              </div>
              <div>
                <h3 className="font-medium text-gray-800 dark:text-white text-sm">IFC Export</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Professional IFC file generated
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                4
              </div>
              <div>
                <h3 className="font-medium text-gray-800 dark:text-white text-sm">3D Render</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Beautiful visualization created
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

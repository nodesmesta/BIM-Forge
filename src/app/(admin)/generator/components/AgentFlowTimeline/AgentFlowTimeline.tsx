"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Task } from "@/types/task";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace("http://", "ws://").replace("https://", "wss://");

// Define the standard agent flow
export const AGENT_FLOW = [
  {
    name: "EnvironmentAgent",
    icon: "🌍",
    description: "Analyze location & climate",
    color: "from-emerald-500 to-teal-600",
    bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
    borderColor: "border-emerald-300 dark:border-emerald-700",
  },
  {
    name: "ArchitectAgent",
    icon: "📐",
    description: "Generate building blueprint",
    color: "from-blue-500 to-indigo-600",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-300 dark:border-blue-700",
  },
  {
    name: "SpaceAgent",
    icon: "🏠",
    description: "Design rooms & spaces",
    color: "from-purple-500 to-violet-600",
    bgColor: "bg-purple-50 dark:bg-purple-900/20",
    borderColor: "border-purple-300 dark:border-purple-700",
  },
  {
    name: "CoordinatorAgent",
    icon: "🔧",
    description: "Merge & coordinate layout",
    color: "from-orange-500 to-amber-600",
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    borderColor: "border-orange-300 dark:border-orange-700",
  },
  {
    name: "IFCGeometryAgent",
    icon: "🏗️",
    description: "Create IFC model",
    color: "from-cyan-500 to-blue-600",
    bgColor: "bg-cyan-50 dark:bg-cyan-900/20",
    borderColor: "border-cyan-300 dark:border-cyan-700",
  },
  {
    name: "RenderAgent",
    icon: "🎨",
    description: "Render 3D visualization",
    color: "from-pink-500 to-rose-600",
    bgColor: "bg-pink-50 dark:bg-pink-900/20",
    borderColor: "border-pink-300 dark:border-pink-700",
  },
];

export interface AgentState {
  name: string;
  status: "pending" | "running" | "complete" | "failed" | "skipped";
  progress: number;
  currentAction?: string;
  message?: string;
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  error?: string;
  icon: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

interface AgentFlowTimelineProps {
  taskId?: string;
  task?: Task | null;
  className?: string;
  onAgentStateChange?: (agents: AgentState[]) => void;
  initialAgents?: AgentState[];
  compact?: boolean;
}

// Hook to manage WebSocket connection
function useAgentWebSocket(taskId: string | undefined, onAgentStateChange?: (agents: AgentState[]) => void) {
  const [agentStates, setAgentStates] = useState<AgentState[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const initializeAgents = useCallback(() => {
    const initialStates: AgentState[] = AGENT_FLOW.map((agent) => ({
      ...agent,
      status: "pending",
      progress: 0,
    }));
    setAgentStates(initialStates);
  }, []);

  const updateAgentState = useCallback(
    (
      agentName: string,
      update: Partial<AgentState>,
      eventType?: string
    ) => {
      setAgentStates((prev) => {
        const newStates = prev.map((agent) => {
          if (agent.name === agentName) {
            const updated = { ...agent, ...update };

            // Auto-set status based on event type
            if (eventType) {
              if (eventType === "agent_started" || eventType === "agent_progress") {
                if (updated.status !== "complete" && updated.status !== "failed") {
                  updated.status = "running";
                }
              }
            }
            return updated;
          }
          return agent;
        });

        // Check if previous agents should be marked complete
        const agentIndex = AGENT_FLOW.findIndex((a) => a.name === agentName);
        if (update.status === "running" && agentIndex > 0) {
          const prevAgentName = AGENT_FLOW[agentIndex - 1].name;
          return newStates.map((agent) => {
            if (
              agent.name === prevAgentName &&
              agent.status === "running"
            ) {
              return { ...agent, status: "complete", progress: 100 };
            }
            return agent;
          });
        }

        return newStates;
      });
      setLastUpdate(new Date());
    },
    []
  );

  const connectWebSocket = useCallback(
    (id: string) => {
      if (!id) return;

      // Clean up existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(`${WS_URL}/api/ws/${id}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[AgentFlow] WebSocket connected");
        setIsConnected(true);
        initializeAgents();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[AgentFlow] Received:", data.type, data);

          // Handle different event types
          if (data.type === "agent_started") {
            updateAgentState(data.agent_name, {
              status: "running",
              progress: data.progress || 0,
              currentAction: data.phase || "Starting...",
              message: data.message,
              startedAt: new Date().toISOString(),
            }, "agent_started");
          } else if (data.type === "agent_progress") {
            updateAgentState(data.agent_name, {
              status: "running",
              progress: data.progress || 0,
              currentAction: data.phase || data.message,
              message: data.message,
            }, "agent_progress");
          } else if (data.type === "agent_complete") {
            updateAgentState(data.agent_name, {
              status: "complete",
              progress: 100,
              completedAt: new Date().toISOString(),
              duration: data.duration,
              message: data.message || "Completed",
            }, "agent_complete");
          } else if (data.type === "agent_failed") {
            updateAgentState(data.agent_name, {
              status: "failed",
              error: data.error,
              message: `Error: ${data.error}`,
            }, "agent_failed");
          } else if (data.type === "connected") {
            // Initial connection - fetch current status via REST
            fetch(`${API_URL}/api/status/${id}`)
              .then((res) => res.json())
              .then((statusData) => {
                console.log("[AgentFlow] Fetched status:", statusData);
                // Update based on task status
                if (statusData.status === "completed") {
                  setAgentStates((prev) =>
                    prev.map((agent) => ({
                      ...agent,
                      status: "complete",
                      progress: 100,
                    }))
                  );
                } else if (statusData.status === "failed") {
                  setAgentStates((prev) =>
                    prev.map((agent) => ({
                      ...agent,
                      status: agent.status === "running" ? "failed" : agent.status,
                    }))
                  );
                }
              })
              .catch(console.error);
          }
        } catch (error) {
          console.error("[AgentFlow] Error parsing message:", error);
        }
      };

      ws.onclose = () => {
        console.log("[AgentFlow] WebSocket disconnected");
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (taskId) {
            connectWebSocket(taskId);
          }
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error("[AgentFlow] WebSocket error:", error);
      };
    },
    [initializeAgents, updateAgentState, taskId]
  );

  // Connect when taskId changes
  useEffect(() => {
    if (taskId) {
      connectWebSocket(taskId);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [taskId, connectWebSocket]);

  // Notify parent of state changes
  useEffect(() => {
    if (onAgentStateChange) {
      onAgentStateChange(agentStates);
    }
  }, [agentStates, onAgentStateChange]);

  return {
    agentStates,
    isConnected,
    lastUpdate,
    updateAgentState,
    setAgentStates,
  };
}

// SVG Connector Line Component
function ConnectorLine({
  isActive,
  isComplete,
}: {
  isActive: boolean;
  isComplete: boolean;
}) {
  return (
    <div className="relative w-12 h-0.5 mx-1 flex-shrink-0">
      {/* Background line */}
      <div className="absolute inset-0 bg-gray-300 dark:bg-gray-600" />

      {/* Animated progress line */}
      <div
        className={cn(
          "absolute inset-y-0 left-0 transition-all duration-500",
          isComplete && "bg-green-500",
          isActive && "bg-blue-500 animate-pulse"
        )}
        style={{
          width: isComplete || isActive ? "100%" : "0%",
        }}
      />

      {/* Arrow indicator */}
      <div
        className={cn(
          "absolute right-0 top-1/2 -translate-y-1/2 transition-all duration-300",
          (isActive || isComplete)
            ? "opacity-100 translate-x-0"
            : "opacity-0 translate-x-2"
        )}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className={cn(
            isComplete ? "text-green-500" : "text-blue-500"
          )}
        >
          <path
            d="M6 0L12 6L6 12"
            fill="currentColor"
          />
        </svg>
      </div>
    </div>
  );
}

// Agent Card Component
function AgentFlowCard({ agent, isLast, compact = false }: {
  agent: AgentState;
  isLast: boolean;
  compact?: boolean;
}) {
  const cardSize = compact ? "w-36 p-3" : "w-48 p-4";
  
  const statusColors = {
    pending: "bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600",
    running:
      "bg-blue-50 dark:bg-blue-900/30 border-blue-400 dark:border-blue-500 shadow-blue-200 dark:shadow-blue-900/50 shadow-lg",
    complete:
      "bg-green-50 dark:bg-green-900/30 border-green-400 dark:border-green-500",
    failed: "bg-red-50 dark:bg-red-900/30 border-red-400 dark:border-red-500",
    skipped: "bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600",
  };

  const statusIcons = {
    pending: "⏳",
    running: "⚡",
    complete: "✅",
    failed: "❌",
    skipped: "⏭️",
  };

  const statusTextColors = {
    pending: "text-gray-600 dark:text-gray-400",
    running: "text-blue-600 dark:text-blue-400",
    complete: "text-green-600 dark:text-green-400",
    failed: "text-red-600 dark:text-red-400",
    skipped: "text-gray-500 dark:text-gray-500",
  };

  return (
    <div className="flex items-start">
      <div
          className={cn(
            "relative flex flex-col items-center rounded-xl border-2 transition-all duration-300 flex-shrink-0",
            cardSize,
          statusColors[agent.status],
          agent.status === "running" && "scale-105"
        )}
      >
        {/* Status indicator dot */}
        <div
          className={cn(
            "absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-sm shadow-md",
            agent.status === "running" && "bg-blue-500 text-white animate-bounce",
            agent.status === "complete" && "bg-green-500 text-white",
            agent.status === "failed" && "bg-red-500 text-white",
            agent.status === "pending" && "bg-gray-400 text-white",
            agent.status === "skipped" && "bg-gray-500 text-white"
          )}
        >
          {agent.status === "running" ? (
            <div className="w-3 h-3 bg-white rounded-full animate-ping opacity-75" />
          ) : (
            statusIcons[agent.status]
          )}
        </div>

        {/* Agent Icon */}
        <div
          className={cn(
            "w-14 h-14 rounded-full flex items-center justify-center text-3xl mb-3 transition-transform duration-300",
            agent.status === "running" && "animate-bounce",
            agent.status === "complete" && "grayscale-0",
            agent.bgColor
          )}
        >
          {agent.icon}
        </div>

        {/* Agent Name */}
        <h3 className="font-semibold text-sm text-gray-800 dark:text-white text-center mb-1">
          {agent.name.replace("Agent", "")}
        </h3>

        {/* Agent Description */}
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center mb-3">
          {agent.description}
        </p>

        {/* Status Badge */}
        <div
          className={cn(
            "px-2 py-1 rounded-full text-xs font-medium capitalize mb-2",
            agent.status === "running" && "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300",
            agent.status === "complete" && "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300",
            agent.status === "failed" && "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300",
            agent.status === "pending" && "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300",
            agent.status === "skipped" && "bg-gray-100 dark:bg-gray-700 text-gray-500"
          )}
        >
          {agent.status === "running" ? "Working..." : agent.status}
        </div>

        {/* Progress Bar (only show when running) */}
        {agent.status === "running" && (
          <div className="w-full space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Progress</span>
              <span className="font-medium text-blue-600">{agent.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${agent.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Current Action (only show when running) */}
        {agent.status === "running" && agent.currentAction && (
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-2 text-center italic">
            {agent.currentAction}
          </p>
        )}

        {/* Duration (show when complete) */}
        {agent.status === "complete" && agent.duration && (
          <p className="text-xs text-green-600 dark:text-green-400 mt-2">
            ⏱️ {(agent.duration / 1000).toFixed(1)}s
          </p>
        )}

        {/* Error Message (show when failed) */}
        {agent.status === "failed" && (
          <p className="text-xs text-red-600 dark:text-red-400 mt-2 text-center max-w-full truncate">
            {agent.error || "Unknown error"}
          </p>
        )}
      </div>

      {/* Connector Line */}
      {!isLast && <ConnectorLine isActive={agent.status === "running"} isComplete={agent.status === "complete"} />}
    </div>
  );
}

// Main Timeline Component
export default function AgentFlowTimeline({
  taskId,
  task,
  className,
  onAgentStateChange,
  initialAgents,
  compact = false,
}: AgentFlowTimelineProps) {
  const { agentStates, isConnected, lastUpdate, setAgentStates } = useAgentWebSocket(taskId, onAgentStateChange);

  // Use initialAgents if provided (for external control)
  useEffect(() => {
    if (initialAgents && initialAgents.length > 0) {
      setAgentStates(initialAgents);
    }
  }, [initialAgents, setAgentStates]);

  // Override with task status if provided
  useEffect(() => {
    if (task && task.status) {
      // If task is completed, mark all as complete
      if (task.status === "completed") {
        setAgentStates((prev) =>
          prev.map((agent) => ({
            ...agent,
            status: "complete" as const,
            progress: 100,
          }))
        );
      } else if (task.status === "failed") {
        setAgentStates((prev) =>
          prev.map((agent) => ({
            ...agent,
            status: agent.status === "running" ? ("failed" as const) : agent.status,
          }))
        );
      }
    }
  }, [task?.status, setAgentStates]);

  // Calculate overall progress
  const completedCount = agentStates.filter((a) => a.status === "complete").length;
  const runningAgent = agentStates.find((a) => a.status === "running");
  const overallProgress =
    agentStates.length > 0
      ? Math.round(
          agentStates.reduce((sum, a) => sum + a.progress, 0) / agentStates.length
        )
      : 0;

  // Compact mode styles
  const containerClass = compact
    ? "bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4"
    : "bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-6";

  const headerClass = compact ? "mb-4" : "mb-6";
  const titleSize = compact ? "text-lg" : "text-xl";
  const cardSize = compact ? "w-36 p-3" : "w-48 p-4";

  return (
    <div className={cn(containerClass, className)}>
      {/* Header */}
      <div className={cn("flex items-center justify-between", headerClass)}>
        <div>
          <h2 className={cn("font-bold text-gray-800 dark:text-white", titleSize)}>
            Agent Workflow
          </h2>
          {!compact && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Real-time multi-agent processing status
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Connection Status */}
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
              isConnected
                ? "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
            )}
          >
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
              )}
            />
            {isConnected ? "Live" : "Disconnected"}
          </div>

          {/* Overall Progress */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 rounded-full">
            <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
              {overallProgress}%
            </span>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="flex gap-4 mb-6">
        <div className="flex items-center gap-2 text-sm">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-gray-600 dark:text-gray-400">
            Completed: <span className="font-medium text-green-600 dark:text-green-400">{completedCount}</span>
          </span>
        </div>
        {runningAgent && (
          <div className="flex items-center gap-2 text-sm">
            <span className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-gray-600 dark:text-gray-400">
              Running: <span className="font-medium text-blue-600 dark:text-blue-400">{runningAgent.name}</span>
            </span>
          </div>
        )}
        <div className="flex items-center gap-2 text-sm">
          <span className="w-3 h-3 rounded-full bg-gray-400" />
          <span className="text-gray-600 dark:text-gray-400">
            Pending: <span className="font-medium">{agentStates.length - completedCount - (runningAgent ? 1 : 0)}</span>
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative overflow-x-auto pb-4">
        {/* Horizontal scroll container */}
        <div className="flex items-start gap-0 min-w-max px-4">
          {agentStates.map((agent, index) => (
            <AgentFlowCard
              key={agent.name}
              agent={agent}
              isLast={index === agentStates.length - 1}
              compact={compact}
            />
          ))}
        </div>
      </div>

      {/* Last Update Time */}
      {lastUpdate && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Last update: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
      )}

      {/* Currently Running Action */}
      {runningAgent && runningAgent.currentAction && (
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-sm text-blue-700 dark:text-blue-300">
              {runningAgent.icon} {runningAgent.currentAction}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// Animation keyframes are defined in Tailwind config or inline styles
// Using inline style for the pulse-subtle animation
const pulseSubtleStyle = `
  @keyframes pulse-subtle {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.02); }
  }
`;

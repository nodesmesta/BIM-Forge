"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Task } from "@/types/task";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace("http://", "ws://").replace("https://", "wss://");

// Main pipeline phases with detailed information
export const PIPELINE_PHASES = [
  {
    id: "environment",
    name: "Environment",
    icon: "🌍",
    description: "Climate & Location Analysis",
    color: "emerald",
    bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
    borderColor: "border-emerald-300 dark:border-emerald-700",
    agents: ["EnvironmentAgent"],
    estimatedTime: "2-5s"
  },
  {
    id: "architecture",
    name: "Architecture",
    icon: "📐",
    description: "Building Blueprint & Layout",
    color: "blue",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-300 dark:border-blue-700",
    agents: ["ArchitectAgent", "CoordinatorAgent"],
    estimatedTime: "10-30s"
  },
  {
    id: "spaces",
    name: "Space Design",
    icon: "🏠",
    description: "Room & Interior Design",
    color: "purple",
    bgColor: "bg-purple-50 dark:bg-purple-900/20",
    borderColor: "border-purple-300 dark:border-purple-700",
    agents: [], // Dynamic - populated when space agents are spawned
    estimatedTime: "15-60s"
  },
  {
    id: "geometry",
    name: "IFC Geometry",
    icon: "🏗️",
    description: "3D Model Generation",
    color: "cyan",
    bgColor: "bg-cyan-50 dark:bg-cyan-900/20",
    borderColor: "border-cyan-300 dark:border-cyan-700",
    agents: ["IFCGeometryAgent"],
    estimatedTime: "10-20s"
  },
  {
    id: "rendering",
    name: "Rendering",
    icon: "🎨",
    description: "Visualization Output",
    color: "pink",
    bgColor: "bg-pink-50 dark:bg-pink-900/20",
    borderColor: "border-pink-300 dark:border-pink-700",
    agents: ["RenderAgent"],
    estimatedTime: "30-120s"
  },
];

export interface SpaceAgentInfo {
  name: string;
  type: string;
  floor: number;
  status: "pending" | "running" | "complete" | "failed" | "skipped";
  progress: number;
  currentAction?: string;
}

export interface PhaseState {
  id: string;
  status: "pending" | "running" | "complete" | "failed" | "skipped";
  progress: number;
  currentAgent?: string;
  currentAction?: string;
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  agents: string[];
  spaceAgents: SpaceAgentInfo[];
  message?: string;
  error?: string;
}

interface PipelineVisualizerProps {
  taskId?: string;
  task?: Task | null;
  className?: string;
  onPhaseChange?: (phases: PhaseState[]) => void;
}

function usePipelineWebSocket(taskId: string | undefined) {
  const [phases, setPhases] = useState<PhaseState[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize phases from pipeline definition
  const initializePhases = useCallback(() => {
    const initialPhases: PhaseState[] = PIPELINE_PHASES.map((phase) => ({
      id: phase.id,
      status: "pending",
      progress: 0,
      agents: phase.agents,
      spaceAgents: [],
    }));
    setPhases(initialPhases);
  }, []);

  // Update specific phase or agent
  const updatePhaseState = useCallback(
    (phaseId: string, update: Partial<PhaseState>, agentName?: string) => {
      setPhases((prev) => {
        const newPhases = [...prev];
        const phaseIndex = newPhases.findIndex((p) => p.id === phaseId);
        
        if (phaseIndex === -1) return prev;

        const phase = { ...newPhases[phaseIndex] };

        // Update phase state
        if (update.status) phase.status = update.status;
        if (update.progress !== undefined) phase.progress = update.progress;
        if (update.currentAgent) phase.currentAgent = update.currentAgent;
        if (update.currentAction) phase.currentAction = update.currentAction;
        if (update.startedAt) phase.startedAt = update.startedAt;
        if (update.completedAt) phase.completedAt = update.completedAt;
        if (update.duration !== undefined) phase.duration = update.duration;
        if (update.message) phase.message = update.message;
        if (update.error) phase.error = update.error;
        if (update.agents) phase.agents = update.agents;
        if (update.spaceAgents) phase.spaceAgents = update.spaceAgents;

        // Update phase status based on agent completion
        if (update.status === "running" && phase.status !== "running") {
          phase.status = "running";
          phase.startedAt = new Date().toISOString();
        }

        // If main agents complete, check space agents
        if (phase.agents.length > 0 && phase.agents.includes(agentName || "")) {
          if (update.status === "complete") {
            // Check if all agents in phase are done
            const allComplete = phase.agents.every(a => 
              a === agentName || phase.spaceAgents.some(sa => sa.name === a && sa.status === "complete")
            );
            if (allComplete) {
              phase.status = "complete";
              phase.progress = 100;
              phase.completedAt = new Date().toISOString();
            }
          }
        }

        newPhases[phaseIndex] = phase;
        return newPhases;
      });
      setLastUpdate(new Date());
    },
    []
  );

  // Handle space agents spawning
  const handleSpaceAgentsSpawned = useCallback((spaceAgents: Array<{name: string, type: string, floor: number}>) => {
    setPhases((prev) => {
      const newPhases = [...prev];
      const spacePhase = newPhases.find(p => p.id === "spaces");
      
      if (spacePhase) {
        const newSpaceAgents: SpaceAgentInfo[] = spaceAgents.map(sa => ({
          name: sa.name,
          type: sa.type,
          floor: sa.floor,
          status: "pending",
          progress: 0,
        }));
        spacePhase.spaceAgents = [...spacePhase.spaceAgents, ...newSpaceAgents];
      }
      
      return newPhases;
    });
  }, []);

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
        console.log("[Pipeline] WebSocket connected");
        setIsConnected(true);
        initializePhases();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[Pipeline] Event:", data.type, data);

          // Map agent to phase
          const agentToPhase: Record<string, string> = {
            EnvironmentAgent: "environment",
            ArchitectAgent: "architecture",
            CoordinatorAgent: "architecture",
            IFCGeometryAgent: "geometry",
            RenderAgent: "rendering",
          };

          const phaseId = agentToPhase[data.agent_name];

          if (data.type === "agent_started") {
            if (phaseId) {
              updatePhaseState(phaseId, {
                status: "running",
                progress: data.progress || 10,
                currentAgent: data.agent_name,
                currentAction: data.phase || "Starting...",
                startedAt: new Date().toISOString(),
              }, data.agent_name);
            }
          } else if (data.type === "agent_progress") {
            if (phaseId) {
              updatePhaseState(phaseId, {
                progress: data.progress || 0,
                currentAction: data.phase || data.message,
                message: data.message,
              }, data.agent_name);
            }
          } else if (data.type === "agent_complete") {
            if (phaseId) {
              const duration = data.duration ? data.duration * 1000 : undefined;
              updatePhaseState(phaseId, {
                status: "complete",
                progress: 100,
                completedAt: new Date().toISOString(),
                duration,
                message: data.message || "Completed",
              }, data.agent_name);
            }
          } else if (data.type === "agent_failed") {
            if (phaseId) {
              updatePhaseState(phaseId, {
                status: "failed",
                error: data.error,
                message: `Error: ${data.error}`,
              }, data.agent_name);
            }
          } else if (data.type === "connected") {
            // Fetch current status
            fetch(`${API_URL}/api/status/${id}`)
              .then((res) => res.json())
              .then((statusData) => {
                console.log("[Pipeline] Status:", statusData);
                // Could map status to phases here
              })
              .catch(console.error);
          }
        } catch (error) {
          console.error("[Pipeline] Error:", error);
        }
      };

      ws.onclose = () => {
        console.log("[Pipeline] WebSocket disconnected");
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(() => {
          if (taskId) connectWebSocket(taskId);
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error("[Pipeline] WebSocket error:", error);
      };
    },
    [initializePhases, updatePhaseState, taskId]
  );

  useEffect(() => {
    if (taskId) {
      connectWebSocket(taskId);
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [taskId, connectWebSocket]);

  return { phases, isConnected, lastUpdate };
}

// Phase Card Component
function PhaseCard({ phase, isLast }: { phase: PhaseState; isLast: boolean }) {
  const phaseConfig = PIPELINE_PHASES.find(p => p.id === phase.id);
  const color = phaseConfig?.color || "gray";
  const bgColor = phaseConfig?.bgColor || "bg-gray-50";
  const borderColor = phaseConfig?.borderColor || "border-gray-300";
  const icon = phaseConfig?.icon || "⚙️";
  const name = phaseConfig?.name || phase.id;
  const description = phaseConfig?.description || "";

  const statusStyles = {
    pending: "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50",
    running: `border-${color}-400 dark:border-${color}-500 ${bgColor}`,
    complete: `border-green-400 dark:border-green-500 bg-green-50 dark:bg-green-900/20`,
    failed: "border-red-400 dark:border-red-500 bg-red-50 dark:bg-red-900/20",
    skipped: "border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-800",
  };

  const statusIndicatorColors = {
    pending: "bg-gray-400",
    running: "bg-blue-500 animate-pulse",
    complete: "bg-green-500",
    failed: "bg-red-500",
    skipped: "bg-gray-500",
  };

  return (
    <div className="flex items-start">
      <div
        className={cn(
          "relative flex flex-col rounded-xl border-2 transition-all duration-500 w-72 flex-shrink-0",
          statusStyles[phase.status]
        )}
      >
        {/* Status indicator */}
        <div
          className={cn(
            "absolute -top-3 -right-3 w-8 h-8 rounded-full flex items-center justify-center text-lg shadow-lg",
            statusIndicatorColors[phase.status]
          )}
        >
          {phase.status === "running" ? (
            <div className="w-4 h-4 bg-white rounded-full animate-ping opacity-75" />
          ) : phase.status === "complete" ? (
            "✅"
          ) : phase.status === "failed" ? (
            "❌"
          ) : phase.status === "pending" ? (
            "⏳"
          ) : (
            "⏭️"
          )}
        </div>

        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center text-2xl",
                bgColor
              )}
            >
              {icon}
            </div>
            <div>
              <h3 className="font-bold text-gray-800 dark:text-white">{name}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Current Agent */}
          {phase.currentAgent && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">Running:</span>
              <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                {phase.currentAgent.replace("Agent", "")}
              </span>
            </div>
          )}

          {/* Current Action */}
          {phase.currentAction && (
            <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
              <p className="text-xs text-blue-600 dark:text-blue-400 italic">
                {phase.currentAction}
              </p>
            </div>
          )}

          {/* Progress Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500 dark:text-gray-400">Progress</span>
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {phase.progress}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={cn(
                  "h-2 rounded-full transition-all duration-500",
                  phase.status === "complete" ? "bg-green-500" :
                  phase.status === "failed" ? "bg-red-500" :
                  "bg-blue-500"
                )}
                style={{ width: `${phase.progress}%` }}
              />
            </div>
          </div>

          {/* Space Agents (for spaces phase) */}
          {phase.spaceAgents.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
                Space Agents ({phase.spaceAgents.length})
              </p>
              <div className="flex flex-wrap gap-1">
                {phase.spaceAgents.map((sa, idx) => (
                  <span
                    key={idx}
                    className={cn(
                      "px-2 py-1 rounded text-xs",
                      sa.status === "complete" && "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300",
                      sa.status === "running" && "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300",
                      sa.status === "pending" && "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300",
                      sa.status === "failed" && "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300"
                    )}
                    title={`${sa.type} - Floor ${sa.floor}`}
                  >
                    {sa.type}#{sa.floor}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Duration */}
          {phase.duration && (
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span>⏱️</span>
              <span>{(phase.duration / 1000).toFixed(1)}s</span>
            </div>
          )}

          {/* Error */}
          {phase.error && (
            <div className="p-2 bg-red-50 dark:bg-red-900/30 rounded-lg">
              <p className="text-xs text-red-600 dark:text-red-400">
                {phase.error}
              </p>
            </div>
          )}

          {/* Message */}
          {phase.message && !phase.error && phase.status === "complete" && (
            <p className="text-xs text-green-600 dark:text-green-400">
              ✓ {phase.message}
            </p>
          )}
        </div>

        {/* Footer - Agents list */}
        {phase.agents.length > 0 && (
          <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Agents: {phase.agents.map(a => a.replace("Agent", "")).join(", ")}
            </p>
          </div>
        )}
      </div>

      {/* Connector */}
      {!isLast && (
        <div className="relative w-16 h-0.5 mx-2 mt-6 flex-shrink-0">
          <div className="absolute inset-0 bg-gray-300 dark:bg-gray-600" />
          <div
            className={cn(
              "absolute inset-y-0 left-0 transition-all duration-500",
              phase.status === "complete" && "bg-green-500",
              phase.status === "running" && "bg-blue-500 animate-pulse"
            )}
            style={{ width: phase.status === "complete" || phase.status === "running" ? "100%" : "0%" }}
          />
          <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 8H12M12 8L8 4M12 8L8 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}

// Main Pipeline Component
export default function PipelineVisualizer({
  taskId,
  task,
  className,
  onPhaseChange,
}: PipelineVisualizerProps) {
  const { phases, isConnected, lastUpdate } = usePipelineWebSocket(taskId);

  // Notify parent of changes
  useEffect(() => {
    if (onPhaseChange && phases.length > 0) {
      onPhaseChange(phases);
    }
  }, [phases, onPhaseChange]);

  // Calculate overall progress
  const completedPhases = phases.filter((p) => p.status === "complete").length;
  const runningPhase = phases.find((p) => p.status === "running");
  const totalSpaceAgents = phases.reduce((sum, p) => sum + p.spaceAgents.length, 0);
  const overallProgress = phases.length > 0
    ? Math.round(phases.reduce((sum, p) => sum + p.progress, 0) / phases.length)
    : 0;

  return (
    <div className={cn("bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800 dark:text-white">
            Pipeline Visualization
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Real-time multi-phase processing with detailed agent tracking
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Space Agents Count */}
          {totalSpaceAgents > 0 && (
            <div className="px-3 py-1.5 bg-purple-50 dark:bg-purple-900/30 rounded-full">
              <span className="text-sm font-medium text-purple-600 dark:text-purple-400">
                {totalSpaceAgents} Space Agents
              </span>
            </div>
          )}

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
          <div className="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 rounded-full">
            <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
              {overallProgress}%
            </span>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-6 mb-6 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Completed: <span className="font-medium text-green-600 dark:text-green-400">{completedPhases}</span>
          </span>
        </div>
        {runningPhase && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Running: <span className="font-medium text-blue-600 dark:text-blue-400">{runningPhase.currentAgent || PIPELINE_PHASES.find(p => p.id === runningPhase.id)?.name}</span>
            </span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-gray-400" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Pending: <span className="font-medium text-gray-600 dark:text-gray-400">{phases.length - completedPhases - (runningPhase ? 1 : 0)}</span>
          </span>
        </div>
        {totalSpaceAgents > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-purple-500" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Space Agents: <span className="font-medium text-purple-600 dark:text-purple-400">{totalSpaceAgents}</span>
            </span>
          </div>
        )}
      </div>

      {/* Pipeline Flow */}
      <div className="overflow-x-auto pb-4">
        <div className="flex items-start gap-2 min-w-max">
          {phases.map((phase, index) => (
            <PhaseCard
              key={phase.id}
              phase={phase}
              isLast={index === phases.length - 1}
            />
          ))}
        </div>
      </div>

      {/* Last Update */}
      {lastUpdate && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            Last update: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  );
}
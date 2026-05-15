"use client";

import { Task } from "@/types/task";

interface AgentProgress {
  name: string;
  status: "pending" | "running" | "complete" | "failed";
  progress: number;
  currentAction?: string;
}

interface AgentProgressDisplayProps {
  task: Task;
}

const agentConfigs: Record<string, { icon: string; defaultProgress: number; actions: string[] }> = {
  EnvironmentAgent: {
    icon: "🌍",
    defaultProgress: 15,
    actions: ["Extracting location...", "Analyzing climate...", "Calculating sun path...", "Generating recommendations..."]
  },
  ArchitectAgent: {
    icon: "📐",
    defaultProgress: 30,
    actions: ["Parsing prompt...", "Spawning agents...", "Generating space designs...", "Merging designs..."]
  },
  BedroomAgent: {
    icon: "🛏️",
    defaultProgress: 25,
    actions: ["Calling LLM...", "Generating dimensions...", "Designing furniture...", "Selecting materials..."]
  },
  BathroomAgent: {
    icon: "🚿",
    defaultProgress: 25,
    actions: ["Calling LLM...", "Designing fixtures...", "Selecting materials...", "Planning ventilation..."]
  },
  KitchenAgent: {
    icon: "🍳",
    defaultProgress: 25,
    actions: ["Calling LLM...", "Designing layout...", "Selecting appliances...", "Planning MEP..."]
  },
  LivingRoomAgent: {
    icon: "🛋️",
    defaultProgress: 25,
    actions: ["Calling LLM...", "Designing space...", "Selecting furniture...", "Planning lighting..."]
  },
  CoordinatorAgent: {
    icon: "🔧",
    defaultProgress: 40,
    actions: ["Collecting designs...", "Grouping by floor...", "Arranging spaces...", "Generating walls...", "Placing doors/windows..."]
  },
  IFCGeometryAgent: {
    icon: "🏗️",
    defaultProgress: 50,
    actions: ["Creating IFC file...", "Building geometry...", "Adding elements...", "Writing file..."]
  },
  RenderAgent: {
    icon: "🎨",
    defaultProgress: 60,
    actions: ["Loading IFC...", "Setting up Blender...", "Rendering...", "Generating thumbnail..."]
  }
};

export default function AgentProgressDisplay({ task }: AgentProgressDisplayProps) {
  const getAgentsForTask = (): AgentProgress[] => {
    const agents: AgentProgress[] = [];

    // Determine which agents are active based on task status
    const status = task.status;
    const progress = task.progress || 0;

    // EnvironmentAgent (always first, 0-10%)
    if (progress > 0) {
      agents.push({
        name: "EnvironmentAgent",
        status: progress >= 10 ? "complete" : progress > 0 ? "running" : "pending",
        progress: Math.min(progress * 1.5, 100),
        currentAction: progress > 0 ? agentConfigs.EnvironmentAgent.actions[Math.floor(progress / 3.5) % agentConfigs.EnvironmentAgent.actions.length] : "Waiting..."
      });
    }

    // ArchitectAgent (10-30%)
    if (progress >= 10) {
      const architectProgress = Math.min((progress - 10) * 2, 100);
      agents.push({
        name: "ArchitectAgent",
        status: progress >= 30 ? "complete" : progress > 10 ? "running" : "pending",
        progress: architectProgress,
        currentAction: progress > 10 ? agentConfigs.ArchitectAgent.actions[Math.floor((progress - 10) / 0.5) % agentConfigs.ArchitectAgent.actions.length] : "Waiting..."
      });
    }

    // Space Agents (20-50%) - shown during ArchitectAgent phase
    if (progress >= 15) {
      const spaceAgents = ["BedroomAgent", "BathroomAgent", "KitchenAgent", "LivingRoomAgent"];
      const spaceProgress = Math.min((progress - 15) * 2.5, 100);

      spaceAgents.forEach(agent => {
        if (progress >= 20) {
          agents.push({
            name: agent,
            status: progress >= 40 ? "complete" : progress > 15 ? "running" : "pending",
            progress: progress >= 40 ? 100 : spaceProgress,
            currentAction: progress > 15 ? agentConfigs[agent].actions[Math.floor(spaceProgress / 25) % agentConfigs[agent].actions.length] : "Waiting..."
          });
        }
      });
    }

    // CoordinatorAgent (50-75%)
    if (progress >= 50) {
      const coordinatorProgress = Math.min((progress - 50) * 4, 100);
      agents.push({
        name: "CoordinatorAgent",
        status: progress >= 75 ? "complete" : progress > 50 ? "running" : "pending",
        progress: coordinatorProgress,
        currentAction: progress > 50 ? agentConfigs.CoordinatorAgent.actions[Math.floor((progress - 50) / 0.625) % agentConfigs.CoordinatorAgent.actions.length] : "Waiting..."
      });
    }

    // IFCGeometryAgent (75-90%)
    if (progress >= 75) {
      const ifcProgress = Math.min((progress - 75) * 6.67, 100);
      agents.push({
        name: "IFCGeometryAgent",
        status: progress >= 90 ? "complete" : progress > 75 ? "running" : "pending",
        progress: ifcProgress,
        currentAction: progress > 75 ? agentConfigs.IFCGeometryAgent.actions[Math.floor((progress - 75) / 0.225) % agentConfigs.IFCGeometryAgent.actions.length] : "Waiting..."
      });
    }

    // RenderAgent (90-100%)
    if (progress >= 90) {
      const renderProgress = Math.min((progress - 90) * 10, 100);
      agents.push({
        name: "RenderAgent",
        status: progress >= 100 ? "complete" : progress > 90 ? "running" : "pending",
        progress: renderProgress,
        currentAction: progress > 90 ? agentConfigs.RenderAgent.actions[Math.floor((progress - 90) / 0.1) % agentConfigs.RenderAgent.actions.length] : "Waiting..."
      });
    }

    return agents;
  };

  const agents = getAgentsForTask();

  if (agents.length === 0) {
    return null;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "complete": return "bg-green-500";
      case "running": return "bg-blue-500 animate-pulse";
      case "failed": return "bg-red-500";
      default: return "bg-gray-400";
    }
  };

  const getIconContainerClass = (status: string) => {
    switch (status) {
      case "complete": return "bg-green-100 dark:bg-green-900/30";
      case "running": return "bg-blue-100 dark:bg-blue-900/30";
      case "failed": return "bg-red-100 dark:bg-red-900/30";
      default: return "bg-gray-100 dark:bg-gray-800";
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-6 mt-6">
      <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
        Agent Progress Details
      </h2>

      <div className="space-y-4">
        {agents.map((agent, index) => (
          <div key={agent.name} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${getIconContainerClass(agent.status)}`}>
                {agentConfigs[agent.name]?.icon || "📦"}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-800 dark:text-white">
                    {agent.name}
                  </h3>
                  <span className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} />
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {agent.currentAction}
                </p>
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {Math.round(agent.progress)}%
              </span>
            </div>

            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  agent.status === "complete" ? "bg-green-500" :
                  agent.status === "running" ? "bg-blue-500" :
                  agent.status === "failed" ? "bg-red-500" : "bg-gray-400"
                }`}
                style={{ width: `${agent.progress}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">
            Active Agents: {agents.filter(a => a.status === "running").length}
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            Completed: {agents.filter(a => a.status === "complete").length}
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            Total: {agents.length}
          </span>
        </div>
      </div>
    </div>
  );
}

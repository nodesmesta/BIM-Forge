"use client";

import { useState } from "react";
import StructuredForm from "./StructuredForm";
import ChatInterface from "./ChatInterface";
import ClaudeTaskGenerator from "./ClaudeTaskGenerator";
import StatusTracker from "./StatusTracker";
import AgentProgressDisplay from "./AgentProgressDisplay";
import RenderPreview from "./RenderPreview";
import { AgentFlowTimeline } from "./AgentFlowTimeline";
import { Task } from "@/types/task";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function IntegratedGenerator() {
  const [specification, setSpecification] = useState<any>(null);
  const [task, setTask] = useState<Task | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [inputMode, setInputMode] = useState<"chat" | "form">("chat");

  const handleSpecificationSubmit = (spec: any) => {
    setSpecification(spec);
  };

  const handleProgressUpdate = (updatedTask: Task) => {
    setTask(updatedTask);

    // Check if task is complete
    if (updatedTask.status === "completed" || updatedTask.status === "failed") {
      setIsGenerating(false);
    }
  };

  
  const renderUrl = task?.result?.render_path
    ? `${API_URL}${task.result.render_path}`
    : null;

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Building Generator
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Describe your building in natural language or use structured form
        </p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Input & Task Management */}
        <div className="space-y-6">
          {/* Tab Switcher: Chat vs Form */}
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setInputMode("chat")}
              className={cn(
                "flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors",
                inputMode === "chat"
                  ? "bg-white dark:bg-gray-700 text-blue-600 shadow"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
              )}
            >
              💬 Chat
            </button>
            <button
              onClick={() => setInputMode("form")}
              className={cn(
                "flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors",
                inputMode === "form"
                  ? "bg-white dark:bg-gray-700 text-blue-600 shadow"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
              )}
            >
              📋 Form
            </button>
          </div>

          {/* Input Based on Mode */}
          {inputMode === "chat" ? (
            <ChatInterface onGenerate={handleSpecificationSubmit} />
          ) : (
            <StructuredForm
              onGenerate={handleSpecificationSubmit}
              isGenerating={isGenerating}
            />
          )}

          {/* Task Generator (automatically triggered when specification is set) */}
          {specification && (
            <ClaudeTaskGenerator
              specification={specification}
              onTaskUpdate={handleProgressUpdate}
            />
          )}

          {/* Agent Flow Timeline (Real-time workflow visualization) */}
          {task && (
            <AgentFlowTimeline taskId={task.id} task={task} />
          )}

          {/* Status Trackers */}
          {task && (
            <>
              <StatusTracker task={task} />
              <AgentProgressDisplay task={task} />
            </>
          )}
        </div>

        {/* Right Column - Preview */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-6">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
            Render Preview
          </h2>
          <RenderPreview
            task={task}
            renderUrl={renderUrl}
            isGenerating={isGenerating}
          />

          {/* Task Details */}
          {task && (
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-3">
                Task Details
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Task ID:</span>
                  <span className="font-mono">{task.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Created:</span>
                  <span>{task.created_at ? new Date(task.created_at).toLocaleString() : "N/A"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Status:</span>
                  <span className="capitalize">{task.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Progress:</span>
                  <span>{task.progress}%</span>
                </div>
                {task.error_message && (
                  <div className="flex justify-between text-red-600">
                    <span>Error:</span>
                    <span>{task.error_message}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Efficiency Analysis */}
      {specification && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-6">
          <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-4">
            Specification Analysis
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">
                {specification.rooms?.length || 0}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Room Types</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {specification.floors?.length || 1}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Floors</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">
                {specification.site?.building_footprint_m2 || 0}m²
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Footprint</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">
                {specification.style || "Modern"}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Style</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
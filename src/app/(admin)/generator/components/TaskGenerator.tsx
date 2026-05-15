"use client";

import { useState, useEffect, useRef } from "react";
import { Task } from "@/types/task";

interface TaskGeneratorProps {
  specification: any;
  onTaskCreated: (task: Task) => void;
  onProgressUpdate: (task: Task) => void;
  onError: (error: string) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace("http://", "ws://").replace("https://", "wss://");

export default function TaskGenerator({
  specification,
  onTaskCreated,
  onProgressUpdate,
  onError,
}: TaskGeneratorProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentTask, setCurrentTask] = useState<Task | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Connect to WebSocket for a task
  const connectWebSocket = (taskId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `${WS_URL}/api/ws/${taskId}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log(`WebSocket connected for task ${taskId}`);
    };

    wsRef.current.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data);

        // Update task state
        setCurrentTask((prev) => {
          if (!prev) return null;

          const updatedTask: Task = {
            ...prev,
            status: update.status || prev.status,
            progress: update.progress !== undefined ? update.progress : prev.progress,
            result: update.result || prev.result,
            error_message: update.error || prev.error_message,
            workflow_status: update.workflow_status || prev.workflow_status,
          };

          // Use setTimeout to avoid React warning about setState during render
          setTimeout(() => {
            onProgressUpdate(updatedTask);
          }, 0);

          return updatedTask;
        });
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      onError("WebSocket connection error");
    };

    wsRef.current.onclose = () => {
      console.log("WebSocket closed");
    };
  };

  const generateTask = async () => {
    if (!specification) {
      onError("No specification provided");
      return;
    }

    setIsGenerating(true);

    // Create initial task object
    const initialTask: Task = {
      id: `task_${Date.now()}`,
      prompt: specification.project_name || "Building Project",
      status: "pending",
      progress: 0,
      created_at: new Date().toISOString(),
    };

    setCurrentTask(initialTask);
    onTaskCreated(initialTask);

    try {
      // Send request to backend
      const response = await fetch(`${API_URL}/api/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: JSON.stringify(specification),
          is_structured: true,
          specification: specification,
          priority: 1,
          max_revisions: 3,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const taskId = data.task_id;

      // Update task with real ID from backend
      const updatedTask: Task = {
        ...initialTask,
        id: taskId,
      };

      setCurrentTask(updatedTask);

      // Connect to WebSocket for real-time updates
      connectWebSocket(taskId);

    } catch (error) {
      console.error("Error generating task:", error);

      const errorTask: Task = {
        ...initialTask,
        status: "failed",
        error_message: error instanceof Error ? error.message : "Unknown error",
      };

      setCurrentTask(errorTask);
      onError(`Failed to generate task: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const cancelTask = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    if (currentTask) {
      const cancelledTask: Task = {
        ...currentTask,
        status: "failed",
        error_message: "Cancelled by user",
      };

      setCurrentTask(cancelledTask);
      onProgressUpdate(cancelledTask);
    }

    setIsGenerating(false);
  };

  // Generate task automatically when specification changes
  useEffect(() => {
    if (specification) {
      generateTask();
    }
  }, [specification]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-800 dark:text-white">
            Task Generator
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {currentTask ? `Task ID: ${currentTask.id}` : "Ready to generate"}
          </p>
        </div>

        <div className="flex space-x-2">
          {!isGenerating && !currentTask && (
            <button
              onClick={generateTask}
              disabled={!specification}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              Generate Task
            </button>
          )}

          {isGenerating && (
            <button
              onClick={cancelTask}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Status display */}
      {currentTask && (
        <div className="border rounded-lg p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Status</p>
              <p className="font-medium capitalize">{currentTask.status}</p>
            </div>

            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Progress</p>
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${currentTask.progress}%` }}
                  />
                </div>
                <span className="text-sm font-medium">{currentTask.progress}%</span>
              </div>
            </div>

            {currentTask.error_message && (
              <div className="col-span-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">Error</p>
                <p className="text-red-600 text-sm">{currentTask.error_message}</p>
              </div>
            )}

            {currentTask.result && (
              <div className="col-span-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">Results</p>
                <div className="text-sm space-y-1">
                  {currentTask.result.render_path && (
                    <p>Render: {currentTask.result.render_path}</p>
                  )}
                  {currentTask.result.ifc_path && (
                    <p>IFC: {currentTask.result.ifc_path}</p>
                  )}
                  {currentTask.result.thumbnail_path && (
                    <p>Thumbnail: {currentTask.result.thumbnail_path}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
"use client";

import { useState, useEffect, useRef } from "react";
import { Task } from "@/types/task";

interface ClaudeTaskGeneratorProps {
  specification: any;
  onTaskUpdate: (task: Task) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace("http://", "ws://").replace("https://", "wss://");

export default function ClaudeTaskGenerator({
  specification,
  onTaskUpdate,
}: ClaudeTaskGeneratorProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [task, setTask] = useState<Task | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Sync task state to parent using useEffect (unidirectional flow)
  useEffect(() => {
    if (task) {
      onTaskUpdate(task);
    }
  }, [task, onTaskUpdate]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Connect to WebSocket - pure connection logic only
  const connectWebSocket = (taskId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `${WS_URL}/api/ws/${taskId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      // Connection successful - happy path
    };

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);

      setTask((prev) => {
        if (!prev) return null;

        return {
          ...prev,
          status: update.status || prev.status,
          progress: update.progress !== undefined ? update.progress : prev.progress,
          result: update.result || prev.result,
          error_message: update.error || prev.error_message,
          workflow_status: update.workflow_status || prev.workflow_status,
        };
      });
    };
  };

  const generateTask = async () => {
    setIsGenerating(true);

    const initialTask: Task = {
      id: `task_${Date.now()}`,
      prompt: specification.project_name || "Building Project",
      status: "pending",
      progress: 0,
      created_at: new Date().toISOString(),
    };

    setTask(initialTask);

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

    const data = await response.json();
    const taskId = data.task_id;

    const updatedTask: Task = {
      ...initialTask,
      id: taskId,
    };

    setTask(updatedTask);
    connectWebSocket(taskId);
    setIsGenerating(false);
  };

  // Generate when specification is provided
  useEffect(() => {
    if (specification && !isGenerating && !task) {
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
            {task ? `Task ID: ${task.id}` : "Ready to generate"}
          </p>
        </div>

        {!isGenerating && !task && (
          <button
            onClick={generateTask}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Generate Task
          </button>
        )}
      </div>

      {task && (
        <div className="border rounded-lg p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Status</p>
              <p className="font-medium capitalize">{task.status}</p>
            </div>

            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Progress</p>
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                <span className="text-sm font-medium">{task.progress}%</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
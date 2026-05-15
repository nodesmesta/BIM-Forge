"use client";

import { Task } from "@/types/task";

interface StatusTrackerProps {
  task: Task;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "bg-gray-500" },
  spec_generating: { label: "Generating Specification...", color: "bg-blue-500" },
  spec_complete: { label: "Specification Complete", color: "bg-cyan-500" },
  ifc_generating: { label: "Creating IFC Model...", color: "bg-purple-500" },
  ifc_complete: { label: "IFC Model Complete", color: "bg-indigo-500" },
  rendering: { label: "Rendering Image...", color: "bg-pink-500" },
  completed: { label: "Completed", color: "bg-green-500" },
  failed: { label: "Failed", color: "bg-red-500" },
};

export default function StatusTracker({ task }: StatusTrackerProps) {
  const statusInfo = statusLabels[task.status] || {
    label: task.status,
    color: "bg-gray-500",
  };

  const steps = [
    { key: "pending", label: "Queued" },
    { key: "spec_generating", label: "Spec" },
    { key: "ifc_generating", label: "IFC" },
    { key: "rendering", label: "Render" },
    { key: "completed", label: "Done" },
  ];

  const getCurrentStepIndex = () => {
    const currentKeys = Object.keys(statusLabels);
    return Math.min(
      currentKeys.indexOf(task.status),
      steps.length - 1
    );
  };

  const currentStepIndex = getCurrentStepIndex();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
        Task Status
      </h2>

      {/* Status Badge */}
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-3 h-3 rounded-full ${statusInfo.color} animate-pulse`} />
        <span className="text-lg font-medium text-gray-800 dark:text-white">
          {statusInfo.label}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
          <span>Progress</span>
          <span>{task.progress}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${task.progress}%` }}
          />
        </div>
      </div>

      {/* Step Indicators */}
      <div className="flex items-center justify-between mb-4">
        {steps.map((step, index) => {
          const isActive = index <= currentStepIndex;
          const isCurrent = index === currentStepIndex;

          return (
            <div key={step.key} className="flex flex-col items-center flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors duration-300 ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-500"
                } ${isCurrent ? "ring-4 ring-blue-200 dark:ring-blue-800" : ""}`}
              >
                {index + 1}
              </div>
              <span
                className={`text-xs mt-2 ${
                  isActive ? "text-blue-600 dark:text-blue-400" : "text-gray-500"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Error Message */}
      {task.error_message && (
        <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">
            {task.error_message}
          </p>
        </div>
      )}

      {/* Task ID */}
      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
        Task ID: {task.id}
      </div>
    </div>
  );
}

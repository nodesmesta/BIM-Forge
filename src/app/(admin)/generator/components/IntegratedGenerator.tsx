"use client";

import { useState } from "react";
import ChatInterface from "./ChatInterface";
import ClaudeTaskGenerator from "./ClaudeTaskGenerator";
import StatusTracker from "./StatusTracker";
import PipelineVisualizer from "./PipelineVisualizer";
import { Task } from "@/types/task";

interface Specification {
  project_name?: string;
  style?: string;
  floors?: number[];
  rooms?: Array<{
    room_type: string;
    count: number;
    min_area_m2: number;
    preferred_floor: number;
    exterior_access: boolean;
    private: boolean;
  }>;
  site?: {
    building_footprint_m2?: number;
  };
  total_area_m2?: number;
  location?: {
    name?: string;
    country?: string;
    latitude?: number;
    longitude?: number;
    timezone?: string;
  };
}

export default function IntegratedGenerator() {
  const [specification, setSpecification] = useState<Specification | null>(null);
  const [task, setTask] = useState<Task | null>(null);

  const handleSpecificationSubmit = (spec: Specification) => {
    setSpecification(spec);
  };

  const handleProgressUpdate = (updatedTask: Task) => {
    setTask(updatedTask);
  };

  return (
    <div className="min-h-[calc(100vh-120px)]">
      {/* Chat Interface */}
      <ChatInterface onGenerate={handleSpecificationSubmit} />

      {/* Task Generator (automatically triggered when specification is set) */}
      {specification && (
        <ClaudeTaskGenerator
          specification={specification}
          onTaskUpdate={handleProgressUpdate}
        />
      )}

      {/* Agent Flow Timeline (Real-time workflow visualization) */}
      {task && (
        <PipelineVisualizer taskId={task.id} task={task} />
      )}

      {/* Status Trackers */}
      {task && (
        <StatusTracker task={task} />
      )}
    </div>
  );
}
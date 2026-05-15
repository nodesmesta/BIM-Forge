"use client";

import { Task } from "@/types/task";

interface RenderPreviewProps {
  task: Task | null;
  renderUrl: string | null;
  isGenerating: boolean;
}

export default function RenderPreview({
  task,
  renderUrl,
  isGenerating,
}: RenderPreviewProps) {
  const getStatusMessage = () => {
    if (!task) {
      return "Enter a building description and click Generate to start";
    }

    switch (task.status) {
      case "pending":
        return "Waiting to start...";
      case "spec_generating":
        return "Analyzing your description...";
      case "spec_complete":
        return "Specification ready, creating model...";
      case "ifc_generating":
        return "Building IFC model...";
      case "ifc_complete":
        return "Model ready, starting render...";
      case "rendering":
        return "Rendering your building...";
      case "completed":
        return "Render complete!";
      case "failed":
        return "Generation failed";
      default:
        return "Processing...";
    }
  };

  const handleDownload = (url: string, filename: string) => {
    window.open(url, "_blank");
  };

  return (
    <div className="space-y-4">
      {/* Preview Area */}
      <div className="aspect-video bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center overflow-hidden">
        {renderUrl ? (
          task?.status === "completed" ? (
            <img
              src={renderUrl}
              alt="Building Render"
              className="w-full h-full object-contain"
              onError={(e) => {
                console.error("Image load error:", e);
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : (
            <img
              src={renderUrl}
              alt="Building Render"
              className="w-full h-full object-contain"
              onError={(e) => {
                console.error("Image load error:", e);
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          )
        ) : (
          <div className="text-center p-8">
            {isGenerating ? (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-gray-600 dark:text-gray-300">
                  {getStatusMessage()}
                </p>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                {getStatusMessage()}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {task?.status === "completed" && renderUrl && (
        <div className="flex gap-3">
          <button
            onClick={() => handleDownload(renderUrl, `${task.id}.png`)}
            className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Download Render
          </button>
          <button
            onClick={() =>
              handleDownload(
                `${window.location.origin}/api/gallery/${task.id}/ifc`,
                `${task.id}.ifc`
              )
            }
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Download IFC
          </button>
        </div>
      )}

      {/* Info Panel */}
      {task && (
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Task Information
          </h3>
          <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>
              <span className="font-medium">Prompt:</span> {task.prompt}
            </p>
            <p>
              <span className="font-medium">Status:</span> {task.status}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

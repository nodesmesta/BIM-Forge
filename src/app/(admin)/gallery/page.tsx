"use client";

import { useState, useEffect } from "react";
import { GalleryItem } from "@/types/task";
import { TaskDetailModal } from "@/app/(admin)/generator/components/TaskDetailModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function GalleryPage() {
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<GalleryItem | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  useEffect(() => {
    fetchGallery();
    const interval = setInterval(fetchGallery, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchGallery = async () => {
    try {
      const response = await fetch(`${API_URL}/api/gallery`);
      const data = await response.json();
      setItems(data);
    } catch (error) {
      console.error("Error fetching gallery:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (item: GalleryItem) => {
    setSelectedItem(item);
    setDetailModalOpen(true);
  };

  const handleDownload = (url: string, filename: string) => {
    window.open(url, "_blank");
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("id-ID", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Gallery
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          View and manage your generated building renders
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400 text-lg">
            No renders yet. Start by creating a new building!
          </p>
          <a
            href="/generator"
            className="inline-block mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors"
          >
            Create New Building
          </a>
        </div>
      ) : (
        <>
          {/* Grid View */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-theme-md overflow-hidden hover:shadow-theme-lg transition-all hover:-translate-y-1"
              >
                <div
                  className="aspect-square bg-gray-100 dark:bg-gray-700 cursor-pointer relative group"
                  onClick={() => handleViewDetails(item)}
                >
                  <img
                    src={`${API_URL}${item.image}`}
                    alt={`Render ${item.id.slice(0, 8)}`}
                    className="w-full h-full object-cover"
                  />
                  {/* Hover Overlay */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 dark:bg-gray-800/90 px-4 py-2 rounded-lg">
                      <span className="text-gray-800 dark:text-white font-medium">
                        👁️ View Details
                      </span>
                    </div>
                  </div>
                </div>
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDate(item.created_at)}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        item.status === "completed"
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                          : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>

                  {/* Task ID */}
                  <p className="text-xs font-mono text-gray-400 dark:text-gray-500 mb-3 truncate">
                    {item.id}
                  </p>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleViewDetails(item)}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 px-3 rounded transition-colors"
                    >
                      Details
                    </button>
                    <button
                      onClick={() => handleDownload(`${API_URL}${item.image}`, `${item.id}.png`)}
                      className="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-sm py-2 px-3 rounded transition-colors"
                    >
                      PNG
                    </button>
                    <button
                      onClick={() => handleDownload(`${API_URL}${item.ifc}`, `${item.id}.ifc`)}
                      className="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-sm py-2 px-3 rounded transition-colors"
                    >
                      IFC
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Total Count */}
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Total: {items.length} render{items.length !== 1 ? "s" : ""}
          </div>
        </>
      )}

      {/* Task Detail Modal with Agent Workflow */}
      <TaskDetailModal
        taskId={selectedItem?.id || null}
        isOpen={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedItem(null);
        }}
      />
    </div>
  );
}

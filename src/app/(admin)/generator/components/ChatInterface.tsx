"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Task } from "@/types/task";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ParsedInfo {
  project_name: string;
  style: string;
  floors: number;
  rooms: Array<{
    room_type: string;
    count: number;
    min_area_m2: number;
    preferred_floor: number;
    exterior_access: boolean;
    private: boolean;
  }>;
  location: {
    name: string;
    country: string;
    latitude: number;
    longitude: number;
    timezone: string;
  } | null;
  total_area: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  parsed_info?: ParsedInfo;
  specification?: any;
}

const ROOM_LABELS: Record<string, string> = {
  living_room: "Ruang Tamu",
  dining_room: "Ruang Makan",
  kitchen: "Dapur",
  bedroom: "Kamar Tidur",
  master_bedroom: "Kamar Utama",
  bathroom: "Kamar Mandi",
  office: "Kantor",
  garage: "Garasi",
  carport: "Carport",
  laundry: "Ruang Cuci",
  storage: "Gudang",
  garden: "Taman",
  balcony: "Balkon",
  terrace: "Teras",
  hallway: "Koridor",
  staircase: "Tangga",
};

const EXAMPLE_PROMPTS = [
  "Rumah minimalis 2 lantai dengan 3 kamar tidur, 2 kamar mandi di Jakarta",
  "Bangun rumah tropis 1 lantai 4 kamar tidur dengan carport di Bali",
  "Townhouse 3 lantai 5 kamar tidur kantor rooftop garden di Bandung",
];

export default function ChatInterface({ onGenerate }: { onGenerate: (spec: any) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Halo! 👋 Saya asisten desain bangunan Anda.\n\nCeritakan bangunan seperti apa yang ingin Anda bangun. Contoh:\n• \"Rumah minimalis 2 lantai dengan 3 kamar tidur, 2 kamar mandi di Jakarta\"\n• \"Bangun rumah tropis 1 lantai 4 kamar tidur dengan carport di Bali\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const response = await fetch(`${API_URL}/api/chatbot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: input }),
    });

    const data = await response.json();

    const assistantMessage: ChatMessage = {
      id: `assistant_${Date.now()}`,
      role: "assistant",
      content: data.message || data.success
        ? `Sempurna! Saya telah memproses deskripsi Anda.\n\n📋 **Ringkasan:**\n• **Nama:** ${data.parsed_info?.project_name || ""}\n• **Style:** ${data.parsed_info?.style || ""}\n• **Lantai:** ${data.parsed_info?.floors || ""}\n• **Lokasi:** ${data.parsed_info?.location?.name || ""}\n• **Luas:** ~${Math.round(data.parsed_info?.total_area)}m²\n\n🏠 **Ruangan:**\n${formatRooms(data.parsed_info?.rooms)}\n\nKlik tombol **Generate** di bawah untuk memulai pembuatan model IFC.`
        : `Maaf, saya tidak dapat memproses permintaan Anda: ${data.message}`,
      parsed_info: data.parsed_info,
      specification: data.specification,
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(false);
  };

  const formatRooms = (rooms: any[] | undefined) => {
    if (!rooms || !rooms.length) return "• (tidak ada ruangan yang spesifik)";

    const counts: Record<string, number> = {};
    rooms.forEach((r) => {
      counts[r.room_type] = (counts[r.room_type] || 0) + r.count;
    });

    return Object.entries(counts)
      .map(([type, count]) => {
        const label = ROOM_LABELS[type] || type;
        return `• ${count}x ${label}`;
      })
      .join("\n");
  };

  const handleGenerate = () => {
    const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.specification);
    if (lastAssistantMsg?.specification) {
      onGenerate(lastAssistantMsg.specification);
    }
  };

  const useExample = (example: string) => {
    setInput(example);
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow-theme-md">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
          💬 Chat Desain
        </h2>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Ceritakan bangunan yang Anda inginkan dalam bahasa Indonesia
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-4 py-3",
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200"
              )}
            >
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content}
              </p>

              {/* Generate Button */}
              {msg.role === "assistant" && msg.specification && (
                <button
                  onClick={handleGenerate}
                  className="mt-3 w-full py-2 px-4 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                >
                  <span>🚀</span>
                  <span>Generate Building</span>
                </button>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-900 rounded-lg px-4 py-3">
              <div className="flex items-center gap-2 text-gray-500">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span className="text-sm">Menganalisis...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Examples */}
      {messages.length === 1 && (
        <div className="px-4 pb-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Contoh yang bisa langsung digunakan:</p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_PROMPTS.map((example, idx) => (
              <button
                key={idx}
                onClick={() => useExample(example)}
                className="text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {example.length > 35 ? example.substring(0, 35) + "..." : example}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Contoh: Rumah minimalis 2 lantai dengan 3 kamar tidur..."
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-500 text-sm"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={cn(
              "px-4 py-2.5 rounded-lg font-medium transition-colors",
              input.trim() && !isLoading
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed"
            )}
          >
            {isLoading ? (
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
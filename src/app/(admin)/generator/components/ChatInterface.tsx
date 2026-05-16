"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ParsedInfo {
  project_name?: string;
  style?: string;
  floors?: number;
  rooms?: Array<{
    room_type: string;
    count: number;
    min_area_m2: number;
    preferred_floor: number;
    exterior_access: boolean;
    private: boolean;
  }>;
  location?: {
    name: string;
    country: string;
    latitude: number;
    longitude: number;
    timezone: string;
  } | null;
  total_area?: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  parsed_info?: ParsedInfo;
  specification?: any;
  is_complete?: boolean;
}

interface SessionData {
  builder_data: any;
  history: Array<{ role: string; content: string }>;
}

export default function ChatInterface({ onGenerate }: { onGenerate: (spec: any) => void }) {
const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi! I am the BIM Forge assistant. I can help you design buildings, answer questions about architecture and BIM, or just chat.\\n\\nTo start designing, just tell me the building you have in mind -- for example: \"I want a minimalist 2-story house with 3 bedrooms in Bandung\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chatbot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          prompt: currentInput,
          session_data: sessionData
        }),
      });

      const data = await response.json();

      if (data.success) {
        const assistantMessage: ChatMessage = {
          id: `assistant_${Date.now()}`,
          role: "assistant",
          content: data.message || "An error occurred while processing your request.",
          parsed_info: data.parsed_info,
          specification: data.specification,
          is_complete: data.is_complete,
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Save session data for next turn
        if (data.session_data) {
          setSessionData(data.session_data);
        }
      } else {
        const errorMessage: ChatMessage = {
          id: `error_${Date.now()}`,
          role: "assistant",
          content: data.message || "I couldn't process that request.",
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: "assistant",
        content: "Connection error. Make sure the backend server is running on port 8000.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = () => {
    const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.specification);
    if (lastAssistantMsg?.specification) {
      onGenerate(lastAssistantMsg.specification);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] bg-gray-50 dark:bg-gray-800 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-gray-800">
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
                  : "bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100"
              )}
            >
              {/* Avatar indicator */}
              <div className="mb-1">
                <span className="text-xs opacity-70 font-medium">
                  {msg.role === "user" ? "You" : "Assistant"}
                </span>
              </div>
              
              <div className="text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="text-gray-700 dark:text-gray-200">{children}</li>,
                    strong: ({ children }) => <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>,
                    h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-base font-semibold mb-1">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
                    code: ({ children, className }) => {
                      const isInline = !className;
                      return isInline 
                        ? <code className="bg-gray-100 dark:bg-gray-600 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                        : <code className={className}>{children}</code>;
                    },
                    pre: ({ children }) => <pre className="bg-gray-100 dark:bg-gray-600 p-2 rounded overflow-x-auto text-xs mb-2">{children}</pre>,
                    a: ({ href, children }) => <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                    blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 dark:border-gray-500 pl-3 italic text-gray-600 dark:text-gray-400 mb-2">{children}</blockquote>,
                    table: ({ children }) => <table className="w-full border-collapse border border-gray-300 dark:border-gray-600 mb-2 text-xs">{children}</table>,
                    th: ({ children }) => <th className="border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-600 px-2 py-1 text-left font-semibold">{children}</th>,
                    td: ({ children }) => <td className="border border-gray-300 dark:border-gray-600 px-2 py-1">{children}</td>,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>

              {/* Generate Button - only show when specification is complete */}
              {msg.role === "assistant" && msg.specification && msg.is_complete && (
                <button
                  onClick={handleGenerate}
                  className="mt-3 w-full py-2.5 px-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg"
                >
                  Generate Building
                </button>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-700 rounded-lg px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span className="text-sm text-gray-600 dark:text-gray-300">Analyzing...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2">
        <div className="flex items-end gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 shadow-sm hover:shadow-md transition-shadow">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (input.trim() && !isLoading) {
                  handleSubmit();
                }
              }
            }}
            placeholder="Type your message..."
            className="flex-1 bg-transparent text-gray-800 dark:text-white text-sm placeholder-gray-400 resize-none outline-none min-h-[24px] max-h-[120px]"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className={cn(
              "p-2 rounded-full transition-colors flex-shrink-0",
              input.trim() && !isLoading
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
            )}
          >
            {isLoading ? (
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          AI can make mistakes. Consider checking important information.
        </p>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Send, FileText, Bot, User, Loader2 } from "lucide-react";

interface Source {
  id: number;
  source: string;
  text: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I am your Talent Acquisition (TA) Copilot. Ask me anything about candidate resumes, job descriptions, or pipeline spreadsheets.",
    },
  ]);
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = query;
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8001/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage, top_k: 5, top_n: 3 }),
      });

      if (!res.ok) throw new Error("Failed to fetch response from backend.");

      const data = await res.json();
      
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          sources: data.sources,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error: Could not connect to the FastAPI backend. Make sure your server is running on port 8000.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex flex-col h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 p-4 bg-slate-950 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="bg-indigo-600 p-2 rounded-lg">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg">Talent Acquisition RAG Copilot</h1>
            <p className="text-xs text-slate-400">Powered by FastAPI, Qdrant, BGE-Reranker & Groq Llama-3</p>
          </div>
        </div>
      </header>

      {/* Chat Messages Window */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 max-w-4xl mx-auto w-full">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-3 ${
              msg.role === "user" ? "flex-row-reverse space-x-reverse" : ""
            }`}
          >
            <div
              className={`p-2 rounded-full flex items-center justify-center ${
                msg.role === "user" ? "bg-indigo-600" : "bg-emerald-600"
              }`}
            >
              {msg.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>

            <div
              className={`max-w-xl rounded-2xl p-4 shadow-md ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-tr-none"
                  : "bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>

              {/* Render Source Citations if present */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-700/60">
                  <p className="text-xs font-semibold text-slate-400 mb-2">Retrieved Sources:</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src) => (
                      <div
                        key={src.id}
                        className="bg-slate-900/80 border border-slate-700 rounded-lg p-2 text-xs flex items-center space-x-1.5 max-w-xs"
                      >
                        <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                        <span className="font-medium text-indigo-300">[{src.id}] {src.source}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-start space-x-3">
            <div className="bg-emerald-600 p-2 rounded-full">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-slate-800 border border-slate-700 rounded-2xl p-4 rounded-tl-none flex items-center space-x-2 text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span className="text-sm">Analyzing candidate profiles and ranking contexts...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Form Footer */}
      <footer className="border-t border-slate-800 p-4 bg-slate-950">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about candidates, skills, or job requirements (e.g., 'Who has python experience?')..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-slate-100 placeholder-slate-500"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-5 rounded-xl flex items-center justify-center transition"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </footer>
    </main>
  );
}
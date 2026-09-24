"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Bot,
  Check,
  CircleAlert,
  FileText,
  FileUp,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  UploadCloud,
  User,
  X,
} from "lucide-react";

interface Source {
  id: number;
  source: string;
  text: string;
}

interface ChatSession {
  id: string;
  messages: Message[];
  updatedAt: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

interface UploadResult {
  filename: string;
  status?: string;
  message?: string;
}

const acceptedFileTypes = ".pdf,.doc,.docx,.txt,.xls,.xlsx,.png,.jpg,.jpeg,.webp";
const chatHistoryKey = "ta-rag-chat-history";
const initialMessage: Message = {
  role: "assistant",
  content:
    "Hello! I’m your Talent Acquisition copilot. Ask me about candidates, skills, job requirements, or interview schedules.",
};

function createChatSession(): ChatSession {
  return { id: crypto.randomUUID(), messages: [initialMessage], updatedAt: Date.now() };
}

function getChatTitle(messages: Message[]) {
  return messages.find((message) => message.role === "user")?.content || "New conversation";
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const conversationEndRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [uploadMessage, setUploadMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState("");
  const [historyReady, setHistoryReady] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    try {
      const storedHistory = sessionStorage.getItem(chatHistoryKey);
      const parsedHistory = storedHistory ? JSON.parse(storedHistory) as ChatSession[] : [];
      const sessions = parsedHistory.length > 0 ? parsedHistory : [createChatSession()];
      startTransition(() => {
        setChatHistory(sessions);
        setActiveChatId(sessions[0].id);
        setMessages(sessions[0].messages);
      });
    } catch {
      const session = createChatSession();
      startTransition(() => {
        setChatHistory([session]);
        setActiveChatId(session.id);
        setMessages(session.messages);
      });
    } finally {
      setHistoryReady(true);
    }
  }, []);

  useEffect(() => {
    if (historyReady && chatHistory.length > 0) {
      sessionStorage.setItem(chatHistoryKey, JSON.stringify(chatHistory));
    }
  }, [chatHistory, historyReady]);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, activeChatId]);

  const updateMessages = (updater: Message[] | ((current: Message[]) => Message[])) => {
    setMessages((current) => {
      const next = typeof updater === "function" ? updater(current) : updater;
      setChatHistory((history) => history.map((chat) => (
        chat.id === activeChatId ? { ...chat, messages: next, updatedAt: Date.now() } : chat
      )));
      return next;
    });
  };

  const createNewChat = () => {
    if (loading) return;
    const session = createChatSession();
    setChatHistory((current) => [session, ...current]);
    setActiveChatId(session.id);
    setMessages(session.messages);
    setQuery("");
  };

  const selectChat = (session: ChatSession) => {
    if (loading) return;
    setActiveChatId(session.id);
    setMessages(session.messages);
    setQuery("");
  };

  const deleteChat = (chatId: string) => {
    if (loading) return;

    setChatHistory((current) => {
      const remainingChats = current.filter((chat) => chat.id !== chatId);

      if (remainingChats.length === 0) {
        const replacementChat = createChatSession();
        setActiveChatId(replacementChat.id);
        setMessages(replacementChat.messages);
        return [replacementChat];
      }

      if (chatId === activeChatId) {
        const nextChat = remainingChats[0];
        setActiveChatId(nextChat.id);
        setMessages(nextChat.messages);
      }

      return remainingChats;
    });
    setQuery("");
  };

  const addFiles = (files: File[]) => {
    setSelectedFiles((current) => {
      const nextFiles = files.filter(
        (file) => !current.some((existing) => existing.name === file.name && existing.size === file.size),
      );
      return [...current, ...nextFiles];
    });
    setUploadStatus("idle");
    setUploadMessage("");
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) addFiles(Array.from(event.target.files));
    event.target.value = "";
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    addFiles(Array.from(event.dataTransfer.files));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setUploadStatus("error");
      setUploadMessage("Choose at least one document to index.");
      return;
    }

    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append("files", file));

    try {
      setUploadStatus("uploading");
      setUploadMessage("Parsing documents and updating the knowledge base...");
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();
      const results = (data.files as UploadResult[])
        .map((file) => `${file.filename}: ${file.message || file.status || "indexed"}`)
        .join("\n");
      setUploadStatus("success");
      setUploadMessage(results || "Documents indexed successfully.");
      setSelectedFiles([]);
    } catch {
      setUploadStatus("error");
      setUploadMessage("Upload failed. Check that the backend service is running.");
    }
  };

  const handleSendMessage = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = query.trim();
    setQuery("");
    updateMessages((current) => [
      ...current,
      { role: "user", content: userMessage },
      { role: "assistant", content: "" },
    ]);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage, top_k: 5, top_n: 3 }),
      });
      if (!response.ok) throw new Error("Chat request failed");

      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await response.json();
        updateMessages((current) => {
          const next = [...current];
          const assistantIndex = next.length - 1;
          next[assistantIndex] = {
            role: "assistant",
            content: data.response,
            sources: data.sources,
          };
          return next;
        });
      } else {
        if (!response.body) throw new Error("Chat response has no body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamedResponse = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          if (!chunk) continue;
          streamedResponse += chunk;

          updateMessages((current) => {
            const next = [...current];
            const assistantIndex = next.length - 1;
            next[assistantIndex] = {
              ...next[assistantIndex],
              content: streamedResponse,
            };
            return next;
          });
        }

        const remainder = decoder.decode();
        if (remainder) {
          streamedResponse += remainder;
          updateMessages((current) => {
            const next = [...current];
            const assistantIndex = next.length - 1;
            next[assistantIndex] = {
              ...next[assistantIndex],
              content: streamedResponse,
            };
            return next;
          });
        }

        const citationMarker = "\nSources:\n";
        const citationIndex = streamedResponse.indexOf(citationMarker);
        const answer = citationIndex >= 0
          ? streamedResponse.slice(0, citationIndex).trimEnd()
          : streamedResponse;
        const citations = citationIndex >= 0
          ? streamedResponse
              .slice(citationIndex + citationMarker.length)
              .split("\n")
              .map((line) => line.match(/^\[(\d+)\]\s+(.+)$/))
              .filter((match): match is RegExpMatchArray => match !== null)
              .map(([, id, source]) => ({
                id: Number(id),
                source,
                text: "",
              }))
          : [];

        updateMessages((current) => {
          const next = [...current];
          const assistantIndex = next.length - 1;
          next[assistantIndex] = {
            ...next[assistantIndex],
            content: answer,
            sources: citations,
          };
          return next;
        });
      }
    } catch {
      updateMessages((current) => {
        const next = [...current];
        const assistantIndex = next.length - 1;
        next[assistantIndex] = {
          ...next[assistantIndex],
          content: "I couldn’t connect to the backend service. Make sure it is running on port 8000.",
        };
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark"><Sparkles size={19} strokeWidth={2.5} /></div>
          <div>
            <p className="brand-name">Talent Acquisition</p>
            <p className="brand-product">RAG Copilot</p>
          </div>
        </div>
      </header>

      <div className="workspace">
        <aside className="library-panel">
          <div className="panel-heading">
            <div>
              <h1>Document intake</h1>
            </div>
            <span className="count-badge">{selectedFiles.length}</span>
          </div>

          <div className="upload-zone" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
            <div className="upload-icon"><UploadCloud size={22} /></div>
            <h2>Drop files here</h2>
            <p>Resumes, job descriptions, spreadsheets, or images</p>
            <button type="button" className="secondary-button" onClick={() => fileInputRef.current?.click()}>
              <Plus size={16} /> Browse files
            </button>
            <input ref={fileInputRef} type="file" multiple accept={acceptedFileTypes} onChange={handleFileSelect} hidden />
            <span className="file-hint">PDF, DOCX, XLSX, TXT, PNG · up to 10 files</span>
          </div>

          <div className="queue-heading">
            <span>Upload queue</span>
            <span>{selectedFiles.length ? `${selectedFiles.length} selected` : "Empty"}</span>
          </div>

          <div className="file-list">
            {selectedFiles.length === 0 ? (
              <div className="empty-files"><FileUp size={18} /><span>Selected documents appear here</span></div>
            ) : (
              selectedFiles.map((file) => (
                <div className="file-row" key={`${file.name}-${file.size}`}>
                  <div className="file-type"><FileText size={16} /></div>
                  <div className="file-details"><strong>{file.name}</strong><span>{formatFileSize(file.size)}</span></div>
                  <button type="button" className="icon-button" aria-label={`Remove ${file.name}`} onClick={() => setSelectedFiles((current) => current.filter((item) => item !== file))}>
                    <X size={15} />
                  </button>
                </div>
              ))
            )}
          </div>

          <button type="button" className="primary-button upload-button" onClick={handleUpload} disabled={uploadStatus === "uploading"}>
            {uploadStatus === "uploading" ? <Loader2 size={17} className="spin" /> : <UploadCloud size={17} />}
            {uploadStatus === "uploading" ? "Indexing documents" : "Upload & index"}
            {uploadStatus !== "uploading" && <ArrowUpRight size={16} />}
          </button>

          {uploadMessage && (
            <div className={`upload-feedback ${uploadStatus}`}>
              {uploadStatus === "success" ? <Check size={16} /> : uploadStatus === "error" ? <CircleAlert size={16} /> : null}
              <span>{uploadMessage}</span>
            </div>
          )}

          <div className="privacy-note"><Check size={14} /><span>Documents stay in your local workspace</span></div>

          <div className="history-panel">
            <div className="history-heading">
              <span><MessageSquare size={14} /> Chat history</span>
              <div className="history-actions">
                <span>{chatHistory.length}</span>
                <button type="button" className="new-chat-button sidebar-new-chat-button" onClick={createNewChat}>
                  <Plus size={15} /> New chat
                </button>
              </div>
            </div>
            <div className="history-list">
              {chatHistory.map((chat) => (
                <button
                  type="button"
                  className={`history-item ${chat.id === activeChatId ? "active" : ""}`}
                  key={chat.id}
                  onClick={() => selectChat(chat)}
                  title={getChatTitle(chat.messages)}
                >
                  <MessageSquare size={14} />
                  <span>{getChatTitle(chat.messages)}</span>
                  <span
                    className="history-delete"
                    role="button"
                    tabIndex={0}
                    aria-label={`Delete ${getChatTitle(chat.messages)}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      deleteChat(chat.id);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        event.stopPropagation();
                        deleteChat(chat.id);
                      }
                    }}
                  >
                    <X size={13} />
                  </span>
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="chat-panel">
          <div className="conversation">
            <div className="conversation-intro">
              <span className="intro-kicker">Ready when you are</span>
              <h2>Make your candidate data useful.</h2>
              <p>Ask a focused question and I’ll search, rerank, and cite the most relevant evidence.</p>
              <div className="prompt-chips">
                {["Who has Python experience?", "Compare candidates for a role", "Show interview schedules"].map((prompt) => (
                  <button type="button" key={prompt} onClick={() => setQuery(prompt)}>{prompt}<ArrowUpRight size={14} /></button>
                ))}
              </div>
            </div>

            <div className="message-stack">
              {messages.map((message, index) => (
                <div className={`message ${message.role}`} key={`${message.role}-${index}`}>
                  <div className="message-avatar">{message.role === "user" ? <User size={15} /> : <Bot size={15} />}</div>
                  <div className="message-content">
                    <span className="message-label">{message.role === "user" ? "You" : "Copilot"}</span>
                    <p>
                      {message.content || (loading && message.role === "assistant" && index === messages.length - 1 ? (
                        <><Loader2 size={15} className="spin" /> Searching your knowledge base...</>
                      ) : null)}
                    </p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="sources-block">
                        <span>Sources used</span>
                        <div className="source-list">
                          {message.sources.map((source) => <div className="source-pill" key={source.id}><FileText size={13} /> [{source.id}] {source.source}</div>)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={conversationEndRef} aria-hidden="true" />
            </div>
          </div>

          <div className="composer-wrap">
            <form className="composer" onSubmit={handleSendMessage}>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask about candidates, skills, roles, or interviews..." aria-label="Ask the recruiting assistant" />
              <button type="submit" className="send-button" disabled={loading || !query.trim()} aria-label="Send message"><Send size={17} /></button>
            </form>
            <p className="composer-note">AI-generated answers are grounded in indexed evidence. Review sources before making hiring decisions.</p>
          </div>
        </section>
      </div>
    </main>
  );
}
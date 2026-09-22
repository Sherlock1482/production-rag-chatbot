"use client";

import { useRef, useState } from "react";
import {
  ArrowUpRight,
  Bot,
  Check,
  CircleAlert,
  FileArchive,
  FileText,
  FileUp,
  Loader2,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Trash2,
  UploadCloud,
  User,
  X,
} from "lucide-react";

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

interface UploadResult {
  filename: string;
  status?: string;
  message?: string;
}

const acceptedFileTypes = ".pdf,.doc,.docx,.txt,.xls,.xlsx,.png,.jpg,.jpeg,.webp";

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [uploadMessage, setUploadMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I’m your Talent Acquisition copilot. Ask me about candidates, skills, job requirements, or interview schedules.",
    },
  ]);
  const [loading, setLoading] = useState(false);

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
      setUploadMessage("Upload failed. Check that the FastAPI backend is running.");
    }
  };

  const handleSendMessage = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = query.trim();
    setQuery("");
    setMessages((current) => [...current, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage, top_k: 5, top_n: 3 }),
      });
      if (!response.ok) throw new Error("Chat request failed");
      const data = await response.json();
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.response, sources: data.sources },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "I couldn’t connect to the backend. Make sure FastAPI is running on port 8000.",
        },
      ]);
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
        <div className="topbar-meta">
          <span className="status-dot" />
          <span>Knowledge workspace</span>
          <span className="topbar-divider" />
          <span className="engine-label">FastAPI <b>·</b> Qdrant <b>·</b> Groq</span>
        </div>
      </header>

      <div className="workspace">
        <aside className="library-panel">
          <div className="eyebrow"><FileArchive size={14} /> Knowledge base</div>
          <div className="panel-heading">
            <div>
              <h1>Document intake</h1>
              <p>Build the source library your copilot searches.</p>
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
        </aside>

        <section className="chat-panel">
          <div className="chat-header">
            <div className="chat-title-wrap">
              <div className="assistant-avatar"><Bot size={20} /></div>
              <div><h2>Recruiting assistant</h2><p>Grounded answers from your indexed documents</p></div>
            </div>
            <button type="button" className="new-chat-button" onClick={() => setMessages([messages[0]])}><Trash2 size={15} /> Clear chat</button>
          </div>

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
                    <p>{message.content}</p>
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
              {loading && <div className="message assistant"><div className="message-avatar"><Bot size={15} /></div><div className="message-content loading-message"><span className="message-label">Copilot</span><p><Loader2 size={15} className="spin" /> Searching your knowledge base...</p></div></div>}
            </div>
          </div>

          <div className="composer-wrap">
            <form className="composer" onSubmit={handleSendMessage}>
              <Paperclip size={18} className="composer-icon" />
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
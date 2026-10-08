"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Bot,
  Briefcase,
  Check,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  FileText,
  FileUp,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Target,
  UploadCloud,
  User,
  X,
} from "lucide-react";

interface Source {
  id: number | string;
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

function FormattedMessage({ content }: { content: string }) {
  if (!content) return null;

  // Sanitize Windows console mojibake (e.g. ΓÇó -> - , ΓÇö -> - ) and normalize bullets/dashes
  const sanitized = content
    .replace(/ΓÇó/g, "- ")
    .replace(/ΓÇö/g, " - ")
    .replace(/[•●]/g, "- ")
    .replace(/[—–]/g, " - ");

  const lines = sanitized.split("\n");
  const renderedElements: React.ReactNode[] = [];
  let currentBullets: string[] = [];

  const flushBullets = (keyIdx: number) => {
    if (currentBullets.length > 0) {
      renderedElements.push(
        <ul key={`ul-${keyIdx}`} className="formatted-bullet-list">
          {currentBullets.map((b, bIdx) => (
            <li key={`li-${keyIdx}-${bIdx}`}>{b}</li>
          ))}
        </ul>
      );
      currentBullets = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Check dividing rules
    if (trimmed.startsWith("----") || trimmed.startsWith("====")) {
      flushBullets(idx);
      renderedElements.push(<hr key={`hr-${idx}`} className="formatted-divider" />);
      return;
    }

    // Check bullet points (- or *)
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const cleanBullet = trimmed.replace(/^[\-\*]\s*/, "").replace(/\*\*/g, "").trim();
      currentBullets.push(cleanBullet);
      return;
    }

    flushBullets(idx);

    if (!trimmed) return;

    // Check major section headings
    const isMainHeading =
      trimmed.startsWith("TOP ") ||
      trimmed.startsWith("CANDIDATE FIT & GAP ANALYSIS") ||
      trimmed.startsWith("CANDIDATE MATCH & COMPARISON SUMMARY") ||
      trimmed.startsWith("DETAILED CANDIDATE EVALUATION BREAKDOWN");

    if (isMainHeading) {
      renderedElements.push(
        <h4 key={`h4-${idx}`} className="formatted-section-heading">
          {trimmed.replace(/^[#\s]+/, "").replace(/\*\*/g, "")}
        </h4>
      );
      return;
    }

    // Check subheadings (ends with :)
    const isSubheading =
      trimmed.endsWith(":") &&
      (trimmed.includes("Summary") ||
        trimmed.includes("Skills") ||
        trimmed.includes("Strengths") ||
        trimmed.includes("Questions") ||
        trimmed.includes("Breakdown") ||
        trimmed.includes("Gaps"));

    if (isSubheading) {
      renderedElements.push(
        <h5 key={`h5-${idx}`} className="formatted-sub-heading">
          {trimmed.replace(/^[#\s]+/, "").replace(/\*\*/g, "")}
        </h5>
      );
      return;
    }

    // Check candidate line: e.g. "1. Alex — 67% Match" or "Candidate 1: Alex..."
    const isCandidateHeading = /^(?:\d+\.|\bCandidate\s+\d+:)/i.test(trimmed);
    if (isCandidateHeading) {
      renderedElements.push(
        <div key={`cand-header-${idx}`} className="formatted-candidate-heading">
          {trimmed.replace(/\*\*/g, "")}
        </div>
      );
      return;
    }

    // Clean regular paragraph
    const cleanText = trimmed.replace(/\*\*/g, "").replace(/^[#\s]+/, "");
    renderedElements.push(
      <p key={`p-${idx}`} className="formatted-text-line">
        {cleanText}
      </p>
    );
  });

  flushBullets(lines.length);

  return <div className="formatted-message-body">{renderedElements}</div>;
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
  const [intakeTab, setIntakeTab] = useState<"general" | "jd">("general");
  const [intakeCollapsed, setIntakeCollapsed] = useState(false);
  const [selectedJdFile, setSelectedJdFile] = useState<File | null>(null);
  const [jdCandidateName, setJdCandidateName] = useState("");
  const [jdUploadStatus, setJdUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [jdUploadMessage, setJdUploadMessage] = useState("");
  const jdFileInputRef = useRef<HTMLInputElement>(null);

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

  const handleJdAnalysis = async () => {
    if (!selectedJdFile) {
      setJdUploadStatus("error");
      setJdUploadMessage("Choose a Job Description PDF first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedJdFile);
    formData.append("candidate_name", jdCandidateName.trim());
    formData.append("session_id", activeChatId);

    try {
      setJdUploadStatus("uploading");
      setJdUploadMessage(
        jdCandidateName.trim()
          ? `Evaluating ${jdCandidateName.trim()} against ${selectedJdFile.name}...`
          : `Scanning Qdrant resumes to rank Top 3 matches for ${selectedJdFile.name}...`
      );

      const response = await fetch("http://localhost:8000/upload-jd", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to process JD PDF");
      }

      const data = await response.json();

      if (data.status === "analyzed") {
        setJdUploadStatus("success");
        setJdUploadMessage(
          data.top_candidates
            ? `Top 3 matching candidates ranked from Qdrant.`
            : `Analysis complete: ${data.candidate_name}.`
        );

        const promptText = data.top_candidates
          ? `Find top candidate matches in Qdrant for Job Description: ${data.filename}`
          : `Evaluate ${data.candidate_name} against uploaded Job Description: ${data.filename}`;
        const finalAnswer = data.markdown_report || "Fit analysis complete.";
        const sources = (data.sources || []).map((s: string, idx: number) => ({
          id: idx + 1,
          source: s,
          text: "",
        }));

        updateMessages((current) => [
          ...current,
          { role: "user", content: promptText },
          { role: "assistant", content: finalAnswer, sources },
        ]);
        setSelectedJdFile(null);
      } else if (data.status === "candidate_not_found") {
        setJdUploadStatus("error");
        setJdUploadMessage(
          data.message || `No resume found for candidate '${data.candidate_name}' in the knowledge base.`
        );
      } else {
        setJdUploadStatus("success");
        setJdUploadMessage(data.message || "Job Description PDF parsed successfully.");
      }
    } catch (err: any) {
      setJdUploadStatus("error");
      setJdUploadMessage(err.message || "Failed to analyze Job Description PDF.");
    }
  };

  const handleSendMessage = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = query.trim();
    setQuery("");

    // Capture current conversation history before adding new user message
    const recentHistory = messages
      .filter((m) => m.content && m.content !== initialMessage.content)
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));

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
        body: JSON.stringify({
          query: userMessage,
          top_k: 5,
          top_n: 3,
          session_id: activeChatId,
          history: recentHistory,
        }),
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

        const parseStreamedContent = (raw: string) => {
          const match = raw.match(/\n+(?:Sources used|Sources:?)\s*(?:\n|$)/i);
          if (!match || match.index === undefined) {
            return { answer: raw, citations: [] };
          }
          const answer = raw.slice(0, match.index).trimEnd();
          const remaining = raw.slice(match.index + match[0].length);
          const seen = new Set<string>();
          const citations = remaining
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean)
            .map((l) => {
              const m = l.match(/^\[([^\]]+)\]\s*(.+)$/);
              return m ? { id: m[1], source: m[2].trim() } : null;
            })
            .filter((item): item is { id: string; source: string } => item !== null)
            .filter((item) => {
              const key = item.source.toLowerCase();
              if (seen.has(key)) return false;
              seen.add(key);
              return true;
            })
            .map((item, idx) => ({
              id: item.id.toLowerCase() === "live" ? "Live" : idx + 1,
              source: item.source,
              text: "",
            }));
          return { answer, citations };
        };

        const { answer, citations } = parseStreamedContent(streamedResponse);

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
          {/* Top Bar: Title & Circular New Chat button */}
          <div className="sidebar-top-bar">
            <div className="sidebar-title-group">
              <MessageSquare size={16} className="sidebar-title-icon" />
              <span className="sidebar-title">Chats</span>
              <span className="count-badge count-badge-sm">{chatHistory.length}</span>
            </div>
            <button
              type="button"
              className="circle-new-chat-btn"
              onClick={createNewChat}
              title="Start new conversation"
              aria-label="New chat"
            >
              <Plus size={18} strokeWidth={2.4} />
            </button>
          </div>

          {/* Dynamic Scrollable Chat History List (Flexible 1fr) */}
          <div className="history-scroll-container">
            {chatHistory.length === 0 ? (
              <div className="empty-history">
                <span>No previous conversations</span>
              </div>
            ) : (
              chatHistory.map((chat) => (
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
              ))
            )}
          </div>

          {/* Compact, Dynamic Intake Widget (Zero Scroll) */}
          <div className="compact-intake-card">
            <div className="intake-header-row">
              <div className="intake-tab-bar compact">
                <button
                  type="button"
                  className={`intake-tab-btn ${intakeTab === "general" ? "active" : ""}`}
                  onClick={() => setIntakeTab("general")}
                >
                  <FileText size={12} /> Resumes
                </button>
                <button
                  type="button"
                  className={`intake-tab-btn ${intakeTab === "jd" ? "active" : ""}`}
                  onClick={() => setIntakeTab("jd")}
                >
                  <Briefcase size={12} /> JD (PDF)
                </button>
              </div>

              <button
                type="button"
                className="intake-toggle-btn"
                onClick={() => setIntakeCollapsed((prev) => !prev)}
                title={intakeCollapsed ? "Expand upload intake" : "Minimize upload intake"}
                aria-label="Toggle intake visibility"
              >
                {intakeCollapsed ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>

            {!intakeCollapsed && (
              <div className="intake-body-area">
                {intakeTab === "general" ? (
                  <>
                    <div
                      className="compact-dropzone"
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <UploadCloud size={16} className="compact-drop-icon" />
                      <span className="compact-drop-text">
                        {selectedFiles.length > 0
                          ? `${selectedFiles.length} file(s) chosen`
                          : "Drop resumes or browse"}
                      </span>
                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept={acceptedFileTypes}
                        onChange={handleFileSelect}
                        hidden
                      />
                    </div>

                    {selectedFiles.length > 0 && (
                      <div className="compact-file-chip-row">
                        {selectedFiles.map((file) => (
                          <div className="compact-file-chip" key={`${file.name}-${file.size}`}>
                            <span title={file.name}>{file.name}</span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedFiles((current) => current.filter((item) => item !== file));
                              }}
                              aria-label={`Remove ${file.name}`}
                            >
                              <X size={11} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    <button
                      type="button"
                      className="primary-button compact-action-btn"
                      onClick={handleUpload}
                      disabled={uploadStatus === "uploading" || selectedFiles.length === 0}
                    >
                      {uploadStatus === "uploading" ? (
                        <Loader2 size={14} className="spin" />
                      ) : (
                        <UploadCloud size={14} />
                      )}
                      <span>{uploadStatus === "uploading" ? "Indexing..." : "Upload & index"}</span>
                      {uploadStatus !== "uploading" && <ArrowUpRight size={13} />}
                    </button>

                    {uploadMessage && (
                      <div className={`compact-feedback ${uploadStatus}`}>
                        {uploadStatus === "success" ? <Check size={12} /> : <CircleAlert size={12} />}
                        <span>{uploadMessage}</span>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div
                      className="compact-dropzone jd"
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={(event) => {
                        event.preventDefault();
                        const file = Array.from(event.dataTransfer.files).find((f) =>
                          f.name.toLowerCase().endsWith(".pdf")
                        );
                        if (file) {
                          setSelectedJdFile(file);
                          setJdUploadStatus("idle");
                          setJdUploadMessage("");
                        }
                      }}
                      onClick={() => jdFileInputRef.current?.click()}
                    >
                      <Briefcase size={16} className="compact-drop-icon" />
                      <span className="compact-drop-text">
                        {selectedJdFile ? selectedJdFile.name : "Drop JD (PDF) or browse"}
                      </span>
                      {selectedJdFile && (
                        <button
                          type="button"
                          className="compact-chip-clear"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedJdFile(null);
                          }}
                          aria-label="Clear selected JD"
                        >
                          <X size={12} />
                        </button>
                      )}
                      <input
                        ref={jdFileInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setSelectedJdFile(e.target.files[0]);
                            setJdUploadStatus("idle");
                            setJdUploadMessage("");
                          }
                          e.target.value = "";
                        }}
                        hidden
                      />
                    </div>

                    <div className="dynamic-jd-indicator">
                      <Sparkles size={12} className="dynamic-jd-icon" />
                      <span>Scans all resumes in Qdrant &amp; ranks Top 3 matching candidates</span>
                    </div>

                    <button
                      type="button"
                      className="primary-button compact-action-btn jd"
                      onClick={handleJdAnalysis}
                      disabled={!selectedJdFile || jdUploadStatus === "uploading"}
                    >
                      {jdUploadStatus === "uploading" ? (
                        <Loader2 size={14} className="spin" />
                      ) : (
                        <Target size={14} />
                      )}
                      <span>
                        {jdUploadStatus === "uploading"
                          ? "Matching Qdrant Resumes..."
                          : "Find Top 3 Matches in Qdrant"}
                      </span>
                      {jdUploadStatus !== "uploading" && <ArrowUpRight size={13} />}
                    </button>

                    {jdUploadMessage && (
                      <div className={`compact-feedback ${jdUploadStatus}`}>
                        {jdUploadStatus === "success" ? <Check size={12} /> : <CircleAlert size={12} />}
                        <span>{jdUploadMessage}</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
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
                    {message.role === "assistant" ? (
                      message.content ? (
                        <FormattedMessage content={message.content} />
                      ) : loading && index === messages.length - 1 ? (
                        <p className="loading-message">
                          <Loader2 size={15} className="spin" /> Searching your knowledge base...
                        </p>
                      ) : null
                    ) : (
                      <p>{message.content}</p>
                    )}
                    {message.sources && message.sources.length > 0 && (
                      <div className="sources-block">
                        <span>Sources used</span>
                        <div className="source-list">
                          {message.sources.map((source) => <div className="source-pill" key={`${source.id}-${source.source}`}><FileText size={13} /> [{source.id}] {source.source}</div>)}
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
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask about candidates, skills, roles, or interviews..."
                aria-label="Ask the recruiting assistant"
              />
              <button
                type="submit"
                className="send-button"
                disabled={loading || !query.trim()}
                aria-label="Send message"
              >
                <Send size={17} />
              </button>
            </form>
            <p className="composer-note">AI-generated answers are grounded in indexed evidence. Review sources before making hiring decisions.</p>
          </div>

        </section>
      </div>
    </main>
  );
}
import React, { useMemo, useRef, useState, useCallback } from "react";
import toast from "react-hot-toast";
import {
  Activity,
  Upload,
  Package,
  Code,
  TrendingUp,
  RotateCcw,
  Play,
  CheckCircle2,
  Circle,
  AlertTriangle,
  X,
  TerminalSquare,
  Send,
} from "lucide-react";

import { useDashboardStore } from "../store";
import { useWebSocket } from "../hooks/useWebSocket";
import { api } from "../api/client";
import type { ModeId } from "../types";

type QuickCard = {
  id: string;
  title: string;
  description: string;
  model: "claude" | "gpt-oss";
  icon: React.ReactNode;
  onRun: () => Promise<void> | void;
};

export function MeridianDesktop() {
  useWebSocket();

  const {
    connectionStatus,
    currentProject,
    modes,
    artifacts,
    activities,
    attachments,
    resetModes,
    addToCommandHistory,
    setSelectedArtifact,
    addAttachment,
    removeAttachment,
    clearAttachments,
  } = useDashboardStore();

  const [commandInput, setCommandInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // ---- Helpers ----
  const runMode = useCallback(async (modeId: ModeId) => {
    await api.runMode(modeId);
  }, []);

  const openArtifact = useCallback(async (artifactId: string) => {
    const full = await api.getArtifact(artifactId);
    setSelectedArtifact(full);
  }, [setSelectedArtifact]);

  const handleCommand = useCallback(async (raw: string) => {
    const command = raw.trim();
    if (!command) return;
    setCommandInput("");
    addToCommandHistory(command);

    try {
      if (command === "/reset") {
        resetModes();
        toast.success("Pipeline reset");
        return;
      }
      if (command.startsWith("/run mode ")) {
        const modeId = command.replace("/run mode ", "").trim() as ModeId;
        await runMode(modeId);
        toast.success(`Running mode ${modeId}`);
        return;
      }
      if (command === "/status") {
        const running = modes.filter((m) => m.status === "running");
        toast(running.length ? `Running: ${running.map((m) => m.name).join(", ")}` : "No modes running");
        return;
      }
      if (command === "/artifacts") {
        toast(`${artifacts.length} artifacts available`);
        return;
      }
      await api.sendCommand(command);
      toast.success("Command sent");
    } catch {
      toast.error("Command failed");
    }
  }, [addToCommandHistory, resetModes, runMode, modes, artifacts.length]);

  const ingestFiles = useCallback(async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    try {
      for (const f of list) await addAttachment(f);
      toast.success(`Uploaded ${list.length} file(s)`);
    } catch {
      toast.error("Upload failed");
    }
  }, [addAttachment]);

  const onBrowseClick = () => fileInputRef.current?.click();
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const onDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) await ingestFiles(e.dataTransfer.files);
  };

  // ---- Quick Actions ----
  const quickCards: QuickCard[] = useMemo(() => [
    {
      id: "qa-eda",
      title: "Run Analysis",
      description: "Kick off Mode 0 (EDA) on your current project.",
      model: "gpt-oss",
      icon: <TrendingUp size={18} />,
      onRun: async () => { await runMode("0"); toast.success("Starting EDA"); },
    },
    {
      id: "qa-code",
      title: "Generate Code",
      description: "Run Mode 5 (Claude) to produce implementation.",
      model: "claude",
      icon: <Code size={18} />,
      onRun: async () => { await runMode("5"); toast.success("Starting code gen"); },
    },
    {
      id: "qa-reset",
      title: "Reset Pipeline",
      description: "Clear mode statuses for a clean run.",
      model: "gpt-oss",
      icon: <RotateCcw size={18} />,
      onRun: () => { resetModes(); toast.success("Pipeline reset"); },
    },
  ], [resetModes, runMode]);

  // Mode groupings
  const modeGroups = [
    { label: "Discovery", modes: ["0.5", "0", "1"] },
    { label: "Development", modes: ["2", "3", "4"] },
    { label: "Implementation", modes: ["5", "6", "6.5"] },
    { label: "Delivery", modes: ["7"] },
  ];

  const getModeInfo = (id: string) => modes.find((m) => m.id === id);
  const completedCount = modes.filter((m) => m.status === "completed").length;

  // ---- Styles ----
  const colors = {
    pageBg: "#f1f5f9",
    sidebarBg: "#ffffff",
    cardBg: "#ffffff",
    border: "#e2e8f0",
    text: "#1e293b",
    textMuted: "#64748b",
    textLight: "#94a3b8",
    primary: "#2563eb",
    primaryHover: "#1d4ed8",
    success: "#10b981",
    pillBlueBg: "#eff6ff",
    pillBlueText: "#1d4ed8",
    pillBlueBorder: "#bfdbfe",
    pillGreenBg: "#ecfdf5",
    pillGreenText: "#047857",
    pillGreenBorder: "#a7f3d0",
  };

  return (
    <div
      style={{ backgroundColor: colors.pageBg, color: colors.text, minHeight: "100vh" }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 50,
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            backgroundColor: "#fff", border: `2px solid ${colors.primary}`,
            borderRadius: 16, padding: "32px 48px", textAlign: "center",
          }}>
            <Upload size={48} color={colors.primary} style={{ marginBottom: 12 }} />
            <div style={{ fontWeight: 600, fontSize: 18 }}>Drop files to upload</div>
            <div style={{ color: colors.textMuted, fontSize: 14 }}>PDF, CSV, JSON, images</div>
          </div>
        </div>
      )}

      <div style={{ display: "flex", height: "100vh" }}>
        {/* LEFT SIDEBAR */}
        <aside style={{
          width: 260, backgroundColor: colors.sidebarBg,
          borderRight: `1px solid ${colors.border}`,
          display: "flex", flexDirection: "column", overflow: "hidden",
        }}>
          <div style={{ padding: 20 }}>
            {/* App Identity */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                backgroundColor: colors.primary, color: "#fff",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontWeight: 700, fontSize: 16,
              }}>M</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: colors.text }}>MERIDIAN</div>
                <div style={{ fontSize: 11, color: colors.textMuted }}>Intelligence Platform</div>
              </div>
            </div>

            {/* Status */}
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 24, fontSize: 12,
            }}>
              <span style={{ color: colors.textMuted }}>
                Status: <span style={{ color: colors.text, fontWeight: 500 }}>{connectionStatus || "—"}</span>
              </span>
              <span style={{
                backgroundColor: colors.pillBlueBg, color: colors.pillBlueText,
                border: `1px solid ${colors.pillBlueBorder}`,
                padding: "2px 8px", borderRadius: 12, fontSize: 10, fontWeight: 500,
              }}>API</span>
            </div>

            {/* Pipeline Nav */}
            <div style={{ fontSize: 12, fontWeight: 600, color: colors.text, marginBottom: 12 }}>
              Pipeline Progress
            </div>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "0 20px" }}>
            {modeGroups.map((group) => (
              <div key={group.label} style={{ marginBottom: 16 }}>
                <div style={{
                  fontSize: 10, fontWeight: 600, color: colors.textMuted,
                  textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8,
                }}>{group.label}</div>
                {group.modes.map((modeId) => {
                  const info = getModeInfo(modeId);
                  const isComplete = info?.status === "completed";
                  const isRunning = info?.status === "running";
                  return (
                    <div
                      key={modeId}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "6px 8px", borderRadius: 6, marginBottom: 2,
                        cursor: "pointer", fontSize: 13,
                        backgroundColor: isRunning ? colors.pillBlueBg : "transparent",
                      }}
                      onClick={() => runMode(modeId as ModeId)}
                    >
                      {isComplete ? (
                        <CheckCircle2 size={16} color={colors.success} />
                      ) : (
                        <Circle size={16} color={colors.textLight} />
                      )}
                      <span style={{ color: colors.text }}>
                        Mode {modeId}: {info?.name || modeId}
                        {modeId === "5" && <span style={{ color: colors.textMuted }}> (Claude)</span>}
                      </span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Session Stats */}
          <div style={{
            padding: 20, borderTop: `1px solid ${colors.border}`,
            fontSize: 12,
          }}>
            <div style={{ fontWeight: 600, color: colors.text, marginBottom: 12 }}>Session Stats</div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ color: colors.textMuted }}>Completed</span>
              <span style={{ fontWeight: 500 }}>{completedCount}/10</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ color: colors.textMuted }}>Artifacts</span>
              <span style={{ fontWeight: 500 }}>{artifacts.length}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: colors.textMuted }}>Project</span>
              <span style={{ fontWeight: 500, maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis" }}>
                {currentProject?.name || "—"}
              </span>
            </div>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main style={{ flex: 1, overflowY: "auto", padding: 24 }}>
          {/* Header row with model pills */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 24,
          }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>
                {currentProject?.name || "MERIDIAN Dashboard"}
              </h1>
              <p style={{ fontSize: 13, color: colors.textMuted, margin: "4px 0 0" }}>
                Mode execution, artifacts, and live activity
              </p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{
                backgroundColor: colors.pillGreenBg, color: colors.pillGreenText,
                border: `1px solid ${colors.pillGreenBorder}`,
                padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500,
              }}>GPT-OSS-120B (Analysis)</span>
              <span style={{
                backgroundColor: colors.pillBlueBg, color: colors.pillBlueText,
                border: `1px solid ${colors.pillBlueBorder}`,
                padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500,
              }}>Claude Opus (Code)</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ marginBottom: 24 }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              marginBottom: 16,
            }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Quick Actions</h2>
              <span style={{ fontSize: 12, color: colors.textMuted }}>Common workflows</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {quickCards.map((card) => (
                <div
                  key={card.id}
                  style={{
                    backgroundColor: colors.cardBg,
                    border: `1px solid ${colors.border}`,
                    borderRadius: 12, padding: 16,
                  }}
                >
                  <div style={{
                    display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                    marginBottom: 12,
                  }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8,
                      backgroundColor: colors.pageBg,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color: colors.textMuted,
                    }}>{card.icon}</div>
                    <span style={{
                      backgroundColor: card.model === "claude" ? colors.pillBlueBg : colors.pillGreenBg,
                      color: card.model === "claude" ? colors.pillBlueText : colors.pillGreenText,
                      border: `1px solid ${card.model === "claude" ? colors.pillBlueBorder : colors.pillGreenBorder}`,
                      padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 500,
                    }}>{card.model === "claude" ? "Claude" : "GPT-OSS"}</span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{card.title}</div>
                  <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 16, minHeight: 32 }}>
                    {card.description}
                  </div>
                  <button
                    onClick={async () => { try { await card.onRun(); } catch { toast.error("Failed"); } }}
                    style={{
                      width: "100%", padding: "8px 0",
                      backgroundColor: colors.primary, color: "#fff",
                      border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500,
                      cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    }}
                  >
                    <Play size={14} /> Run
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Attachments / Upload Zone */}
          <div style={{ marginBottom: 24 }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              marginBottom: 16,
            }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Attachments</h2>
              <div style={{ display: "flex", gap: 8 }}>
                {attachments && attachments.length > 0 && (
                  <button
                    onClick={() => { clearAttachments(); toast.success("Cleared"); }}
                    style={{
                      padding: "6px 12px", backgroundColor: colors.pageBg,
                      border: `1px solid ${colors.border}`, borderRadius: 6,
                      fontSize: 12, color: colors.text, cursor: "pointer",
                    }}
                  >Clear</button>
                )}
                <button
                  onClick={onBrowseClick}
                  style={{
                    padding: "6px 12px", backgroundColor: colors.primary,
                    border: "none", borderRadius: 6,
                    fontSize: 12, color: "#fff", cursor: "pointer", fontWeight: 500,
                  }}
                >Browse Files</button>
              </div>
            </div>
            
            {/* Drop Zone */}
            <div
              style={{
                backgroundColor: isDragging ? colors.pillBlueBg : colors.cardBg,
                border: `2px dashed ${isDragging ? colors.primary : colors.border}`,
                borderRadius: 12, padding: 24,
                transition: "all 0.2s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12,
                  backgroundColor: colors.pillBlueBg,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Upload size={24} color={colors.primary} />
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, color: colors.text }}>
                    Drag & drop files here
                  </div>
                  <div style={{ fontSize: 12, color: colors.textMuted, marginTop: 2 }}>
                    Or click <button 
                      onClick={onBrowseClick}
                      style={{ 
                        background: "none", border: "none", color: colors.primary, 
                        fontSize: 12, fontWeight: 500, cursor: "pointer", padding: 0,
                      }}
                    >Browse Files</button> to upload PDF, Word, TXT, MD, CSV, Excel, JPEG
                  </div>
                </div>
              </div>
            </div>

            {/* Attached Files List */}
            {attachments && attachments.length > 0 && (
              <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                {attachments.slice(0, 10).map((att: any) => (
                  <div
                    key={att.id || att.name}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`,
                      borderRadius: 8, padding: "10px 12px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 6,
                        backgroundColor: colors.pageBg,
                        display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        <Package size={16} color={colors.textMuted} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500, fontSize: 13, color: colors.text }}>{att.name}</div>
                        <div style={{ fontSize: 11, color: colors.textMuted }}>
                          {att.size ? `${(att.size / 1024).toFixed(1)} KB` : ""} 
                          {att.status ? ` • ${att.status}` : ""}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => removeAttachment(att.id)}
                      style={{
                        width: 28, height: 28, borderRadius: 6,
                        backgroundColor: colors.pageBg, border: "none",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        cursor: "pointer",
                      }}
                    >
                      <X size={14} color={colors.textMuted} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Artifacts */}
          <div style={{ marginBottom: 24 }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              marginBottom: 16,
            }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Recent Artifacts</h2>
              <span style={{ fontSize: 12, color: colors.textMuted }}>{artifacts.length} total</span>
            </div>
            <div style={{
              backgroundColor: colors.cardBg,
              border: `1px solid ${colors.border}`,
              borderRadius: 12, padding: 16,
            }}>
              {artifacts.length > 0 ? (
                <div>
                  {artifacts.slice(0, 5).map((art: any, i: number) => (
                    <div
                      key={art.id}
                      style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "10px 0",
                        borderBottom: i < Math.min(artifacts.length, 5) - 1 ? `1px solid ${colors.border}` : "none",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{
                          width: 32, height: 32, borderRadius: 8,
                          backgroundColor: colors.pageBg,
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          <Package size={16} color={colors.textMuted} />
                        </div>
                        <div>
                          <div style={{ fontWeight: 500, fontSize: 13 }}>{art.name}</div>
                          <div style={{ fontSize: 11, color: colors.textMuted }}>
                            Mode {art.modeId} • {art.createdAt ? new Date(art.createdAt).toLocaleTimeString() : "—"}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={async () => { try { await openArtifact(art.id); toast.success("Loaded"); } catch { toast.error("Failed"); } }}
                        style={{
                          background: "none", border: "none", color: colors.primary,
                          fontSize: 13, fontWeight: 500, cursor: "pointer",
                        }}
                      >View</button>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "20px 0", color: colors.textMuted, fontSize: 13 }}>
                  No artifacts yet
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
            <button
              onClick={async () => { await runMode("0"); toast.success("Starting analysis"); }}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", backgroundColor: colors.primary, color: "#fff",
                border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
              }}
            >
              <TrendingUp size={16} /> Run Analysis
            </button>
            <button
              onClick={async () => { await runMode("5"); toast.success("Starting code gen"); }}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", backgroundColor: colors.primary, color: "#fff",
                border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
              }}
            >
              <Code size={16} /> Generate Code
            </button>
            <button
              onClick={() => { resetModes(); toast.success("Reset"); }}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", backgroundColor: colors.pageBg, color: colors.text,
                border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
              }}
            >
              <RotateCcw size={16} /> Reset Pipeline
            </button>
          </div>

          {/* Command Input */}
          <div>
            <div style={{
              display: "flex", alignItems: "center", gap: 12,
              backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`,
              borderRadius: 10, padding: "4px 4px 4px 16px",
            }}>
              <input
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCommand(commandInput)}
                placeholder="Type a MERIDIAN command or describe what you want to analyze..."
                style={{
                  flex: 1, border: "none", outline: "none", fontSize: 13,
                  backgroundColor: "transparent", color: colors.text,
                }}
              />
              <button
                onClick={() => handleCommand(commandInput)}
                style={{
                  padding: "8px 16px", backgroundColor: colors.primary, color: "#fff",
                  border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 6,
                }}
              >
                <Send size={14} /> Send
              </button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, fontSize: 12 }}>
              <span style={{ color: colors.textMuted }}>Suggestions:</span>
              {["/status", "/run mode 3", "/artifacts"].map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => setCommandInput(cmd)}
                  style={{
                    padding: "4px 10px", backgroundColor: colors.pageBg,
                    border: `1px solid ${colors.border}`, borderRadius: 14,
                    fontSize: 11, color: colors.text, cursor: "pointer",
                  }}
                >{cmd}</button>
              ))}
            </div>
          </div>
        </main>

        {/* RIGHT SIDEBAR - Live Activity */}
        <aside style={{
          width: 280, backgroundColor: colors.sidebarBg,
          borderLeft: `1px solid ${colors.border}`,
          display: "flex", flexDirection: "column",
        }}>
          <div style={{ padding: 20 }}>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 16,
            }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Live Activity</h2>
              <span style={{
                backgroundColor: colors.pillBlueBg, color: colors.pillBlueText,
                border: `1px solid ${colors.pillBlueBorder}`,
                padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 500,
              }}>Live</span>
            </div>
            <p style={{ fontSize: 12, color: colors.textMuted, margin: "0 0 16px" }}>
              Real-time pipeline updates and events
            </p>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "0 20px 20px" }}>
            {activities?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {activities.slice(0, 20).map((a: any) => (
                  <div
                    key={a.id || `${a.timestamp}-${a.type}`}
                    style={{
                      backgroundColor: colors.pageBg, borderRadius: 8, padding: 12,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <Activity size={14} color={colors.textMuted} style={{ marginTop: 2 }} />
                      <div>
                        <div style={{ fontSize: 12, color: colors.text }}>{a.content || a.type}</div>
                        <div style={{ fontSize: 10, color: colors.textLight, marginTop: 4 }}>
                          {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : ""}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{
                backgroundColor: colors.pageBg, borderRadius: 8, padding: 24,
                textAlign: "center", color: colors.textMuted, fontSize: 13,
              }}>
                No activity yet
              </div>
            )}
          </div>
        </aside>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.jpeg,.jpg,.png,.gif"
        style={{ display: "none" }}
        onChange={async (e) => {
          if (e.target.files?.length) {
            await ingestFiles(e.target.files);
            e.target.value = "";
          }
        }}
      />
    </div>
  );
}

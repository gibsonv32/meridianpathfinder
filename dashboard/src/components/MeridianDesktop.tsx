import React, { useMemo, useRef, useState, useCallback, useEffect } from "react";
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
  Send,
  FileText,
  FileSpreadsheet,
  FileImage,
  File,
  ChevronRight,
  Loader2,
  Table,
  ArrowRight,
  Search,
  Command,
  Clock,
  Pause,
  RefreshCw,
  Download,
  Copy,
} from "lucide-react";

import { useDashboardStore } from "../store";
import { useWebSocket } from "../hooks/useWebSocket";
import { api } from "../api/client";
import type { ModeId, ModeStatus } from "../types";

type QuickCard = {
  id: string;
  title: string;
  description: string;
  model: "claude" | "gpt-oss";
  icon: React.ReactNode;
  onRun: () => Promise<void> | void;
};

type FilePreview = {
  name: string;
  type: string;
  size: number;
  preview?: {
    headers?: string[];
    rows?: string[][];
    rowCount?: number;
    colCount?: number;
    text?: string;
    imageUrl?: string;
  };
};

type DrawerContent = 
  | { type: "mode"; modeId: string }
  | { type: "artifact"; artifact: any }
  | null;

type CommandItem = {
  id: string;
  icon: React.ReactNode;
  label: string;
  description: string;
  shortcut?: string;
  action: () => void;
  category: "actions" | "modes" | "navigation" | "recent";
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
    commandHistory,
    resetModes,
    addToCommandHistory,
    setSelectedArtifact,
    addAttachment,
    removeAttachment,
    clearAttachments,
  } = useDashboardStore();

  const [commandInput, setCommandInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [filePreviews, setFilePreviews] = useState<FilePreview[]>([]);
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [drawerContent, setDrawerContent] = useState<DrawerContent>(null);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [paletteSearch, setPaletteSearch] = useState("");
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const [modeProgress] = useState<Record<string, number>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const paletteInputRef = useRef<HTMLInputElement | null>(null);

  // Keyboard shortcut for Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(true);
        setPaletteSearch("");
        setSelectedCommandIndex(0);
      }
      if (e.key === "Escape") {
        setCommandPaletteOpen(false);
        setDrawerContent(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus palette input when opened
  useEffect(() => {
    if (commandPaletteOpen && paletteInputRef.current) {
      paletteInputRef.current.focus();
    }
  }, [commandPaletteOpen]);

  // ---- Helpers ----
  const runMode = useCallback(async (modeId: ModeId) => {
    await api.runMode(modeId);
  }, []);

  const openArtifact = useCallback(async (artifactId: string) => {
    const full = await api.getArtifact(artifactId);
    setSelectedArtifact(full);
    setDrawerContent({ type: "artifact", artifact: full });
  }, [setSelectedArtifact]);

  const openModeDetail = useCallback((modeId: string) => {
    setDrawerContent({ type: "mode", modeId });
  }, []);

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
      // Generic command - just show feedback
      toast.success("Command received");
    } catch {
      toast.error("Command failed");
    }
  }, [addToCommandHistory, resetModes, runMode, modes, artifacts.length]);

  // Parse CSV
  const parseCSV = (text: string): { headers: string[]; rows: string[][]; rowCount: number } => {
    const lines = text.split('\n').filter(l => l.trim());
    const headers = lines[0]?.split(',').map(h => h.trim().replace(/^"|"$/g, '')) || [];
    const rows = lines.slice(1, 6).map(line => 
      line.split(',').map(cell => cell.trim().replace(/^"|"$/g, ''))
    );
    return { headers, rows, rowCount: lines.length - 1 };
  };

  const generatePreview = useCallback(async (file: File): Promise<FilePreview> => {
    const preview: FilePreview = { name: file.name, type: file.type || getFileType(file.name), size: file.size };
    const ext = file.name.split('.').pop()?.toLowerCase();

    if (ext === 'csv') {
      const text = await file.text();
      const parsed = parseCSV(text);
      preview.preview = { headers: parsed.headers, rows: parsed.rows, rowCount: parsed.rowCount, colCount: parsed.headers.length };
    } else if (['txt', 'md'].includes(ext || '')) {
      const text = await file.text();
      preview.preview = { text: text.slice(0, 500) + (text.length > 500 ? '...' : '') };
    } else if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) {
      preview.preview = { imageUrl: URL.createObjectURL(file) };
    } else if (['pdf', 'doc', 'docx', 'xlsx', 'xls'].includes(ext || '')) {
      preview.preview = { text: `${ext?.toUpperCase()} document - ${formatBytes(file.size)}` };
    }
    return preview;
  }, []);

  const getFileType = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const types: Record<string, string> = {
      csv: 'text/csv', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      pdf: 'application/pdf', txt: 'text/plain', md: 'text/markdown',
      jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
    };
    return types[ext || ''] || 'application/octet-stream';
  };

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['csv', 'xlsx', 'xls'].includes(ext || '')) return <FileSpreadsheet size={18} />;
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) return <FileImage size={18} />;
    if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext || '')) return <FileText size={18} />;
    return <File size={18} />;
  };

  const ingestFiles = useCallback(async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    try {
      const previews: FilePreview[] = [];
      for (const f of list) {
        // Create attachment object from file
        const attachment = {
          id: `att-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          file: f,
          name: f.name,
          type: f.type,
          size: f.size,
          status: 'success' as const,
          progress: 100,
        };
        addAttachment(attachment);
        const preview = await generatePreview(f);
        previews.push(preview);
      }
      setFilePreviews(prev => [...prev, ...previews]);
      toast.success(`Uploaded ${list.length} file(s)`);
    } catch { toast.error("Upload failed"); }
  }, [addAttachment, generatePreview]);

  const removeFile = useCallback((filename: string, attachmentId?: string) => {
    if (attachmentId) removeAttachment(attachmentId);
    setFilePreviews(prev => prev.filter(p => p.name !== filename));
  }, [removeAttachment]);

  const clearAllFiles = useCallback(() => {
    clearAttachments();
    setFilePreviews([]);
    toast.success("Cleared all files");
  }, [clearAttachments]);

  const onBrowseClick = () => fileInputRef.current?.click();
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const onDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) await ingestFiles(e.dataTransfer.files);
  };

  // Quick Actions
  const quickCards: QuickCard[] = useMemo(() => [
    { id: "qa-eda", title: "Run Analysis", description: "Kick off Mode 0 (EDA) on your current project.", model: "gpt-oss", icon: <TrendingUp size={18} />, onRun: async () => { await runMode("0"); toast.success("Starting EDA"); } },
    { id: "qa-code", title: "Generate Code", description: "Run Mode 5 (Claude) to produce implementation.", model: "claude", icon: <Code size={18} />, onRun: async () => { await runMode("5"); toast.success("Starting code gen"); } },
    { id: "qa-reset", title: "Reset Pipeline", description: "Clear mode statuses for a clean run.", model: "gpt-oss", icon: <RotateCcw size={18} />, onRun: () => { resetModes(); setFilePreviews([]); toast.success("Pipeline reset"); } },
  ], [resetModes, runMode]);

  // Pipeline phases
  const pipelinePhases = [
    { name: "Discovery", modes: [{ id: "0.5", name: "Opportunity" }, { id: "0", name: "EDA" }, { id: "1", name: "Decision Intel" }] },
    { name: "Development", modes: [{ id: "2", name: "Feasibility" }, { id: "3", name: "Strategy" }, { id: "4", name: "Business Case" }] },
    { name: "Implementation", modes: [{ id: "5", name: "Code Gen", llm: "claude" }, { id: "6", name: "Execution" }, { id: "6.5", name: "Interpretation" }] },
    { name: "Delivery", modes: [{ id: "7", name: "Delivery" }] },
  ];

  const getModeStatus = (modeId: string): ModeStatus | "idle" => {
    const mode = modes.find(m => m.id === modeId);
    return mode?.status || "idle";
  };
  
  const getModeProgress = (modeId: string): number => modeProgress[modeId] || 0;
  const completedCount = modes.filter((m) => m.status === "completed").length;
  const runningMode = modes.find(m => m.status === "running");

  // Command Palette items
  const commandItems: CommandItem[] = useMemo(() => {
    const items: CommandItem[] = [
      { id: "run-analysis", icon: <TrendingUp size={16} />, label: "Run Analysis", description: "Start Mode 0 (EDA)", action: async () => { await runMode("0"); toast.success("Starting EDA"); setCommandPaletteOpen(false); }, category: "actions" },
      { id: "generate-code", icon: <Code size={16} />, label: "Generate Code", description: "Start Mode 5 (Claude)", action: async () => { await runMode("5"); toast.success("Starting code gen"); setCommandPaletteOpen(false); }, category: "actions" },
      { id: "reset-pipeline", icon: <RotateCcw size={16} />, label: "Reset Pipeline", description: "Clear all mode statuses", action: () => { resetModes(); setFilePreviews([]); toast.success("Pipeline reset"); setCommandPaletteOpen(false); }, category: "actions" },
      { id: "upload-files", icon: <Upload size={16} />, label: "Upload Files", description: "Browse for files to upload", action: () => { onBrowseClick(); setCommandPaletteOpen(false); }, category: "actions" },
      ...pipelinePhases.flatMap(phase => phase.modes.map(mode => ({
        id: `mode-${mode.id}`,
        icon: <Play size={16} />,
        label: `Run Mode ${mode.id}: ${mode.name}`,
        description: `Execute ${mode.name} mode`,
        action: async () => { await runMode(mode.id as ModeId); toast.success(`Starting ${mode.name}`); setCommandPaletteOpen(false); },
        category: "modes" as const,
      }))),
      { id: "view-artifacts", icon: <Package size={16} />, label: "View Artifacts", description: `${artifacts.length} artifacts available`, action: () => { toast(`${artifacts.length} artifacts`); setCommandPaletteOpen(false); }, category: "navigation" },
      { id: "check-status", icon: <Activity size={16} />, label: "Check Status", description: "View pipeline status", action: () => { const running = modes.filter(m => m.status === "running"); toast(running.length ? `Running: ${running.map(m => m.name).join(", ")}` : "No modes running"); setCommandPaletteOpen(false); }, category: "navigation" },
    ];

    const recentItems: CommandItem[] = (commandHistory || []).slice(0, 5).map((cmd, i) => ({
      id: `recent-${i}`,
      icon: <Clock size={16} />,
      label: cmd,
      description: "Recent command",
      action: async () => { await handleCommand(cmd); setCommandPaletteOpen(false); },
      category: "recent" as const,
    }));

    return [...items, ...recentItems];
  }, [runMode, resetModes, artifacts.length, modes, commandHistory, handleCommand]);

  const filteredCommands = useMemo(() => {
    if (!paletteSearch) return commandItems;
    const search = paletteSearch.toLowerCase();
    return commandItems.filter(item => 
      item.label.toLowerCase().includes(search) || 
      item.description.toLowerCase().includes(search)
    );
  }, [commandItems, paletteSearch]);

  const handlePaletteKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedCommandIndex(i => Math.min(i + 1, filteredCommands.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedCommandIndex(i => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filteredCommands[selectedCommandIndex]) {
      e.preventDefault();
      filteredCommands[selectedCommandIndex].action();
    }
  };

  // Colors
  const colors = {
    pageBg: "#f1f5f9", sidebarBg: "#ffffff", cardBg: "#ffffff", border: "#e2e8f0",
    text: "#1e293b", textMuted: "#64748b", textLight: "#94a3b8",
    primary: "#2563eb", primaryHover: "#1d4ed8", success: "#10b981", warning: "#f59e0b", error: "#ef4444",
    pillBlueBg: "#eff6ff", pillBlueText: "#1d4ed8", pillBlueBorder: "#bfdbfe",
    pillGreenBg: "#ecfdf5", pillGreenText: "#047857", pillGreenBorder: "#a7f3d0",
  };

  // Get mode detail for drawer
  const getDrawerModeData = () => {
    if (drawerContent?.type !== "mode") return null;
    const modeId = drawerContent.modeId;
    const phaseInfo = pipelinePhases.flatMap(p => p.modes.map(m => ({ ...m, phase: p.name }))).find(m => m.id === modeId);
    return { modeId, phaseInfo };
  };

  return (
    <div style={{ backgroundColor: colors.pageBg, color: colors.text, minHeight: "100vh" }} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
      
      {/* Command Palette Modal */}
      {commandPaletteOpen && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "flex-start", justifyContent: "center", paddingTop: 100 }} onClick={() => setCommandPaletteOpen(false)}>
          <div style={{ position: "absolute", inset: 0, backgroundColor: "rgba(0,0,0,0.4)" }} />
          <div onClick={e => e.stopPropagation()} style={{ position: "relative", width: 560, maxHeight: "60vh", backgroundColor: colors.cardBg, borderRadius: 16, boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
            <div style={{ padding: 16, borderBottom: `1px solid ${colors.border}`, display: "flex", alignItems: "center", gap: 12 }}>
              <Search size={20} color={colors.textMuted} />
              <input
                ref={paletteInputRef}
                type="text"
                value={paletteSearch}
                onChange={e => { setPaletteSearch(e.target.value); setSelectedCommandIndex(0); }}
                onKeyDown={handlePaletteKeyDown}
                placeholder="Search commands, modes, or type a command..."
                style={{ flex: 1, border: "none", outline: "none", fontSize: 15, backgroundColor: "transparent", color: colors.text }}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", backgroundColor: colors.pageBg, borderRadius: 6, fontSize: 11, color: colors.textMuted }}>
                <Command size={12} /> K
              </div>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
              {["actions", "modes", "navigation", "recent"].map(category => {
                const items = filteredCommands.filter(c => c.category === category);
                if (!items.length) return null;
                return (
                  <div key={category} style={{ marginBottom: 8 }}>
                    <div style={{ padding: "8px 12px", fontSize: 11, fontWeight: 600, color: colors.textMuted, textTransform: "uppercase" }}>
                      {category === "recent" ? "Recent" : category === "modes" ? "Run Modes" : category === "actions" ? "Quick Actions" : "Navigation"}
                    </div>
                    {items.map((item) => {
                      const globalIdx = filteredCommands.indexOf(item);
                      const isSelected = globalIdx === selectedCommandIndex;
                      return (
                        <div
                          key={item.id}
                          onClick={item.action}
                          onMouseEnter={() => setSelectedCommandIndex(globalIdx)}
                          style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 12px", borderRadius: 8, cursor: "pointer", backgroundColor: isSelected ? colors.pillBlueBg : "transparent" }}
                        >
                          <div style={{ width: 32, height: 32, borderRadius: 8, backgroundColor: isSelected ? colors.primary : colors.pageBg, display: "flex", alignItems: "center", justifyContent: "center", color: isSelected ? "#fff" : colors.textMuted }}>{item.icon}</div>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 14, fontWeight: 500, color: colors.text }}>{item.label}</div>
                            <div style={{ fontSize: 12, color: colors.textMuted }}>{item.description}</div>
                          </div>
                          {item.shortcut && <div style={{ fontSize: 11, color: colors.textLight, padding: "2px 6px", backgroundColor: colors.pageBg, borderRadius: 4 }}>{item.shortcut}</div>}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
              {filteredCommands.length === 0 && <div style={{ padding: 24, textAlign: "center", color: colors.textMuted }}>No results found</div>}
            </div>
            <div style={{ padding: "12px 16px", borderTop: `1px solid ${colors.border}`, display: "flex", alignItems: "center", gap: 16, fontSize: 11, color: colors.textMuted }}>
              <span>↑↓ Navigate</span><span>↵ Select</span><span>Esc Close</span>
            </div>
          </div>
        </div>
      )}

      {/* Detail Drawer */}
      {drawerContent && (
        <div style={{ position: "fixed", inset: 0, zIndex: 90, display: "flex", justifyContent: "flex-end" }} onClick={() => setDrawerContent(null)}>
          <div style={{ position: "absolute", inset: 0, backgroundColor: "rgba(0,0,0,0.3)" }} />
          <div onClick={e => e.stopPropagation()} style={{ position: "relative", width: 480, height: "100%", backgroundColor: colors.cardBg, boxShadow: "-4px 0 20px rgba(0,0,0,0.1)", display: "flex", flexDirection: "column" }}>
            <div style={{ padding: 20, borderBottom: `1px solid ${colors.border}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>{drawerContent.type === "mode" ? `Mode ${drawerContent.modeId}` : "Artifact Details"}</h2>
              <button onClick={() => setDrawerContent(null)} style={{ width: 32, height: 32, borderRadius: 8, backgroundColor: colors.pageBg, border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}><X size={18} color={colors.textMuted} /></button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
              {drawerContent.type === "mode" && (() => {
                const data = getDrawerModeData();
                if (!data) return null;
                const { modeId, phaseInfo } = data;
                const status = getModeStatus(modeId);
                const progress = getModeProgress(modeId);
                const isRunning = status === "running";
                const isCompleted = status === "completed";
                const isError = status === "failed";

                return (
                  <div>
                    <div style={{ marginBottom: 24 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                        <div style={{ width: 48, height: 48, borderRadius: 12, backgroundColor: isCompleted ? colors.success : isRunning ? colors.primary : isError ? colors.error : colors.pageBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          {isCompleted ? <CheckCircle2 size={24} color="#fff" /> : isRunning ? <Loader2 size={24} color="#fff" style={{ animation: "spin 1s linear infinite" }} /> : isError ? <AlertTriangle size={24} color="#fff" /> : <Circle size={24} color={colors.textLight} />}
                        </div>
                        <div>
                          <div style={{ fontSize: 18, fontWeight: 600 }}>{phaseInfo?.name || `Mode ${modeId}`}</div>
                          <div style={{ fontSize: 13, color: colors.textMuted }}>{phaseInfo?.phase} Phase</div>
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                        <span style={{ padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500, backgroundColor: isCompleted ? colors.pillGreenBg : isRunning ? colors.pillBlueBg : isError ? "#fef2f2" : colors.pageBg, color: isCompleted ? colors.pillGreenText : isRunning ? colors.pillBlueText : isError ? colors.error : colors.textMuted, border: `1px solid ${isCompleted ? colors.pillGreenBorder : isRunning ? colors.pillBlueBorder : isError ? "#fecaca" : colors.border}` }}>{String(status).charAt(0).toUpperCase() + String(status).slice(1)}</span>
                        {(phaseInfo as any)?.llm === "claude" && <span style={{ padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500, backgroundColor: colors.pillBlueBg, color: colors.pillBlueText, border: `1px solid ${colors.pillBlueBorder}` }}>Claude</span>}
                      </div>
                      {isRunning && (
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}><span style={{ color: colors.textMuted }}>Progress</span><span style={{ fontWeight: 500 }}>{progress}%</span></div>
                          <div style={{ height: 8, backgroundColor: colors.pageBg, borderRadius: 4, overflow: "hidden" }}><div style={{ height: "100%", width: `${progress}%`, backgroundColor: colors.primary, borderRadius: 4, transition: "width 0.3s ease" }} /></div>
                        </div>
                      )}
                    </div>
                    <div style={{ marginBottom: 24 }}>
                      <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: colors.textMuted }}>Description</h3>
                      <p style={{ fontSize: 14, color: colors.text, lineHeight: 1.6, margin: 0 }}>{getModeDescription(modeId)}</p>
                    </div>
                    <div style={{ marginBottom: 24 }}>
                      <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: colors.textMuted }}>Expected Outputs</h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {getModeOutputs(modeId).map((output, i) => (
                          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", backgroundColor: colors.pageBg, borderRadius: 8 }}><Package size={14} color={colors.textMuted} /><span style={{ fontSize: 13 }}>{output}</span></div>
                        ))}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      {!isRunning && <button onClick={async () => { await runMode(modeId as ModeId); toast.success(`Starting mode ${modeId}`); }} style={{ flex: 1, padding: "10px 16px", backgroundColor: colors.primary, color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><Play size={16} /> Run Mode</button>}
                      {isRunning && <button onClick={() => toast("Stop not implemented")} style={{ flex: 1, padding: "10px 16px", backgroundColor: colors.warning, color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><Pause size={16} /> Stop</button>}
                      {isCompleted && <button onClick={() => toast("Re-run not implemented")} style={{ flex: 1, padding: "10px 16px", backgroundColor: colors.pageBg, color: colors.text, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><RefreshCw size={16} /> Re-run</button>}
                    </div>
                  </div>
                );
              })()}

              {drawerContent.type === "artifact" && (
                <div>
                  <div style={{ marginBottom: 24 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                      <div style={{ width: 48, height: 48, borderRadius: 12, backgroundColor: colors.pillBlueBg, display: "flex", alignItems: "center", justifyContent: "center" }}><Package size={24} color={colors.primary} /></div>
                      <div>
                        <div style={{ fontSize: 18, fontWeight: 600 }}>{drawerContent.artifact?.name || "Artifact"}</div>
                        <div style={{ fontSize: 13, color: colors.textMuted }}>Mode {drawerContent.artifact?.modeId}</div>
                      </div>
                    </div>
                  </div>
                  <div style={{ marginBottom: 24 }}>
                    <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: colors.textMuted }}>Content</h3>
                    <div style={{ backgroundColor: colors.pageBg, borderRadius: 8, padding: 16, maxHeight: 400, overflowY: "auto" }}>
                      <pre style={{ fontSize: 12, fontFamily: "monospace", margin: 0, whiteSpace: "pre-wrap", color: colors.text }}>{drawerContent.artifact?.content || "No content available"}</pre>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => { navigator.clipboard.writeText(drawerContent.artifact?.content || ""); toast.success("Copied!"); }} style={{ flex: 1, padding: "10px 16px", backgroundColor: colors.pageBg, color: colors.text, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><Copy size={16} /> Copy</button>
                    <button onClick={() => toast("Download not implemented")} style={{ flex: 1, padding: "10px 16px", backgroundColor: colors.primary, color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><Download size={16} /> Download</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Drag overlay */}
      {isDragging && (
        <div style={{ position: "fixed", inset: 0, zIndex: 50, backgroundColor: "rgba(37, 99, 235, 0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ backgroundColor: "#fff", border: `2px solid ${colors.primary}`, borderRadius: 16, padding: "32px 48px", textAlign: "center" }}>
            <Upload size={48} color={colors.primary} style={{ marginBottom: 12 }} />
            <div style={{ fontWeight: 600, fontSize: 18 }}>Drop files to upload</div>
          </div>
        </div>
      )}

      <div style={{ display: "flex", height: "100vh" }}>
        {/* LEFT SIDEBAR */}
        <aside style={{ width: 280, backgroundColor: colors.sidebarBg, borderRight: `1px solid ${colors.border}`, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: colors.primary, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 16 }}>M</div>
              <div><div style={{ fontWeight: 600, fontSize: 14 }}>MERIDIAN</div><div style={{ fontSize: 11, color: colors.textMuted }}>Intelligence Platform</div></div>
            </div>
            <button onClick={() => setCommandPaletteOpen(true)} style={{ width: "100%", padding: "10px 12px", backgroundColor: colors.pageBg, border: `1px solid ${colors.border}`, borderRadius: 8, display: "flex", alignItems: "center", gap: 10, cursor: "pointer", marginBottom: 20 }}>
              <Search size={16} color={colors.textMuted} />
              <span style={{ flex: 1, textAlign: "left", fontSize: 13, color: colors.textMuted }}>Search...</span>
              <div style={{ display: "flex", alignItems: "center", gap: 2, padding: "2px 6px", backgroundColor: colors.cardBg, borderRadius: 4, fontSize: 10, color: colors.textLight }}><Command size={10} /> K</div>
            </button>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, fontSize: 12 }}>
              <span style={{ color: colors.textMuted }}>Status: <span style={{ color: colors.text, fontWeight: 500 }}>{connectionStatus || "—"}</span></span>
              <span style={{ backgroundColor: colors.pillBlueBg, color: colors.pillBlueText, border: `1px solid ${colors.pillBlueBorder}`, padding: "2px 8px", borderRadius: 12, fontSize: 10, fontWeight: 500 }}>API</span>
            </div>
            <div style={{ backgroundColor: colors.pageBg, borderRadius: 10, padding: 12, marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}><span style={{ fontSize: 12, fontWeight: 600 }}>Pipeline Progress</span><span style={{ fontSize: 12, color: colors.textMuted }}>{completedCount}/10</span></div>
              <div style={{ height: 6, backgroundColor: colors.border, borderRadius: 3, overflow: "hidden" }}><div style={{ height: "100%", width: `${(completedCount / 10) * 100}%`, backgroundColor: colors.success, borderRadius: 3, transition: "width 0.3s ease" }} /></div>
              {runningMode && <div style={{ marginTop: 8, fontSize: 11, color: colors.primary, display: "flex", alignItems: "center", gap: 6 }}><Loader2 size={12} style={{ animation: "spin 1s linear infinite" }} />Running: {runningMode.name}</div>}
            </div>
          </div>

          {/* Pipeline Flowchart */}
          <div style={{ flex: 1, overflowY: "auto", padding: "0 20px 20px" }}>
            {pipelinePhases.map((phase, phaseIdx) => (
              <div key={phase.name} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 16, height: 16, borderRadius: 4, backgroundColor: colors.pageBg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 700 }}>{phaseIdx + 1}</span>
                  {phase.name}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {phase.modes.map((mode, modeIdx) => {
                    const status = getModeStatus(mode.id);
                    const progress = getModeProgress(mode.id);
                    const isRunning = status === "running";
                    const isCompleted = status === "completed";
                    const isError = status === "failed";

                    return (
                      <div key={mode.id}>
                        <div
                          onClick={() => openModeDetail(mode.id)}
                          style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 8, cursor: "pointer", transition: "all 0.15s ease", backgroundColor: isRunning ? colors.pillBlueBg : isCompleted ? colors.pillGreenBg : isError ? "#fef2f2" : colors.cardBg, border: `1px solid ${isRunning ? colors.pillBlueBorder : isCompleted ? colors.pillGreenBorder : isError ? "#fecaca" : colors.border}` }}
                        >
                          <div style={{ width: 24, height: 24, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: isCompleted ? colors.success : isRunning ? colors.primary : isError ? colors.error : colors.pageBg }}>
                            {isCompleted ? <CheckCircle2 size={14} color="#fff" /> : isRunning ? <Loader2 size={14} color="#fff" style={{ animation: "spin 1s linear infinite" }} /> : isError ? <AlertTriangle size={14} color="#fff" /> : <Circle size={14} color={colors.textLight} />}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
                              <span>{mode.id}: {mode.name}</span>
                              {(mode as any).llm === "claude" && <span style={{ fontSize: 9, padding: "1px 4px", borderRadius: 4, backgroundColor: colors.pillBlueBg, color: colors.pillBlueText }}>Claude</span>}
                            </div>
                            {isRunning && (
                              <div style={{ marginTop: 4 }}>
                                <div style={{ height: 3, backgroundColor: "rgba(37,99,235,0.2)", borderRadius: 2, overflow: "hidden" }}><div style={{ height: "100%", width: `${progress}%`, backgroundColor: colors.primary, transition: "width 0.3s ease" }} /></div>
                                <div style={{ fontSize: 10, color: colors.primary, marginTop: 2 }}>{progress}%</div>
                              </div>
                            )}
                          </div>
                          <ChevronRight size={14} color={colors.textMuted} />
                        </div>
                        {modeIdx < phase.modes.length - 1 && <div style={{ width: 2, height: 8, backgroundColor: colors.border, marginLeft: 21, marginTop: 2, marginBottom: 2 }} />}
                      </div>
                    );
                  })}
                </div>
                {phaseIdx < pipelinePhases.length - 1 && <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "8px 0" }}><ArrowRight size={16} color={colors.textLight} /></div>}
              </div>
            ))}
          </div>

          <div style={{ padding: 16, borderTop: `1px solid ${colors.border}`, fontSize: 11 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}><span style={{ color: colors.textMuted }}>Artifacts</span><span style={{ fontWeight: 500 }}>{artifacts.length}</span></div>
            <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: colors.textMuted }}>Project</span><span style={{ fontWeight: 500, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis" }}>{currentProject?.name || "—"}</span></div>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main style={{ flex: 1, overflowY: "auto", padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
            <div><h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>{currentProject?.name || "MERIDIAN Dashboard"}</h1><p style={{ fontSize: 13, color: colors.textMuted, margin: "4px 0 0" }}>Mode execution, artifacts, and live activity</p></div>
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ backgroundColor: colors.pillGreenBg, color: colors.pillGreenText, border: `1px solid ${colors.pillGreenBorder}`, padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500 }}>GPT-OSS-120B</span>
              <span style={{ backgroundColor: colors.pillBlueBg, color: colors.pillBlueText, border: `1px solid ${colors.pillBlueBorder}`, padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500 }}>Claude Opus</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}><h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Quick Actions</h2><span style={{ fontSize: 12, color: colors.textMuted }}>Common workflows</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {quickCards.map((card) => (
                <div key={card.id} style={{ backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 8, backgroundColor: colors.pageBg, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textMuted }}>{card.icon}</div>
                    <span style={{ backgroundColor: card.model === "claude" ? colors.pillBlueBg : colors.pillGreenBg, color: card.model === "claude" ? colors.pillBlueText : colors.pillGreenText, border: `1px solid ${card.model === "claude" ? colors.pillBlueBorder : colors.pillGreenBorder}`, padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 500 }}>{card.model === "claude" ? "Claude" : "GPT-OSS"}</span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{card.title}</div>
                  <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 16, minHeight: 32 }}>{card.description}</div>
                  <button onClick={async () => { try { await card.onRun(); } catch { toast.error("Failed"); } }} style={{ width: "100%", padding: "8px 0", backgroundColor: colors.primary, color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}><Play size={14} /> Run</button>
                </div>
              ))}
            </div>
          </div>

          {/* Data Files */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Data Files</h2>
              <div style={{ display: "flex", gap: 8 }}>
                {filePreviews.length > 0 && <button onClick={clearAllFiles} style={{ padding: "6px 12px", backgroundColor: colors.pageBg, border: `1px solid ${colors.border}`, borderRadius: 6, fontSize: 12, cursor: "pointer" }}>Clear All</button>}
                <button onClick={onBrowseClick} style={{ padding: "6px 12px", backgroundColor: colors.primary, border: "none", borderRadius: 6, fontSize: 12, color: "#fff", cursor: "pointer", fontWeight: 500 }}>Browse Files</button>
              </div>
            </div>
            
            {filePreviews.length === 0 && (
              <div style={{ backgroundColor: isDragging ? colors.pillBlueBg : colors.cardBg, border: `2px dashed ${isDragging ? colors.primary : colors.border}`, borderRadius: 12, padding: 32, transition: "all 0.2s ease", textAlign: "center" }}>
                <div style={{ width: 56, height: 56, borderRadius: 14, margin: "0 auto 16px", backgroundColor: colors.pillBlueBg, display: "flex", alignItems: "center", justifyContent: "center" }}><Upload size={28} color={colors.primary} /></div>
                <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>Drag & drop files here</div>
                <div style={{ fontSize: 13, color: colors.textMuted, marginBottom: 16 }}>or click <button onClick={onBrowseClick} style={{ background: "none", border: "none", color: colors.primary, fontSize: 13, fontWeight: 500, cursor: "pointer", padding: 0 }}>Browse Files</button></div>
                <div style={{ fontSize: 11, color: colors.textLight }}>Supports PDF, Word, TXT, MD, CSV, Excel, JPEG, PNG</div>
              </div>
            )}

            {filePreviews.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {filePreviews.map((file) => {
                  const attachment = attachments?.find(a => a.name === file.name);
                  const isExpanded = expandedFile === file.name;
                  return (
                    <div key={file.name} style={{ backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 12, overflow: "hidden" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", cursor: "pointer" }} onClick={() => setExpandedFile(isExpanded ? null : file.name)}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                          <div style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: colors.pageBg, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textMuted }}>{getFileIcon(file.name)}</div>
                          <div>
                            <div style={{ fontWeight: 500, fontSize: 14 }}>{file.name}</div>
                            <div style={{ fontSize: 12, color: colors.textMuted, display: "flex", gap: 8 }}>
                              <span>{formatBytes(file.size)}</span>
                              {file.preview?.rowCount && <span>• {file.preview.rowCount.toLocaleString()} rows</span>}
                              {file.preview?.colCount && <span>• {file.preview.colCount} cols</span>}
                            </div>
                          </div>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <button onClick={(e) => { e.stopPropagation(); removeFile(file.name, attachment?.id); }} style={{ width: 32, height: 32, borderRadius: 6, backgroundColor: colors.pageBg, border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}><X size={16} color={colors.textMuted} /></button>
                          <ChevronRight size={18} color={colors.textMuted} style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0)", transition: "transform 0.2s ease" }} />
                        </div>
                      </div>
                      {isExpanded && file.preview && (
                        <div style={{ borderTop: `1px solid ${colors.border}`, padding: 16, backgroundColor: colors.pageBg }}>
                          {file.preview.headers && file.preview.rows && (
                            <div style={{ overflowX: "auto" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12, fontSize: 12, color: colors.textMuted }}><Table size={14} /><span>First {file.preview.rows.length} of {file.preview.rowCount?.toLocaleString()} rows</span></div>
                              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, backgroundColor: colors.cardBg, borderRadius: 8 }}>
                                <thead><tr>{file.preview.headers.map((h, i) => <th key={i} style={{ padding: "10px 12px", textAlign: "left", backgroundColor: colors.pageBg, fontWeight: 600, borderBottom: `1px solid ${colors.border}`, whiteSpace: "nowrap" }}>{h}</th>)}</tr></thead>
                                <tbody>{file.preview.rows.map((row, ri) => <tr key={ri}>{row.map((cell, ci) => <td key={ci} style={{ padding: "8px 12px", borderBottom: ri < file.preview!.rows!.length - 1 ? `1px solid ${colors.border}` : "none", whiteSpace: "nowrap", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{cell}</td>)}</tr>)}</tbody>
                              </table>
                            </div>
                          )}
                          {file.preview.text && !file.preview.headers && <div style={{ backgroundColor: colors.cardBg, borderRadius: 8, padding: 12, fontSize: 12, fontFamily: "monospace", whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto" }}>{file.preview.text}</div>}
                          {file.preview.imageUrl && <div style={{ textAlign: "center" }}><img src={file.preview.imageUrl} alt={file.name} style={{ maxWidth: "100%", maxHeight: 300, borderRadius: 8, border: `1px solid ${colors.border}` }} /></div>}
                        </div>
                      )}
                    </div>
                  );
                })}
                <div onClick={onBrowseClick} style={{ border: `2px dashed ${colors.border}`, borderRadius: 10, padding: 16, textAlign: "center", cursor: "pointer" }}>
                  <div style={{ fontSize: 13, color: colors.textMuted }}><Upload size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />Add more files</div>
                </div>
              </div>
            )}
          </div>

          {/* Recent Artifacts */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}><h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Recent Artifacts</h2><span style={{ fontSize: 12, color: colors.textMuted }}>{artifacts.length} total</span></div>
            <div style={{ backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 12, padding: 16 }}>
              {artifacts.length > 0 ? (
                <div>
                  {artifacts.slice(0, 5).map((art: any, i: number) => (
                    <div key={art.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: i < Math.min(artifacts.length, 5) - 1 ? `1px solid ${colors.border}` : "none" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 8, backgroundColor: colors.pageBg, display: "flex", alignItems: "center", justifyContent: "center" }}><Package size={16} color={colors.textMuted} /></div>
                        <div><div style={{ fontWeight: 500, fontSize: 13 }}>{art.name}</div><div style={{ fontSize: 11, color: colors.textMuted }}>Mode {art.modeId} • {art.createdAt ? new Date(art.createdAt).toLocaleTimeString() : "—"}</div></div>
                      </div>
                      <button onClick={() => openArtifact(art.id)} style={{ background: "none", border: "none", color: colors.primary, fontSize: 13, fontWeight: 500, cursor: "pointer" }}>View</button>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "20px 0", color: colors.textMuted, fontSize: 13 }}>No artifacts yet</div>
              )}
            </div>
          </div>

          {/* Command Input */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 10, padding: "4px 4px 4px 16px" }}>
              <input type="text" value={commandInput} onChange={(e) => setCommandInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleCommand(commandInput)} placeholder="Type a command or press ⌘K for palette..." style={{ flex: 1, border: "none", outline: "none", fontSize: 13, backgroundColor: "transparent", color: colors.text }} />
              <button onClick={() => handleCommand(commandInput)} style={{ padding: "8px 16px", backgroundColor: colors.primary, color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}><Send size={14} /> Send</button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, fontSize: 12 }}>
              <span style={{ color: colors.textMuted }}>Quick:</span>
              {["/status", "/run mode 0", "/artifacts"].map((cmd) => (
                <button key={cmd} onClick={() => setCommandInput(cmd)} style={{ padding: "4px 10px", backgroundColor: colors.pageBg, border: `1px solid ${colors.border}`, borderRadius: 14, fontSize: 11, color: colors.text, cursor: "pointer" }}>{cmd}</button>
              ))}
            </div>
          </div>
        </main>

        {/* RIGHT SIDEBAR */}
        <aside style={{ width: 280, backgroundColor: colors.sidebarBg, borderLeft: `1px solid ${colors.border}`, display: "flex", flexDirection: "column" }}>
          <div style={{ padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}><h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Live Activity</h2><span style={{ backgroundColor: colors.pillBlueBg, color: colors.pillBlueText, border: `1px solid ${colors.pillBlueBorder}`, padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 500 }}>Live</span></div>
            <p style={{ fontSize: 12, color: colors.textMuted, margin: "0 0 16px" }}>Real-time pipeline updates</p>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "0 20px 20px" }}>
            {activities?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {activities.slice(0, 20).map((a: any) => (
                  <div key={a.id || `${a.timestamp}-${a.type}`} style={{ backgroundColor: colors.pageBg, borderRadius: 8, padding: 12 }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <Activity size={14} color={colors.textMuted} style={{ marginTop: 2 }} />
                      <div><div style={{ fontSize: 12 }}>{a.content || a.type}</div><div style={{ fontSize: 10, color: colors.textLight, marginTop: 4 }}>{a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : ""}</div></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ backgroundColor: colors.pageBg, borderRadius: 8, padding: 24, textAlign: "center", color: colors.textMuted, fontSize: 13 }}>No activity yet</div>
            )}
          </div>
        </aside>
      </div>

      <input ref={fileInputRef} type="file" multiple accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.jpeg,.jpg,.png,.gif" style={{ display: "none" }} onChange={async (e) => { if (e.target.files?.length) { await ingestFiles(e.target.files); e.target.value = ""; } }} />
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function getModeDescription(modeId: string): string {
  const descriptions: Record<string, string> = {
    "0.5": "Identifies and validates new business opportunities through market analysis, competitive landscape assessment, and strategic alignment evaluation.",
    "0": "Performs comprehensive Exploratory Data Analysis including data profiling, statistical analysis, visualization, and quality assessment.",
    "1": "Generates decision intelligence insights by synthesizing data findings with business context to support strategic decision-making.",
    "2": "Evaluates technical and operational feasibility, assessing resource requirements, risks, and implementation complexity.",
    "3": "Develops strategic recommendations and actionable roadmaps based on analysis findings and business objectives.",
    "4": "Creates comprehensive business cases with ROI projections, cost-benefit analysis, and investment justification.",
    "5": "Generates production-ready code implementations using Claude, including algorithms, integrations, and automation scripts.",
    "6": "Executes generated code in a sandboxed environment, capturing outputs, metrics, and execution logs.",
    "6.5": "Interprets execution results, providing human-readable summaries and actionable recommendations.",
    "7": "Packages all artifacts into final deliverables including reports, presentations, and documentation.",
  };
  return descriptions[modeId] || "No description available.";
}

function getModeOutputs(modeId: string): string[] {
  const outputs: Record<string, string[]> = {
    "0.5": ["Opportunity Assessment Report", "Market Analysis Summary", "Strategic Fit Score"],
    "0": ["Data Profile Report", "Statistical Summary", "Visualizations", "Quality Report"],
    "1": ["Decision Brief", "Key Insights Document", "Recommendation Matrix"],
    "2": ["Feasibility Assessment", "Risk Analysis", "Resource Requirements"],
    "3": ["Strategic Roadmap", "Action Plan", "Priority Matrix"],
    "4": ["Business Case Document", "ROI Analysis", "Investment Proposal"],
    "5": ["Source Code", "Documentation", "Test Cases"],
    "6": ["Execution Logs", "Output Data", "Performance Metrics"],
    "6.5": ["Results Interpretation", "Findings Summary", "Next Steps"],
    "7": ["Final Report", "Executive Summary", "Deliverable Package"],
  };
  return outputs[modeId] || ["Output artifacts"];
}

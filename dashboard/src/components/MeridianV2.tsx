/**
 * MERIDIAN Intelligence Platform v2
 * Industrial dark steel aesthetic with mode cards organized by phase
 */

import { useState, useRef, useCallback } from 'react';
import {
  Cpu,
  Play,
  RotateCcw,
  Zap,
  Code,
  Send,
  Upload,
  File,
  X,
  Check,
  Activity,
  Brain,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { useDashboardStore } from '../store';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import type { ModeId, ModeInfo } from '../types';

// ============= DESIGN TOKENS =============
const tokens = {
  bg: { base: '#121416', panel: '#1a1c1e', elevated: '#2a2d31', hover: '#32363b' },
  border: { dark: '#151618', default: '#2a2d31', light: '#3d4247' },
  text: { primary: '#e8e9ea', secondary: '#a0a4a8', muted: '#6b7075' },
  status: { success: '#4ade80', warning: '#fbbf24', error: '#f87171', running: '#a78bfa', idle: '#6b7075' },
  model: { gpt: '#4ade80', claude: '#22d3ee', hybrid: '#fb923c' },
  accent: { primary: '#f97316', cyan: '#22d3ee' }
};

// ============= MODE → MODEL MAPPING =============
const modeModelMap: Record<string, 'gpt' | 'claude' | 'hybrid'> = {
  '0.5': 'gpt',
  '0': 'gpt',
  '1': 'gpt',
  '2': 'gpt',
  '3': 'hybrid',
  '4': 'gpt',
  '5': 'claude',
  '6': 'claude',
  '6.5': 'hybrid',
  '7': 'hybrid',
};

const modePhaseMap: Record<string, string> = {
  '0.5': 'Discovery',
  '0': 'Discovery',
  '1': 'Discovery',
  '2': 'Development',
  '3': 'Development',
  '4': 'Development',
  '5': 'Implementation',
  '6': 'Implementation',
  '6.5': 'Implementation',
  '7': 'Delivery',
};

// ============= MODEL CONFIG =============
const modelConfig = {
  gpt: { label: 'GPT-O3S', color: tokens.model.gpt, glowClass: 'glow-gpt' },
  claude: { label: 'Claude', color: tokens.model.claude, glowClass: 'glow-claude' },
  hybrid: { label: 'Hybrid', color: tokens.model.hybrid, glowClass: 'glow-hybrid' },
};

// ============= STATUS LED =============
function StatusLED({ status, size = 8 }: { status: string; size?: number }) {
  const colors: Record<string, string> = {
    completed: tokens.status.success,
    success: tokens.status.success,
    running: tokens.status.running,
    queued: tokens.status.warning,
    failed: tokens.status.error,
    error: tokens.status.error,
    idle: tokens.status.idle,
    not_started: tokens.status.idle,
  };
  const color = colors[status] || colors.idle;
  const isActive = status === 'completed' || status === 'success' || status === 'running';
  const isRunning = status === 'running';

  return (
    <div
      className={`rounded-full ${isActive ? 'led-glow' : ''} ${isRunning ? 'led-pulse' : ''}`}
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        border: `1px solid ${color}`,
        boxShadow: isActive ? `0 0 6px ${color}, 0 0 12px ${color}` : 'none',
      }}
    />
  );
}

// ============= MODEL BADGE =============
function ModelBadge({ model, size = 'sm' }: { model: 'gpt' | 'claude' | 'hybrid'; size?: 'xs' | 'sm' | 'md' }) {
  const config = modelConfig[model];
  const sizes = {
    xs: 'text-[10px] px-1.5 py-0.5 gap-1',
    sm: 'text-xs px-2 py-1 gap-1.5',
    md: 'text-sm px-3 py-1.5 gap-2',
  };
  const iconSizes = { xs: 10, sm: 12, md: 14 };

  const Icon = model === 'gpt' ? Brain : model === 'claude' ? Code : Sparkles;

  return (
    <span
      className={`inline-flex items-center rounded font-mono font-semibold ${sizes[size]}`}
      style={{
        backgroundColor: `${config.color}20`,
        color: config.color,
        border: `1px solid ${config.color}40`,
      }}
    >
      <Icon size={iconSizes[size]} />
      {config.label}
    </span>
  );
}

// ============= MODE CARD (Compact) =============
function ModeCard({ mode, onRun }: { mode: ModeInfo & { model: 'gpt' | 'claude' | 'hybrid'; progress?: number }; onRun: (id: string) => void }) {
  const config = modelConfig[mode.model];
  const isRunning = mode.status === 'running';
  const isCompleted = mode.status === 'completed';

  return (
    <div
      className={`mode-card metal-panel rounded-lg p-3 cursor-pointer transition-all hover:-translate-y-0.5 group ${config.glowClass}`}
      style={{ borderColor: isRunning ? config.color : isCompleted ? tokens.status.success : tokens.border.light }}
      onClick={() => !isRunning && onRun(mode.id)}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <StatusLED status={mode.status} size={8} />
          <span className="text-[11px] font-mono" style={{ color: tokens.text.muted }}>
            Mode {mode.id}
          </span>
        </div>
        <ModelBadge model={mode.model} size="xs" />
      </div>

      {/* Title */}
      <h3 className="text-[13px] font-semibold leading-tight mb-1" style={{ color: tokens.text.primary }}>
        {mode.name}
      </h3>
      
      {/* Description */}
      <p className="text-[11px] leading-snug mb-2 line-clamp-2" style={{ color: tokens.text.muted }}>
        {mode.description}
      </p>

      {/* Progress bar for running modes */}
      {isRunning && (
        <div className="mb-2">
          <div className="h-1 rounded-full overflow-hidden" style={{ backgroundColor: tokens.bg.panel }}>
            <div
              className="h-full rounded-full progress-striped"
              style={{ width: '50%', backgroundColor: tokens.status.running }}
            />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className="text-[10px]" style={{ color: tokens.text.muted }}>
          {mode.lastRunAt ? `Last: ${mode.lastRunAt}` : 'Never run'}
        </span>
        <div className="actions flex items-center gap-1">
          {!isRunning && (
            <Play size={12} color={config.color} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          )}
          {isRunning && (
            <Loader2 size={12} color={tokens.status.running} className="animate-spin" />
          )}
        </div>
      </div>
    </div>
  );
}

// ============= PHASE SECTION =============
function PhaseSection({ title, modes, onRunMode }: { title: string; modes: (ModeInfo & { model: 'gpt' | 'claude' | 'hybrid' })[]; onRunMode: (id: string) => void }) {
  if (modes.length === 0) return null;
  
  return (
    <section className="mb-5">
      <div className="flex items-center gap-3 mb-3">
        <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: tokens.text.secondary }}>
          {title}
        </h2>
        <div className="flex-1 h-px" style={{ backgroundColor: tokens.border.default }} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {modes.map((mode) => (
          <ModeCard key={mode.id} mode={mode} onRun={onRunMode} />
        ))}
      </div>
    </section>
  );
}

// ============= PIPELINE PROGRESS MINI =============
function PipelineProgressMini({ modes }: { modes: ModeInfo[] }) {
  const completed = modes.filter((m) => m.status === 'completed').length;

  return (
    <div className="metal-inset rounded p-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>
          Pipeline
        </span>
        <span className="text-[11px] font-medium" style={{ color: tokens.status.success }}>
          {completed}/{modes.length} Complete
        </span>
      </div>
      <div className="flex gap-0.5">
        {modes.map((mode) => (
          <div
            key={mode.id}
            className="flex-1 h-1.5 rounded-sm overflow-hidden"
            style={{ backgroundColor: tokens.bg.panel }}
            title={`Mode ${mode.id}: ${mode.name}`}
          >
            <div
              className="h-full rounded-sm transition-all"
              style={{
                width: mode.status === 'completed' ? '100%' : mode.status === 'running' ? '50%' : '0%',
                backgroundColor: mode.status === 'completed' ? tokens.status.success : mode.status === 'running' ? tokens.status.running : 'transparent',
              }}
            />
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-1.5">
        {['Dis', 'Dev', 'Imp', 'Del'].map((phase) => (
          <span key={phase} className="text-[9px]" style={{ color: tokens.text.muted }}>
            {phase}
          </span>
        ))}
      </div>
    </div>
  );
}

// ============= CONTROL BUTTON =============
function ControlButton({
  icon,
  label,
  variant = 'default',
  onClick,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  variant?: 'default' | 'primary' | 'cyan';
  onClick?: () => void;
  disabled?: boolean;
}) {
  const variants = {
    default: { bg: tokens.bg.elevated, border: tokens.border.light, text: tokens.text.secondary },
    primary: { bg: `${tokens.accent.primary}15`, border: tokens.accent.primary, text: tokens.accent.primary },
    cyan: { bg: `${tokens.accent.cyan}15`, border: tokens.accent.cyan, text: tokens.accent.cyan },
  };
  const v = variants[variant];

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full flex items-center gap-2 px-2.5 py-2 rounded transition-all hover:brightness-110 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      style={{ backgroundColor: v.bg, border: `1px solid ${v.border}`, color: v.text }}
    >
      {icon}
      <span className="text-[12px] font-medium">{label}</span>
    </button>
  );
}

// ============= DROP ZONE =============
function DropZone({
  onFilesAdded,
  files,
  onRemoveFile,
}: {
  onFilesAdded: (files: File[]) => void;
  files: { id: string; name: string; status: string }[];
  onRemoveFile: (id: string) => void;
}) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) onFilesAdded(droppedFiles);
  };

  return (
    <div className="space-y-2">
      <div
        className={`drop-zone rounded-lg p-4 cursor-pointer transition-all ${isDragActive ? 'active' : ''}`}
        style={{
          border: `2px dashed ${isDragActive ? tokens.accent.primary : tokens.border.light}`,
          backgroundColor: isDragActive ? `${tokens.accent.primary}10` : 'transparent',
        }}
        onDragEnter={(e) => { e.preventDefault(); setIsDragActive(true); }}
        onDragLeave={(e) => { e.preventDefault(); setIsDragActive(false); }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => onFilesAdded(Array.from(e.target.files || []))}
          accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.json,.yaml,.yml,.png,.jpg,.jpeg"
        />
        <div className="flex items-center gap-3">
          <Upload size={20} color={isDragActive ? tokens.accent.primary : tokens.text.muted} />
          <span className="text-sm" style={{ color: isDragActive ? tokens.accent.primary : tokens.text.muted }}>
            {isDragActive ? 'Drop files' : 'Drop files or click'}
          </span>
        </div>
      </div>
      {files.length > 0 && (
        <div className="space-y-1">
          {files.map((f) => (
            <div
              key={f.id}
              className="flex items-center gap-2 px-2 py-1.5 rounded text-xs"
              style={{
                background: `linear-gradient(180deg, ${tokens.bg.elevated} 0%, #222528 100%)`,
                border: `1px solid ${tokens.border.light}`,
              }}
            >
              <File size={12} color={tokens.text.muted} />
              <span className="flex-1 truncate" style={{ color: tokens.text.primary }}>
                {f.name}
              </span>
              {f.status === 'complete' ? (
                <Check size={12} color={tokens.status.success} />
              ) : (
                <Loader2 size={12} color={tokens.status.running} className="animate-spin" />
              )}
              <button onClick={() => onRemoveFile(f.id)} className="p-0.5 hover:bg-white/10 rounded">
                <X size={12} color={tokens.text.muted} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============= MAIN COMPONENT =============
export function MeridianV2() {
  const { modes, updateMode, resetModes, activities } = useDashboardStore();
  const [command, setCommand] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<{ id: string; name: string; status: string }[]>([]);
  const [sessionState] = useState({ model: 'Dual-Model', load: 42, uptime: '2h 34m' });

  // Enrich modes with model info
  const enrichedModes = modes.map((m) => ({
    ...m,
    model: modeModelMap[m.id] || 'gpt',
    phase: modePhaseMap[m.id] || 'Discovery',
  }));

  // Group by phase
  const discovery = enrichedModes.filter((m) => m.phase === 'Discovery');
  const development = enrichedModes.filter((m) => m.phase === 'Development');
  const implementation = enrichedModes.filter((m) => m.phase === 'Implementation');
  const delivery = enrichedModes.filter((m) => m.phase === 'Delivery');

  const handleRunMode = useCallback(async (modeId: string) => {
    try {
      await api.runMode(modeId);
      updateMode(modeId as ModeId, { status: 'running' });
      toast.success(`Started Mode ${modeId}`);
    } catch (error) {
      toast.error(`Failed to start mode: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [updateMode]);

  const handleRunAnalysis = () => {
    const gptModes = enrichedModes.filter((m) => m.model === 'gpt' && m.status !== 'completed' && m.status !== 'running');
    if (gptModes.length > 0) handleRunMode(gptModes[0].id);
  };

  const handleGenerateCode = () => {
    const claudeModes = enrichedModes.filter((m) => m.model === 'claude' && m.status !== 'completed' && m.status !== 'running');
    if (claudeModes.length > 0) handleRunMode(claudeModes[0].id);
  };

  const handleResetPipeline = () => {
    resetModes();
    toast.success('Pipeline reset');
  };

  const handleFilesAdded = (newFiles: File[]) => {
    const fileObjects = newFiles.map((file) => ({
      id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      status: 'uploading',
    }));
    setUploadedFiles((prev) => [...prev, ...fileObjects]);
    fileObjects.forEach((f) => {
      setTimeout(() => {
        setUploadedFiles((prev) => prev.map((file) => (file.id === f.id ? { ...file, status: 'complete' } : file)));
      }, 1500);
    });
  };

  const handleSendCommand = () => {
    if (!command.trim()) return;
    
    if (command.startsWith('/run ')) {
      const modeId = command.replace('/run ', '').trim();
      handleRunMode(modeId);
    } else if (command === '/status') {
      toast.success('Pipeline status: Active');
    }
    setCommand('');
  };

  return (
    <div className="h-screen flex flex-col carbon-fiber" style={{ fontFamily: 'IBM Plex Sans, system-ui, sans-serif' }}>
      {/* Header */}
      <header className="metal-panel-dark flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2.5">
          <Cpu size={20} color={tokens.accent.primary} />
          <div>
            <h1 className="text-sm font-bold tracking-wide" style={{ color: tokens.text.primary }}>
              MERIDIAN Intelligence Platform
            </h1>
            <p className="text-[10px]" style={{ color: tokens.text.muted }}>
              Dual-Model AI System
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ModelBadge model="gpt" size="xs" />
          <ModelBadge model="claude" size="xs" />
        </div>
      </header>

      {/* Main */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <aside
          className="w-56 metal-panel-dark border-r flex flex-col p-3 gap-3"
          style={{ borderColor: tokens.border.default }}
        >
          <PipelineProgressMini modes={modes} />

          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>
              Run Controls
            </span>
            <ControlButton
              icon={<Zap size={14} />}
              label="Run Analysis"
              variant="primary"
              onClick={handleRunAnalysis}
            />
            <ControlButton
              icon={<Code size={14} />}
              label="Generate Code"
              variant="cyan"
              onClick={handleGenerateCode}
            />
            <ControlButton
              icon={<RotateCcw size={14} />}
              label="Reset Pipeline"
              onClick={handleResetPipeline}
            />
          </div>

          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>
              Documents
            </span>
            <DropZone
              onFilesAdded={handleFilesAdded}
              files={uploadedFiles}
              onRemoveFile={(id) => setUploadedFiles((prev) => prev.filter((f) => f.id !== id))}
            />
          </div>

          <div className="mt-auto">
            <div className="metal-inset rounded p-2.5 space-y-1.5">
              <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>
                Session
              </span>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: tokens.text.muted }}>Mode:</span>
                <span style={{ color: tokens.text.secondary }}>{sessionState.model}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: tokens.text.muted }}>Load:</span>
                <span style={{ color: tokens.status.success }}>{sessionState.load}%</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: tokens.text.muted }}>Uptime:</span>
                <span style={{ color: tokens.text.secondary }}>{sessionState.uptime}</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Center - Mode Cards */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4">
            <PhaseSection title="Discovery" modes={discovery} onRunMode={handleRunMode} />
            <PhaseSection title="Development" modes={development} onRunMode={handleRunMode} />
            <PhaseSection title="Implementation" modes={implementation} onRunMode={handleRunMode} />
            <PhaseSection title="Delivery" modes={delivery} onRunMode={handleRunMode} />
          </div>

          {/* Command Input */}
          <div className="p-3 border-t" style={{ borderColor: tokens.border.default }}>
            <div className="metal-inset rounded flex items-center">
              <input
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendCommand()}
                placeholder="Type a MERIDIAN command or describe what you want to analyze..."
                className="flex-1 bg-transparent px-3 py-2 text-[12px] outline-none"
                style={{ color: tokens.text.primary, fontFamily: 'IBM Plex Mono, monospace' }}
              />
              <button className="p-2" onClick={handleSendCommand}>
                <Send size={14} fill={command ? tokens.accent.primary : tokens.text.muted} stroke="none" />
              </button>
            </div>
            <div className="flex gap-3 mt-1.5 px-1">
              <span className="text-[10px]" style={{ color: tokens.text.muted }}>
                Quick:
              </span>
              {['/run discovery', '/run implementation', '/status'].map((cmd) => (
                <button
                  key={cmd}
                  className="text-[10px] px-1.5 py-0.5 rounded hover:bg-white/5"
                  style={{ color: tokens.accent.cyan }}
                  onClick={() => setCommand(cmd)}
                >
                  {cmd}
                </button>
              ))}
            </div>
          </div>
        </main>

        {/* Right Sidebar - Activity */}
        <aside className="w-52 metal-panel-dark border-l flex flex-col" style={{ borderColor: tokens.border.default }}>
          <div className="p-2.5 border-b" style={{ borderColor: tokens.border.default }}>
            <h2 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: tokens.text.secondary }}>
              Live Activity
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2.5">
            {activities.length === 0 ? (
              <div className="flex-1 flex items-center justify-center h-full">
                <div className="text-center px-3">
                  <Activity size={24} color={tokens.text.muted} className="mx-auto mb-2" />
                  <p className="text-[11px]" style={{ color: tokens.text.muted }}>
                    No activity yet
                  </p>
                  <p className="text-[10px] mt-1" style={{ color: tokens.text.muted }}>
                    Run a mode to see live output
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                {activities.slice(0, 20).map((activity) => (
                  <div
                    key={activity.id}
                    className="p-1.5 rounded text-[10px]"
                    style={{ backgroundColor: tokens.bg.elevated, border: `1px solid ${tokens.border.default}` }}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <StatusLED status={activity.type.includes('completed') ? 'completed' : activity.type.includes('running') ? 'running' : 'idle'} size={5} />
                      <span className="truncate" style={{ color: tokens.text.primary }}>{activity.content || activity.type}</span>
                    </div>
                    <span style={{ color: tokens.text.muted }}>
                      {new Date(activity.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

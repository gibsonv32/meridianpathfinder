/**
 * MERIDIAN Intelligence Platform V3
 * Industrial dark steel aesthetic - Atomic Design Pattern
 * Based on extracted Claude Code components
 */

import { useState, useCallback } from 'react';
import { useDashboardStore } from '../store';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import type { ModeId, ModeInfo } from '../types';

// ============= DESIGN TOKENS =============
const tokens = {
  bg: { base: '#121416', panel: '#1a1c1e', elevated: '#2a2d31', hover: '#32363b' },
  border: { dark: '#151618', default: '#2a2d31', light: '#3d4247' },
  text: { primary: '#e8e9ea', secondary: '#a0a4a8', muted: '#6b7075' },
  status: { success: '#4ade80', running: '#a78bfa', warning: '#fbbf24', error: '#f87171', idle: '#6b7075' },
  model: { gpt: '#4ade80', claude: '#22d3ee', hybrid: '#fb923c' },
  accent: { primary: '#f97316', cyan: '#22d3ee' },
};

const modelConfig = {
  gpt: { label: 'GPT-O3S', color: tokens.model.gpt, icon: '🧠' },
  claude: { label: 'Claude', color: tokens.model.claude, icon: '⚡' },
  hybrid: { label: 'Hybrid', color: tokens.model.hybrid, icon: '✨' },
};

const modeModelMap: Record<string, 'gpt' | 'claude' | 'hybrid'> = {
  '0.5': 'gpt', '0': 'gpt', '1': 'gpt', '2': 'gpt', '3': 'hybrid',
  '4': 'gpt', '5': 'claude', '6': 'claude', '6.5': 'hybrid', '7': 'hybrid',
};

const modePhaseMap: Record<string, string> = {
  '0.5': 'Discovery', '0': 'Discovery', '1': 'Discovery',
  '2': 'Development', '3': 'Development', '4': 'Development',
  '5': 'Implementation', '6': 'Implementation', '6.5': 'Implementation',
  '7': 'Delivery',
};

// ============= ICONS (SVG) =============
const Icons = {
  Cpu: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" />
    </svg>
  ),
  Play: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  ),
  Zap: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  Code: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
    </svg>
  ),
  Refresh: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  ),
  Upload: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  Send: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <line x1="22" y1="2" x2="11" y2="13" stroke="currentColor" strokeWidth="2" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  ),
  Activity: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
};

// ============= ATOMS =============
function StatusLED({ status, size = 8 }: { status: string; size?: number }) {
  const colors: Record<string, string> = {
    completed: tokens.status.success, success: tokens.status.success,
    running: tokens.status.running, queued: tokens.status.warning,
    failed: tokens.status.error, error: tokens.status.error,
    idle: tokens.status.idle, not_started: tokens.status.idle,
  };
  const color = colors[status] || colors.idle;
  const isActive = ['completed', 'success', 'running'].includes(status);
  return (
    <div
      className={isActive ? 'led-pulse' : ''}
      style={{
        width: size, height: size, borderRadius: '50%',
        backgroundColor: color, border: `1px solid ${color}`,
        boxShadow: isActive ? `0 0 4px ${color}, 0 0 8px ${color}` : 'none',
      }}
    />
  );
}

function ModelBadge({ model, size = 'sm' }: { model: 'gpt' | 'claude' | 'hybrid'; size?: 'xs' | 'sm' }) {
  const cfg = modelConfig[model];
  const sizes = { xs: 'text-[9px] px-1.5 py-0.5', sm: 'text-[10px] px-2 py-1' };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded font-mono font-semibold ${sizes[size]}`}
      style={{ backgroundColor: `${cfg.color}20`, color: cfg.color, border: `1px solid ${cfg.color}40` }}
    >
      {cfg.icon} {cfg.label}
    </span>
  );
}

function ControlButton({ icon, label, variant = 'default', onClick, loading }: {
  icon: React.ReactNode; label: string; variant?: 'default' | 'primary' | 'cyan'; onClick?: () => void; loading?: boolean;
}) {
  const variants = {
    default: { bg: tokens.bg.elevated, border: tokens.border.light, text: tokens.text.secondary },
    primary: { bg: `${tokens.accent.primary}15`, border: tokens.accent.primary, text: tokens.accent.primary },
    cyan: { bg: `${tokens.accent.cyan}15`, border: tokens.accent.cyan, text: tokens.accent.cyan },
  };
  const v = variants[variant];
  return (
    <button
      onClick={onClick} disabled={loading}
      className={`w-full flex items-center gap-2 px-3 py-2 rounded transition-all hover:brightness-110 ${loading ? 'opacity-50' : ''}`}
      style={{ backgroundColor: v.bg, border: `1px solid ${v.border}`, color: v.text }}
    >
      {icon}<span className="text-xs font-medium">{label}</span>
      {loading && <span className="ml-auto animate-spin">⟳</span>}
    </button>
  );
}

// ============= MOLECULES =============
function PipelineProgress({ modes }: { modes: ModeInfo[] }) {
  const completed = modes.filter(m => m.status === 'completed').length;
  return (
    <div className="metal-inset rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>Pipeline</span>
        <span className="text-xs font-medium" style={{ color: tokens.status.success }}>{completed}/{modes.length} Complete</span>
      </div>
      <div className="flex gap-0.5">
        {modes.map(m => (
          <div key={m.id} className="flex-1 h-1.5 rounded-sm overflow-hidden" style={{ backgroundColor: tokens.bg.panel }}>
            <div className="h-full rounded-sm transition-all" style={{
              width: m.status === 'completed' ? '100%' : m.status === 'running' ? '50%' : '0%',
              backgroundColor: m.status === 'completed' ? tokens.status.success : m.status === 'running' ? tokens.status.running : 'transparent',
            }} />
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-1.5">
        {['Dis', 'Dev', 'Imp', 'Del'].map(p => <span key={p} className="text-[9px]" style={{ color: tokens.text.muted }}>{p}</span>)}
      </div>
    </div>
  );
}

function ModeCard({ mode, onRun }: { mode: ModeInfo & { model: 'gpt' | 'claude' | 'hybrid' }; onRun: (id: string) => void }) {
  const cfg = modelConfig[mode.model];
  const isRunning = mode.status === 'running';
  const isCompleted = mode.status === 'completed';
  return (
    <div
      onClick={() => !isRunning && onRun(mode.id)}
      className={`group metal-panel rounded-lg p-3 cursor-pointer transition-all hover:-translate-y-0.5 ${cfg.label === 'GPT-O3S' ? 'glow-gpt' : cfg.label === 'Claude' ? 'glow-claude' : 'glow-hybrid'}`}
      style={{ borderColor: isRunning ? cfg.color : isCompleted ? tokens.status.success : tokens.border.light }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <StatusLED status={mode.status} size={8} />
          <span className="text-[10px] font-mono" style={{ color: tokens.text.muted }}>Mode {mode.id}</span>
        </div>
        <ModelBadge model={mode.model} size="xs" />
      </div>
      <h3 className="text-[13px] font-semibold leading-tight mb-1" style={{ color: tokens.text.primary }}>{mode.name}</h3>
      <p className="text-[10px] leading-snug mb-2 line-clamp-2" style={{ color: tokens.text.muted }}>{mode.description}</p>
      {isRunning && (
        <div className="mb-2 h-1 rounded-full overflow-hidden" style={{ backgroundColor: tokens.bg.panel }}>
          <div className="h-full rounded-full progress-striped" style={{ width: '50%', backgroundColor: tokens.status.running }} />
        </div>
      )}
      <div className="flex items-center justify-between">
        <span className="text-[10px]" style={{ color: tokens.text.muted }}>{mode.lastRunAt || 'Never run'}</span>
        {!isRunning && <Icons.Play />}
      </div>
    </div>
  );
}

function PhaseSection({ title, modes, onRunMode }: { title: string; modes: (ModeInfo & { model: 'gpt' | 'claude' | 'hybrid' })[]; onRunMode: (id: string) => void }) {
  if (!modes.length) return null;
  return (
    <section className="mb-5">
      <div className="flex items-center gap-3 mb-3">
        <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: tokens.text.secondary }}>{title}</h2>
        <div className="flex-1 h-px" style={{ backgroundColor: tokens.border.default }} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {modes.map(m => <ModeCard key={m.id} mode={m} onRun={onRunMode} />)}
      </div>
    </section>
  );
}

// ============= MAIN COMPONENT =============
export function MeridianV3() {
  const { modes, activities, updateMode, resetModes } = useDashboardStore();
  const [command, setCommand] = useState('');
  const [sessionState] = useState({ model: 'Dual-Model', load: 42, uptime: '2h 34m' });

  const enrichedModes = modes.map(m => ({ ...m, model: modeModelMap[m.id] || 'gpt', phase: modePhaseMap[m.id] || 'Discovery' }));
  const discovery = enrichedModes.filter(m => m.phase === 'Discovery');
  const development = enrichedModes.filter(m => m.phase === 'Development');
  const implementation = enrichedModes.filter(m => m.phase === 'Implementation');
  const delivery = enrichedModes.filter(m => m.phase === 'Delivery');

  const handleRunMode = useCallback(async (modeId: string) => {
    try {
      await api.runMode(modeId);
      updateMode(modeId as ModeId, { status: 'running' });
      toast.success(`Started Mode ${modeId}`);
    } catch (e) {
      toast.error(`Failed: ${e instanceof Error ? e.message : 'Unknown'}`);
    }
  }, [updateMode]);

  const handleSendCommand = () => {
    if (!command.trim()) return;
    if (command.startsWith('/run ')) handleRunMode(command.replace('/run ', '').trim());
    setCommand('');
  };

  return (
    <div className="h-screen flex flex-col carbon-fiber" style={{ fontFamily: 'IBM Plex Sans, system-ui, sans-serif' }}>
      {/* Header */}
      <header className="metal-panel-dark flex items-center justify-between px-5 py-2.5" style={{ borderBottom: `1px solid ${tokens.border.default}` }}>
        <div className="flex items-center gap-2.5">
          <span style={{ color: tokens.accent.primary }}><Icons.Cpu /></span>
          <div>
            <h1 className="text-sm font-bold tracking-wide" style={{ color: tokens.text.primary }}>MERIDIAN Intelligence Platform</h1>
            <p className="text-[10px]" style={{ color: tokens.text.muted }}>Dual-Model AI System</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ModelBadge model="gpt" size="sm" />
          <ModelBadge model="claude" size="sm" />
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-56 metal-panel-dark border-r flex flex-col p-3 gap-3" style={{ borderColor: tokens.border.default }}>
          <PipelineProgress modes={modes} />
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>Run Controls</span>
            <ControlButton icon={<span style={{ color: tokens.accent.primary }}><Icons.Zap /></span>} label="Run Analysis" variant="primary" onClick={() => handleRunMode(discovery.find(m => m.status !== 'completed')?.id || '0')} />
            <ControlButton icon={<span style={{ color: tokens.accent.cyan }}><Icons.Code /></span>} label="Generate Code" variant="cyan" onClick={() => handleRunMode('5')} />
            <ControlButton icon={<Icons.Refresh />} label="Reset Pipeline" onClick={() => { resetModes(); toast.success('Reset'); }} />
          </div>
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>Documents</span>
            <div className="rounded-lg p-3 cursor-pointer" style={{ border: `2px dashed ${tokens.border.light}` }}>
              <div className="flex items-center gap-2">
                <span style={{ color: tokens.text.muted }}><Icons.Upload /></span>
                <span className="text-xs" style={{ color: tokens.text.muted }}>Drop files or click</span>
              </div>
            </div>
          </div>
          <div className="mt-auto metal-inset rounded p-2.5 space-y-1.5">
            <span className="text-[10px] font-semibold uppercase" style={{ color: tokens.text.muted }}>Session</span>
            {Object.entries(sessionState).map(([k, v]) => (
              <div key={k} className="flex justify-between text-[11px]">
                <span style={{ color: tokens.text.muted }}>{k}:</span>
                <span style={{ color: k === 'load' ? tokens.status.success : tokens.text.secondary }}>{v}{k === 'load' ? '%' : ''}</span>
              </div>
            ))}
          </div>
        </aside>

        {/* Center */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4">
            <PhaseSection title="Discovery" modes={discovery} onRunMode={handleRunMode} />
            <PhaseSection title="Development" modes={development} onRunMode={handleRunMode} />
            <PhaseSection title="Implementation" modes={implementation} onRunMode={handleRunMode} />
            <PhaseSection title="Delivery" modes={delivery} onRunMode={handleRunMode} />
          </div>
          <div className="p-3 border-t" style={{ borderColor: tokens.border.default }}>
            <div className="metal-inset rounded flex items-center">
              <input
                value={command} onChange={e => setCommand(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSendCommand()}
                placeholder="Type a MERIDIAN command..."
                className="flex-1 bg-transparent px-3 py-2 text-xs outline-none"
                style={{ color: tokens.text.primary, fontFamily: 'IBM Plex Mono, monospace' }}
              />
              <button className="p-2" onClick={handleSendCommand}><Icons.Send /></button>
            </div>
            <div className="flex gap-3 mt-1.5 px-1">
              <span className="text-[10px]" style={{ color: tokens.text.muted }}>Quick:</span>
              {['/run 0', '/run 5', '/status'].map(c => (
                <button key={c} className="text-[10px] px-1.5 rounded hover:bg-white/5" style={{ color: tokens.accent.cyan }} onClick={() => setCommand(c)}>{c}</button>
              ))}
            </div>
          </div>
        </main>

        {/* Right Sidebar - Activity */}
        <aside className="w-52 metal-panel-dark border-l flex flex-col" style={{ borderColor: tokens.border.default }}>
          <div className="p-2.5 border-b" style={{ borderColor: tokens.border.default }}>
            <h2 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: tokens.text.secondary }}>Live Activity</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2.5">
            {activities.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <span style={{ color: tokens.text.muted }}><Icons.Activity /></span>
                <p className="text-[11px] mt-2" style={{ color: tokens.text.muted }}>No activity yet</p>
                <p className="text-[10px]" style={{ color: tokens.text.muted }}>Run a mode to see output</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {activities.slice(0, 20).map(a => (
                  <div key={a.id} className="p-1.5 rounded text-[10px]" style={{ backgroundColor: tokens.bg.elevated, border: `1px solid ${tokens.border.default}` }}>
                    <div className="flex items-center gap-1.5">
                      <StatusLED status={a.type.includes('completed') ? 'completed' : a.type.includes('running') ? 'running' : 'idle'} size={5} />
                      <span className="truncate" style={{ color: tokens.text.primary }}>{a.content || a.type}</span>
                    </div>
                    <span style={{ color: tokens.text.muted }}>{new Date(a.timestamp).toLocaleTimeString()}</span>
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

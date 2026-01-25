import { useState } from 'react';
import {
  Layers,
  FileBox,
  Pin,
  ChevronDown,
  ChevronRight,
  Circle,
  CheckCircle2,
  XCircle,
  Loader2,
  Play,
  RotateCcw,
  Eye,
  Wifi,
  WifiOff,
  Search,
  History,
  Clock,
  Activity,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { useDashboardStore, selectPinnedActivities } from '../store';
import { NotificationCenter } from './Notifications';
import { RunHistory } from './RunHistory';
import { RunQueue } from './RunQueue';
import type { ModeInfo, ModeStatus } from '../types';

export function Sidebar() {
  const {
    connectionStatus,
    currentProject,
    modes,
    activePanel,
    setActivePanel,
    sidebarCollapsed,
    setSearchOpen,
  } = useDashboardStore();
  const pinnedActivities = useDashboardStore(selectPinnedActivities);
  const [showRunHistory, setShowRunHistory] = useState(false);
  const [showRunQueue, setShowRunQueue] = useState(false);

  // Calculate run queue stats
  const runningCount = modes.filter((m) => m.status === 'running').length;
  const completedCount = modes.filter((m) => m.status === 'completed').length;

  return (
    <>
    {showRunHistory && <RunHistory onClose={() => setShowRunHistory(false)} />}
    {showRunQueue && (
      <>
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30"
          onClick={() => setShowRunQueue(false)}
        />
        <RunQueue onClose={() => setShowRunQueue(false)} className="fixed inset-y-0 right-0 w-96 z-40" />
      </>
    )}
    <aside
      className={clsx(
        'flex flex-col bg-bg-secondary border-r border-border-subtle',
        'transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-72'
      )}
    >
      {/* Project Header */}
      <div className="p-4 border-b border-border-subtle">
        <div className="flex items-center justify-between">
          <div className={clsx('flex items-center gap-2', sidebarCollapsed && 'justify-center')}>
            <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center hover-lift">
              <span className="text-white font-bold text-sm">M</span>
              {/* Running indicator */}
              {runningCount > 0 && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-status-running rounded-full animate-pulse" />
              )}
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0">
                <h1 className="font-semibold text-text-primary truncate">
                  {currentProject?.name || 'MERIDIAN'}
                </h1>
                <ConnectionIndicator status={connectionStatus} />
              </div>
            )}
          </div>
          {!sidebarCollapsed && (
            <div className="flex items-center gap-1">
              {/* Run Queue Badge */}
              {runningCount > 0 && (
                <div className="flex items-center gap-1 px-2 py-1 bg-status-running/20 rounded-md">
                  <Activity className="w-3 h-3 text-status-running animate-pulse" />
                  <span className="text-xs text-status-running font-medium">{runningCount}</span>
                </div>
              )}
              <button
                onClick={() => setShowRunQueue(true)}
                className="btn btn-icon btn-ghost relative"
                title="Run Queue"
              >
                <Activity className="w-4 h-4" />
                {runningCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-status-running text-white text-2xs rounded-full flex items-center justify-center">
                    {runningCount}
                  </span>
                )}
              </button>
              <button
                onClick={() => setShowRunHistory(true)}
                className="btn btn-icon btn-ghost"
                title="Run History"
              >
                <History className="w-4 h-4" />
              </button>
              <NotificationCenter />
            </div>
          )}
        </div>

        {/* Progress bar */}
        {!sidebarCollapsed && completedCount > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-text-muted mb-1">
              <span>Progress</span>
              <span>{completedCount}/{modes.length}</span>
            </div>
            <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-accent-blue to-accent-purple transition-all duration-500"
                style={{ width: `${(completedCount / modes.length) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Search Button */}
      {!sidebarCollapsed && (
        <div className="px-3 py-2">
          <button
            onClick={() => setSearchOpen(true)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-bg-tertiary text-text-secondary hover:text-text-primary border border-border-subtle text-sm"
          >
            <Search className="w-4 h-4" />
            <span className="flex-1 text-left">Search...</span>
            <kbd className="text-2xs text-text-muted bg-bg-primary px-1.5 py-0.5 rounded">⌘K</kbd>
          </button>
        </div>
      )}

      {/* Panel Tabs */}
      <div className="flex border-b border-border-subtle">
        <PanelTab
          icon={Layers}
          label="Pipeline"
          active={activePanel === 'pipeline'}
          onClick={() => setActivePanel('pipeline')}
          collapsed={sidebarCollapsed}
        />
        <PanelTab
          icon={FileBox}
          label="Artifacts"
          active={activePanel === 'artifacts'}
          onClick={() => setActivePanel('artifacts')}
          collapsed={sidebarCollapsed}
        />
        <PanelTab
          icon={Pin}
          label="Pinned"
          active={activePanel === 'pinned'}
          onClick={() => setActivePanel('pinned')}
          badge={pinnedActivities.length || undefined}
          collapsed={sidebarCollapsed}
        />
      </div>

      {/* Panel Content */}
      <div className="flex-1 overflow-y-auto">
        {activePanel === 'pipeline' && <PipelinePanel modes={modes} collapsed={sidebarCollapsed} />}
        {activePanel === 'artifacts' && <ArtifactsPanel collapsed={sidebarCollapsed} />}
        {activePanel === 'pinned' && <PinnedPanel collapsed={sidebarCollapsed} />}
      </div>
    </aside>
    </>
  );
}

// -----------------------------------------------------------------------------
// Sub-components
// -----------------------------------------------------------------------------

function ConnectionIndicator({ status }: { status: string }) {
  const isConnected = status === 'connected';
  const isConnecting = status === 'connecting' || status === 'reconnecting';

  return (
    <div className="flex items-center gap-1.5 text-xs">
      {isConnected ? (
        <>
          <Wifi className="w-3 h-3 text-status-success" />
          <span className="text-status-success">Connected</span>
        </>
      ) : isConnecting ? (
        <>
          <Loader2 className="w-3 h-3 text-status-warning animate-spin" />
          <span className="text-status-warning">Connecting...</span>
        </>
      ) : (
        <>
          <WifiOff className="w-3 h-3 text-status-error" />
          <span className="text-status-error">Offline</span>
        </>
      )}
    </div>
  );
}

function PanelTab({
  icon: Icon,
  label,
  active,
  onClick,
  badge,
  collapsed,
}: {
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
  badge?: number;
  collapsed: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm relative',
        'transition-colors duration-150',
        active
          ? 'text-text-primary border-b-2 border-accent-blue'
          : 'text-text-tertiary hover:text-text-secondary border-b-2 border-transparent'
      )}
    >
      <Icon className="w-4 h-4" />
      {!collapsed && <span>{label}</span>}
      {badge !== undefined && badge > 0 && (
        <span className="absolute top-1 right-2 w-4 h-4 flex items-center justify-center text-2xs bg-accent-blue text-white rounded-full">
          {badge}
        </span>
      )}
    </button>
  );
}

function PipelinePanel({ modes, collapsed }: { modes: ModeInfo[]; collapsed: boolean }) {
  const [expandedModes, setExpandedModes] = useState<Set<string>>(new Set());
  const resetModes = useDashboardStore((s) => s.resetModes);
  const clearActivities = useDashboardStore((s) => s.clearActivities);
  const setArtifacts = useDashboardStore((s) => s.setArtifacts);

  const toggleExpand = (modeId: string) => {
    setExpandedModes((prev) => {
      const next = new Set(prev);
      if (next.has(modeId)) {
        next.delete(modeId);
      } else {
        next.add(modeId);
      }
      return next;
    });
  };

  const handleReset = () => {
    resetModes();
    clearActivities();
    setArtifacts([]);
    toast.success('Pipeline reset to initial state');
  };

  return (
    <div className="p-2">
      {!collapsed && (
        <div className="flex items-center justify-between mb-3 px-2 py-1 bg-bg-tertiary rounded-md">
          <span className="text-xs font-medium text-text-secondary">Pipeline Status</span>
          <button
            onClick={handleReset}
            className="p-1 rounded hover:bg-bg-hover transition-colors text-text-muted hover:text-text-primary"
            title="Reset pipeline to initial state"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      )}
      {modes.map((mode, index) => (
        <ModeItem
          key={mode.id}
          mode={mode}
          index={index}
          expanded={expandedModes.has(mode.id)}
          onToggle={() => toggleExpand(mode.id)}
          collapsed={collapsed}
        />
      ))}
      {!collapsed && (
        <button
          onClick={handleReset}
          className="w-full mt-2 px-3 py-2 text-sm bg-bg-tertiary hover:bg-bg-hover rounded-md transition-colors flex items-center justify-center gap-2 text-text-secondary hover:text-text-primary"
        >
          <RotateCcw className="w-4 h-4" />
          Reset Pipeline
        </button>
      )}
    </div>
  );
}

function ModeItem({
  mode,
  expanded,
  onToggle,
  collapsed,
}: {
  mode: ModeInfo;
  index: number;
  expanded: boolean;
  onToggle: () => void;
  collapsed: boolean;
}) {
  const StatusIcon = getStatusIcon(mode.status);
  const statusColor = getStatusColor(mode.status);

  if (collapsed) {
    return (
      <div
        className={clsx(
          'relative flex items-center justify-center p-2 rounded-md mb-1 cursor-pointer',
          'hover:bg-bg-hover transition-colors',
          mode.status === 'running' && 'ring-1 ring-status-running'
        )}
        title={`Mode ${mode.id}: ${mode.name}${mode.verdict ? ` (${mode.verdict.toUpperCase()})` : ''}`}
      >
        <StatusIcon className={clsx('w-5 h-5', statusColor)} />
        {/* Verdict indicator dot */}
        {mode.verdict && (
          <span
            className={clsx(
              'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full',
              mode.verdict === 'go' && 'bg-status-success',
              mode.verdict === 'conditional' && 'bg-status-warning',
              mode.verdict === 'no_go' && 'bg-status-error'
            )}
          />
        )}
      </div>
    );
  }

  return (
    <div className="mb-1">
      <div
        onClick={onToggle}
        className={clsx(
          'mode-item',
          mode.status === 'running' && 'mode-item-current',
          mode.status === 'completed' && 'mode-item-completed',
          mode.status === 'not_started' && 'mode-item-pending'
        )}
      >
        {/* Expand/Collapse */}
        <button className="p-0.5 hover:bg-bg-hover rounded">
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-text-tertiary" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-text-tertiary" />
          )}
        </button>

        {/* Status Icon */}
        <StatusIcon className={clsx('w-4 h-4', statusColor)} />

        {/* Mode Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{mode.id}</span>
            <span className="text-text-secondary text-sm truncate">{mode.name}</span>
          </div>
          {/* Last run time */}
          {mode.lastRunAt && (
            <div className="flex items-center gap-1 text-2xs text-text-muted mt-0.5">
              <Clock className="w-3 h-3" />
              {formatDistanceToNow(new Date(mode.lastRunAt), { addSuffix: true })}
            </div>
          )}
        </div>

        {/* Verdict Badge */}
        {mode.verdict && (
          <span
            className={clsx(
              'text-2xs font-semibold px-1.5 py-0.5 rounded',
              mode.verdict === 'go' && 'bg-status-success/20 text-status-success',
              mode.verdict === 'conditional' && 'bg-status-warning/20 text-status-warning',
              mode.verdict === 'no_go' && 'bg-status-error/20 text-status-error'
            )}
          >
            {mode.verdict === 'go' ? 'GO' : mode.verdict === 'conditional' ? 'COND' : 'NO-GO'}
          </span>
        )}

        {/* Artifact Count */}
        {mode.artifactCount > 0 && (
          <span className="text-2xs text-text-muted bg-bg-tertiary px-1.5 py-0.5 rounded">
            {mode.artifactCount}
          </span>
        )}
      </div>

      {/* Expanded Actions */}
      {expanded && (
        <div className="ml-8 mt-1 flex flex-wrap gap-1 pb-1">
          <button className="btn btn-secondary text-xs py-1">
            <Play className="w-3 h-3" />
            Run
          </button>
          <button className="btn btn-ghost text-xs py-1">
            <Eye className="w-3 h-3" />
            View
          </button>
          {mode.status === 'failed' && (
            <button className="btn btn-ghost text-xs py-1 text-status-warning">
              <RotateCcw className="w-3 h-3" />
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function getStatusIcon(status: ModeStatus) {
  switch (status) {
    case 'completed':
      return CheckCircle2;
    case 'running':
      return Loader2;
    case 'failed':
      return XCircle;
    default:
      return Circle;
  }
}

function getStatusColor(status: ModeStatus) {
  switch (status) {
    case 'completed':
      return 'text-status-success';
    case 'running':
      return 'text-status-running animate-spin';
    case 'failed':
      return 'text-status-error';
    default:
      return 'text-text-muted';
  }
}

function ArtifactsPanel({ collapsed }: { collapsed: boolean }) {
  const artifacts = useDashboardStore((s) => s.artifacts);
  const setSelectedArtifact = useDashboardStore((s) => s.setSelectedArtifact);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      // TODO: Handle document upload to library
      toast.success(`Uploading ${files.length} document${files.length > 1 ? 's' : ''} to library...`);
      console.log('Upload to document library:', files);
    }
  };

  if (collapsed) {
    return (
      <div 
        className={clsx(
          "p-2 text-center text-text-muted transition-colors",
          isDragOver && "bg-accent-blue/10 text-accent-blue"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <FileBox className="w-6 h-6 mx-auto opacity-50" />
      </div>
    );
  }

  const hasArtifacts = artifacts.length > 0;

  return (
    <div 
      className={clsx(
        "relative transition-colors",
        isDragOver && "bg-accent-blue/5"
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drop overlay for artifacts panel */}
      {isDragOver && (
        <div className="absolute inset-0 z-10 border-2 border-dashed border-accent-blue bg-accent-blue/10 flex items-center justify-center rounded-lg m-2">
          <div className="text-center">
            <FileBox className="w-8 h-8 mx-auto mb-2 text-accent-blue" />
            <p className="text-sm font-medium text-accent-blue">Add to document library</p>
          </div>
        </div>
      )}

      {!hasArtifacts ? (
        <div className="p-4 text-center text-text-muted">
          <FileBox className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No artifacts yet</p>
          <p className="text-xs mt-1">Run a mode to generate artifacts</p>
          <div className="mt-3 pt-3 border-t border-border-subtle">
            <p className="text-2xs text-text-muted">Drop documents here to add to library</p>
          </div>
        </div>
      ) : (
        <div className="p-2 space-y-1">
          {/* Upload hint at top */}
          <div className="px-2 py-1 mb-2 text-center">
            <p className="text-2xs text-text-muted">Drop documents here to add to library</p>
          </div>
          
          {artifacts.map((artifact) => (
            <button
              key={artifact.id}
              onClick={() => setSelectedArtifact(artifact as any)}
              className="w-full text-left sidebar-item"
            >
              <FileBox className="w-4 h-4 text-text-tertiary flex-shrink-0" />
              <div className="min-w-0">
                <div className="text-sm truncate">{artifact.name}</div>
                <div className="text-2xs text-text-muted">Mode {artifact.modeId}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PinnedPanel({ collapsed }: { collapsed: boolean }) {
  const pinnedActivities = useDashboardStore(selectPinnedActivities);

  if (collapsed) {
    return (
      <div className="p-2 text-center text-text-muted">
        <Pin className="w-6 h-6 mx-auto opacity-50" />
      </div>
    );
  }

  if (pinnedActivities.length === 0) {
    return (
      <div className="p-4 text-center text-text-muted">
        <Pin className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No pinned items</p>
        <p className="text-xs mt-1">Pin important messages or outputs</p>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1">
      {pinnedActivities.map((activity) => (
        <div key={activity.id} className="sidebar-item hover-lift">
          <Pin className="w-4 h-4 text-accent-yellow flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-sm truncate">{activity.content || activity.type}</div>
            <div className="text-2xs text-text-muted">
              {activity.modeId ? `Mode ${activity.modeId}` : 'System'}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

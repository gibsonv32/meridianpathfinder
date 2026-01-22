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
} from 'lucide-react';
import clsx from 'clsx';
import { useDashboardStore, selectPinnedActivities } from '../store';
import { NotificationCenter } from './Notifications';
import { RunHistory } from './RunHistory';
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

  return (
    <>
    {showRunHistory && <RunHistory onClose={() => setShowRunHistory(false)} />}
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
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center hover-lift">
              <span className="text-white font-bold text-sm">M</span>
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

  return (
    <div className="p-2">
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
          'flex items-center justify-center p-2 rounded-md mb-1 cursor-pointer',
          'hover:bg-bg-hover transition-colors'
        )}
        title={`Mode ${mode.id}: ${mode.name}`}
      >
        <StatusIcon className={clsx('w-5 h-5', statusColor)} />
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
        </div>

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

  if (collapsed) {
    return (
      <div className="p-2 text-center text-text-muted">
        <FileBox className="w-6 h-6 mx-auto opacity-50" />
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className="p-4 text-center text-text-muted">
        <FileBox className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No artifacts yet</p>
        <p className="text-xs mt-1">Run a mode to generate artifacts</p>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1">
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

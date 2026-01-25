import { useState } from 'react';
import {
  Activity,
  MessageSquare,
  ChevronLeft,
  Wifi,
  WifiOff,
  RefreshCw,
  Clock,
  Server,
  Layers,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { useDashboardStore } from '../store';
import { ArtifactViewer } from './ArtifactViewer';

type DrawerView = 'artifact' | 'health' | 'summary' | 'notes';

export function ContextDrawer() {
  const selectedArtifact = useDashboardStore((s) => s.selectedArtifact);
  const connectionStatus = useDashboardStore((s) => s.connectionStatus);
  const setSelectedArtifact = useDashboardStore((s) => s.setSelectedArtifact);
  const [activeView, setActiveView] = useState<DrawerView>('health');
  const [isOpen, setIsOpen] = useState(false);

  // Auto-open when artifact is selected
  if (selectedArtifact && (!isOpen || activeView !== 'artifact')) {
    setIsOpen(true);
    setActiveView('artifact');
  }

  // If nothing to show, render collapsed sidebar with status indicators
  if (!isOpen) {
    return (
      <div className="w-12 bg-bg-secondary border-l border-border-subtle flex flex-col items-center py-4 gap-3">
        <DrawerToggleButton
          icon={Activity}
          label="System Health"
          active={false}
          onClick={() => {
            setActiveView('health');
            setIsOpen(true);
          }}
          statusColor={
            connectionStatus === 'connected'
              ? 'bg-status-success'
              : connectionStatus === 'reconnecting'
              ? 'bg-status-warning'
              : 'bg-status-error'
          }
        />
        <DrawerToggleButton
          icon={Layers}
          label="Run Summary"
          active={false}
          onClick={() => {
            setActiveView('summary');
            setIsOpen(true);
          }}
        />
        <DrawerToggleButton
          icon={MessageSquare}
          label="Notes"
          active={false}
          onClick={() => {
            setActiveView('notes');
            setIsOpen(true);
          }}
        />
        
        {/* Quick close selected artifact if any */}
        {selectedArtifact && (
          <div className="mt-auto">
            <DrawerToggleButton
              icon={CheckCircle2}
              label="View Selected Artifact"
              active={true}
              onClick={() => {
                setActiveView('artifact');
                setIsOpen(true);
              }}
              statusColor="bg-accent-blue"
            />
          </div>
        )}
      </div>
    );
  }

  // Render full drawer
  return (
    <div className="w-96 bg-bg-secondary border-l border-border-subtle flex flex-col animate-fade-in">
      {/* If artifact view, use existing ArtifactViewer */}
      {activeView === 'artifact' && selectedArtifact ? (
        <ArtifactViewer />
      ) : (
        <>
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border-subtle">
            <div className="flex items-center gap-3">
              {activeView === 'health' && <Activity className="w-5 h-5 text-accent-blue" />}
              {activeView === 'summary' && <Layers className="w-5 h-5 text-accent-purple" />}
              {activeView === 'notes' && <MessageSquare className="w-5 h-5 text-accent-green" />}
              <h2 className="font-semibold">
                {activeView === 'health' && 'System Health'}
                {activeView === 'summary' && 'Run Summary'}
                {activeView === 'notes' && 'Notes'}
              </h2>
            </div>
            <div className="flex items-center gap-1">
              {selectedArtifact && (
                <button
                  onClick={() => setSelectedArtifact(null)}
                  className="p-1.5 text-text-muted hover:text-text-primary hover:bg-bg-hover rounded"
                  title="Clear selection"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-text-muted hover:text-text-primary hover:bg-bg-hover rounded"
                title="Close panel"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* View tabs - show only when not viewing artifact */}
          {activeView !== 'artifact' && (
            <div className="flex border-b border-border-subtle">
              <ViewTab
                active={activeView === 'health'}
                onClick={() => setActiveView('health')}
                icon={Activity}
                label="Health"
              />
              <ViewTab
                active={activeView === 'summary'}
                onClick={() => setActiveView('summary')}
                icon={Layers}
                label="Summary"
              />
              <ViewTab
                active={activeView === 'notes'}
                onClick={() => setActiveView('notes')}
                icon={MessageSquare}
                label="Notes"
              />
            </div>
          )}

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {activeView === 'health' && <SystemHealthView />}
            {activeView === 'summary' && <RunSummaryView />}
            {activeView === 'notes' && <NotesView />}
          </div>
        </>
      )}
    </div>
  );
}

function DrawerToggleButton({
  icon: Icon,
  label,
  active,
  onClick,
  statusColor,
}: {
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
  statusColor?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'relative p-2 rounded-lg transition-colors',
        active ? 'bg-accent-blue/20 text-accent-blue' : 'text-text-muted hover:bg-bg-hover hover:text-text-primary'
      )}
      title={label}
    >
      <Icon className="w-5 h-5" />
      {statusColor && (
        <span className={clsx('absolute top-1 right-1 w-2 h-2 rounded-full', statusColor)} />
      )}
    </button>
  );
}

function ViewTab({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ElementType;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex-1 flex items-center justify-center gap-2 py-2.5 text-sm transition-colors',
        active
          ? 'text-text-primary border-b-2 border-accent-blue'
          : 'text-text-tertiary hover:text-text-secondary border-b-2 border-transparent'
      )}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}

// -----------------------------------------------------------------------------
// System Health View
// -----------------------------------------------------------------------------

function SystemHealthView() {
  const connectionStatus = useDashboardStore((s) => s.connectionStatus);
  const setConnectionStatus = useDashboardStore((s) => s.setConnectionStatus);
  const modes = useDashboardStore((s) => s.modes);

  const runningModes = modes.filter((m) => m.status === 'running');
  const completedModes = modes.filter((m) => m.status === 'completed');
  const failedModes = modes.filter((m) => m.status === 'failed');

  const handleReconnect = () => {
    setConnectionStatus('reconnecting');
    // Simulate reconnection
    setTimeout(() => {
      setConnectionStatus('connected');
    }, 2000);
  };

  return (
    <div className="p-4 space-y-6">
      {/* Connection Status */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">Connection</h3>
        <div className="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg">
          <div className="flex items-center gap-3">
            {connectionStatus === 'connected' ? (
              <Wifi className="w-5 h-5 text-status-success" />
            ) : connectionStatus === 'reconnecting' ? (
              <RefreshCw className="w-5 h-5 text-status-warning animate-spin" />
            ) : (
              <WifiOff className="w-5 h-5 text-status-error" />
            )}
            <div>
              <div className="font-medium capitalize">{connectionStatus}</div>
              <div className="text-xs text-text-muted">WebSocket</div>
            </div>
          </div>
          {connectionStatus !== 'connected' && (
            <button
              onClick={handleReconnect}
              className="btn btn-secondary btn-sm"
            >
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Pipeline Status */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">Pipeline</h3>
        <div className="grid grid-cols-3 gap-2">
          <StatusCard
            label="Running"
            count={runningModes.length}
            icon={RefreshCw}
            color="text-status-running"
            bgColor="bg-status-running/10"
          />
          <StatusCard
            label="Complete"
            count={completedModes.length}
            icon={CheckCircle2}
            color="text-status-success"
            bgColor="bg-status-success/10"
          />
          <StatusCard
            label="Failed"
            count={failedModes.length}
            icon={XCircle}
            color="text-status-error"
            bgColor="bg-status-error/10"
          />
        </div>
      </div>

      {/* Backend Info */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">Backend</h3>
        <div className="space-y-2">
          <InfoRow icon={Server} label="API" value="http://localhost:8000" />
          <InfoRow icon={Clock} label="Last heartbeat" value="Just now" />
          <InfoRow icon={Activity} label="Latency" value="< 50ms" />
        </div>
      </div>

      {/* Diagnostics */}
      <div className="pt-4 border-t border-border-subtle">
        <button className="btn btn-secondary w-full">
          Export Diagnostics
        </button>
      </div>
    </div>
  );
}

function StatusCard({
  label,
  count,
  icon: Icon,
  color,
  bgColor,
}: {
  label: string;
  count: number;
  icon: React.ElementType;
  color: string;
  bgColor: string;
}) {
  return (
    <div className={clsx('p-3 rounded-lg text-center', bgColor)}>
      <Icon className={clsx('w-5 h-5 mx-auto mb-1', color)} />
      <div className={clsx('text-lg font-semibold', color)}>{count}</div>
      <div className="text-xs text-text-muted">{label}</div>
    </div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2 text-text-secondary">
        <Icon className="w-4 h-4" />
        <span className="text-sm">{label}</span>
      </div>
      <span className="text-sm font-mono text-text-primary">{value}</span>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Run Summary View
// -----------------------------------------------------------------------------

function RunSummaryView() {
  const modes = useDashboardStore((s) => s.modes);
  const artifacts = useDashboardStore((s) => s.artifacts);

  const completedModes = modes.filter((m) => m.status === 'completed');
  const totalArtifacts = artifacts.length;

  return (
    <div className="p-4 space-y-6">
      {/* Overview */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">Current Run</h3>
        <div className="p-4 bg-bg-tertiary rounded-lg space-y-3">
          <div className="flex justify-between">
            <span className="text-text-secondary">Modes completed</span>
            <span className="font-medium">{completedModes.length} / {modes.length}</span>
          </div>
          <div className="w-full h-2 bg-bg-primary rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-blue transition-all"
              style={{ width: `${(completedModes.length / modes.length) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Artifacts generated</span>
            <span className="font-medium">{totalArtifacts}</span>
          </div>
        </div>
      </div>

      {/* Mode Verdicts */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">Verdicts</h3>
        <div className="space-y-2">
          {completedModes.map((mode) => (
            <div
              key={mode.id}
              className="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg"
            >
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-status-success" />
                <span className="text-sm">Mode {mode.id}: {mode.name}</span>
              </div>
              {mode.verdict && (
                <span
                  className={clsx(
                    'text-xs px-2 py-0.5 rounded font-medium',
                    mode.verdict === 'go' && 'bg-status-success/20 text-status-success',
                    mode.verdict === 'conditional' && 'bg-status-warning/20 text-status-warning',
                    mode.verdict === 'no_go' && 'bg-status-error/20 text-status-error'
                  )}
                >
                  {mode.verdict.toUpperCase()}
                </span>
              )}
            </div>
          ))}
          {completedModes.length === 0 && (
            <div className="text-sm text-text-muted text-center py-4">
              No modes completed yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Notes View
// -----------------------------------------------------------------------------

function NotesView() {
  const activities = useDashboardStore((s) => s.activities);
  const annotatedActivities = activities.filter((a) => a.annotation);

  return (
    <div className="p-4 space-y-4">
      <div className="text-sm text-text-secondary">
        Notes and annotations from the activity feed appear here.
      </div>

      {annotatedActivities.length === 0 ? (
        <div className="text-center py-8">
          <MessageSquare className="w-12 h-12 mx-auto mb-3 text-text-muted opacity-50" />
          <p className="text-text-muted">No notes yet</p>
          <p className="text-xs text-text-muted mt-1">
            Add notes to activities using the annotation feature
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {annotatedActivities.map((activity) => (
            <div
              key={activity.id}
              className="p-3 bg-bg-tertiary rounded-lg border-l-2 border-accent-yellow"
            >
              <div className="text-sm">{activity.annotation}</div>
              <div className="text-xs text-text-muted mt-2">
                {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                {activity.modeId && ` • Mode ${activity.modeId}`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

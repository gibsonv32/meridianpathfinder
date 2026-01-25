import { useState, useCallback } from 'react';
import {
  Activity,
  X,
  Pause,
  Play,
  Square,
  ChevronDown,
  ChevronRight,
  Clock,
  Zap,
  Settings,
  Layers,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import type { ModeId } from '../types';

export interface QueuedRun {
  id: string;
  projectId: string;
  projectName: string;
  modeId: ModeId;
  modeName: string;
  status: 'queued' | 'running' | 'paused' | 'cancelled' | 'completed' | 'failed';
  priority: 'low' | 'normal' | 'high';
  queuedAt: string;
  startedAt?: string;
  completedAt?: string;
  progress?: number;
  parentRunId?: string; // For subtree relationships
  dependencies?: string[]; // Other run IDs this depends on
  estimatedDuration?: number; // in minutes
  resourceRequirement?: {
    cpu: number;
    memory: number;
    gpu?: boolean;
  };
}

interface RunQueueProps {
  onClose: () => void;
  className?: string;
}

// Mock queue data
const mockQueue: QueuedRun[] = [
  {
    id: 'run_001',
    projectId: 'proj_1',
    projectName: 'MERIDIAN',
    modeId: '0',
    modeName: 'EDA',
    status: 'running',
    priority: 'high',
    queuedAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    startedAt: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    progress: 65,
    estimatedDuration: 15,
    resourceRequirement: { cpu: 2, memory: 4096 },
  },
  {
    id: 'run_002',
    projectId: 'proj_1',
    projectName: 'MERIDIAN',
    modeId: '1',
    modeName: 'Decision Intel',
    status: 'queued',
    priority: 'normal',
    queuedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    dependencies: ['run_001'],
    estimatedDuration: 20,
    resourceRequirement: { cpu: 1, memory: 2048 },
  },
  {
    id: 'run_003',
    projectId: 'proj_2',
    projectName: 'Customer Analytics',
    modeId: '0',
    modeName: 'EDA',
    status: 'queued',
    priority: 'low',
    queuedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    estimatedDuration: 10,
    resourceRequirement: { cpu: 1, memory: 1024 },
  },
];

export function RunQueue({ onClose, className }: RunQueueProps) {
  const [queue, setQueue] = useState<QueuedRun[]>(mockQueue);
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());
  const [concurrencyLimit, setConcurrencyLimit] = useState(2);
  const [showSettings, setShowSettings] = useState(false);

  const runningRuns = queue.filter((r) => r.status === 'running');
  const queuedRuns = queue.filter((r) => r.status === 'queued');
  const completedRuns = queue.filter((r) => ['completed', 'failed', 'cancelled'].includes(r.status));

  const toggleExpand = useCallback((runId: string) => {
    setExpandedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  }, []);

  const cancelRun = useCallback((runId: string, cancelSubtree = false) => {
    setQueue((prev) =>
      prev.map((run) => {
        if (run.id === runId || (cancelSubtree && run.parentRunId === runId)) {
          return { ...run, status: 'cancelled' as const };
        }
        return run;
      })
    );
    toast.success(`Run cancelled${cancelSubtree ? ' (including subtree)' : ''}`);
  }, []);

  const pauseRun = useCallback((runId: string) => {
    setQueue((prev) =>
      prev.map((run) =>
        run.id === runId
          ? { ...run, status: run.status === 'paused' ? 'running' : 'paused' }
          : run
      )
    );
    const run = queue.find((r) => r.id === runId);
    toast.success(`Run ${run?.status === 'paused' ? 'resumed' : 'paused'}`);
  }, [queue]);

  const clearCompleted = useCallback(() => {
    setQueue((prev) => prev.filter((run) => !['completed', 'failed', 'cancelled'].includes(run.status)));
    toast.success('Cleared completed runs');
  }, []);

  return (
    <div className={clsx('flex flex-col bg-bg-secondary border-l border-border-subtle', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border-subtle">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-accent-blue" />
          <h2 className="font-semibold">Run Queue</h2>
          <div className="flex items-center gap-1">
            <span className="text-xs text-text-muted">
              {runningRuns.length}/{concurrencyLimit} running
            </span>
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full" />
            <span className="text-xs text-text-muted">{queuedRuns.length} queued</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-1.5 hover:bg-bg-hover rounded transition-colors text-text-muted hover:text-text-primary"
            title="Queue settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-bg-hover rounded transition-colors text-text-muted hover:text-text-primary"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="p-4 border-b border-border-subtle bg-bg-tertiary">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1">Concurrency Limit</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={concurrencyLimit}
                  onChange={(e) => setConcurrencyLimit(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-mono w-8 text-center">{concurrencyLimit}</span>
              </div>
              <p className="text-xs text-text-muted mt-1">
                Maximum number of runs that can execute simultaneously
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={clearCompleted}
                className="btn btn-secondary btn-sm"
                disabled={completedRuns.length === 0}
              >
                Clear Completed ({completedRuns.length})
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Queue Status Overview */}
      <div className="p-3 border-b border-border-subtle">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="p-2 bg-status-running/10 rounded">
            <div className="text-lg font-semibold text-status-running">{runningRuns.length}</div>
            <div className="text-xs text-text-muted">Running</div>
          </div>
          <div className="p-2 bg-accent-yellow/10 rounded">
            <div className="text-lg font-semibold text-accent-yellow">{queuedRuns.length}</div>
            <div className="text-xs text-text-muted">Queued</div>
          </div>
          <div className="p-2 bg-text-muted/10 rounded">
            <div className="text-lg font-semibold text-text-muted">{completedRuns.length}</div>
            <div className="text-xs text-text-muted">Complete</div>
          </div>
        </div>
      </div>

      {/* Queue List */}
      <div className="flex-1 overflow-y-auto">
        {queue.length === 0 ? (
          <div className="p-8 text-center text-text-muted">
            <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No runs in queue</p>
            <p className="text-xs mt-1">Start a mode to see it here</p>
          </div>
        ) : (
          <div className="divide-y divide-border-subtle">
            {/* Running Runs */}
            {runningRuns.length > 0 && (
              <>
                <div className="px-4 py-2 bg-status-running/5">
                  <h3 className="text-xs font-medium text-status-running uppercase tracking-wide">
                    Running ({runningRuns.length})
                  </h3>
                </div>
                {runningRuns.map((run) => (
                  <RunQueueItem
                    key={run.id}
                    run={run}
                    expanded={expandedRuns.has(run.id)}
                    onToggleExpand={() => toggleExpand(run.id)}
                    onCancel={(cancelSubtree) => cancelRun(run.id, cancelSubtree)}
                    onPause={() => pauseRun(run.id)}
                  />
                ))}
              </>
            )}

            {/* Queued Runs */}
            {queuedRuns.length > 0 && (
              <>
                <div className="px-4 py-2 bg-accent-yellow/5">
                  <h3 className="text-xs font-medium text-accent-yellow uppercase tracking-wide">
                    Queued ({queuedRuns.length})
                  </h3>
                </div>
                {queuedRuns.map((run) => (
                  <RunQueueItem
                    key={run.id}
                    run={run}
                    expanded={expandedRuns.has(run.id)}
                    onToggleExpand={() => toggleExpand(run.id)}
                    onCancel={(cancelSubtree) => cancelRun(run.id, cancelSubtree)}
                    onPause={() => pauseRun(run.id)}
                  />
                ))}
              </>
            )}

            {/* Completed Runs */}
            {completedRuns.length > 0 && (
              <>
                <div className="px-4 py-2 bg-text-muted/5">
                  <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide">
                    Completed ({completedRuns.length})
                  </h3>
                </div>
                {completedRuns.slice(0, 5).map((run) => (
                  <RunQueueItem
                    key={run.id}
                    run={run}
                    expanded={expandedRuns.has(run.id)}
                    onToggleExpand={() => toggleExpand(run.id)}
                    onCancel={(cancelSubtree) => cancelRun(run.id, cancelSubtree)}
                    onPause={() => pauseRun(run.id)}
                  />
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface RunQueueItemProps {
  run: QueuedRun;
  expanded: boolean;
  onToggleExpand: () => void;
  onCancel: (cancelSubtree: boolean) => void;
  onPause: () => void;
}

function RunQueueItem({ run, expanded, onToggleExpand, onCancel, onPause }: RunQueueItemProps) {
  const canCancel = ['queued', 'running', 'paused'].includes(run.status);
  const canPause = ['running', 'paused'].includes(run.status);

  const statusConfig = {
    queued: { icon: Clock, color: 'text-accent-yellow', bg: 'bg-accent-yellow/10' },
    running: { icon: Zap, color: 'text-status-running', bg: 'bg-status-running/10' },
    paused: { icon: Pause, color: 'text-accent-orange', bg: 'bg-accent-orange/10' },
    completed: { icon: CheckCircle2, color: 'text-status-success', bg: 'bg-status-success/10' },
    failed: { icon: XCircle, color: 'text-status-error', bg: 'bg-status-error/10' },
    cancelled: { icon: Square, color: 'text-text-muted', bg: 'bg-text-muted/10' },
  };

  const config = statusConfig[run.status];
  const Icon = config.icon;

  return (
    <div className="p-4">
      <div className="flex items-center gap-3">
        {/* Expand/Collapse */}
        <button
          onClick={onToggleExpand}
          className="p-1 hover:bg-bg-hover rounded transition-colors flex-shrink-0"
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-text-muted" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-muted" />
          )}
        </button>

        {/* Status Icon */}
        <div className={clsx('w-8 h-8 rounded flex items-center justify-center flex-shrink-0', config.bg)}>
          <Icon className={clsx('w-4 h-4', config.color)} />
        </div>

        {/* Run Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium">Mode {run.modeId}: {run.modeName}</span>
            <span className={clsx('text-xs px-1.5 py-0.5 rounded font-medium capitalize', config.bg, config.color)}>
              {run.status}
            </span>
            {run.priority !== 'normal' && (
              <span className={clsx(
                'text-xs px-1.5 py-0.5 rounded font-medium',
                run.priority === 'high' 
                  ? 'bg-status-error/20 text-status-error' 
                  : 'bg-text-muted/20 text-text-muted'
              )}>
                {run.priority}
              </span>
            )}
          </div>
          <div className="text-sm text-text-secondary">
            {run.projectName} • Queued {formatDistanceToNow(new Date(run.queuedAt), { addSuffix: true })}
          </div>
          
          {/* Progress bar for running tasks */}
          {run.status === 'running' && run.progress !== undefined && (
            <div className="mt-2 w-full h-1.5 bg-bg-primary rounded-full overflow-hidden">
              <div
                className="h-full bg-status-running transition-all duration-500"
                style={{ width: `${run.progress}%` }}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {canPause && (
            <button
              onClick={onPause}
              className="p-1.5 hover:bg-bg-hover rounded transition-colors text-text-muted hover:text-text-primary"
              title={run.status === 'paused' ? 'Resume run' : 'Pause run'}
            >
              {run.status === 'paused' ? (
                <Play className="w-4 h-4" />
              ) : (
                <Pause className="w-4 h-4" />
              )}
            </button>
          )}
          {canCancel && (
            <>
              <button
                onClick={() => onCancel(false)}
                className="p-1.5 hover:bg-bg-hover rounded transition-colors text-text-muted hover:text-status-error"
                title="Cancel run"
              >
                <X className="w-4 h-4" />
              </button>
              {run.parentRunId && (
                <button
                  onClick={() => onCancel(true)}
                  className="p-1.5 hover:bg-bg-hover rounded transition-colors text-text-muted hover:text-status-error"
                  title="Cancel run and subtree"
                >
                  <Layers className="w-4 h-4" />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-3 ml-8 space-y-3 p-3 bg-bg-tertiary rounded-lg">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-text-muted">Run ID:</span>
              <span className="ml-2 font-mono">{run.id}</span>
            </div>
            {run.startedAt && (
              <div>
                <span className="text-text-muted">Started:</span>
                <span className="ml-2">{formatDistanceToNow(new Date(run.startedAt), { addSuffix: true })}</span>
              </div>
            )}
            {run.estimatedDuration && (
              <div>
                <span className="text-text-muted">Est. Duration:</span>
                <span className="ml-2">{run.estimatedDuration}min</span>
              </div>
            )}
            {run.resourceRequirement && (
              <div>
                <span className="text-text-muted">Resources:</span>
                <span className="ml-2">
                  {run.resourceRequirement.cpu} CPU, {Math.round(run.resourceRequirement.memory / 1024)}GB RAM
                  {run.resourceRequirement.gpu && ', GPU'}
                </span>
              </div>
            )}
          </div>

          {run.dependencies && run.dependencies.length > 0 && (
            <div>
              <span className="text-text-muted text-sm">Dependencies:</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {run.dependencies.map((depId) => (
                  <span
                    key={depId}
                    className="text-xs px-2 py-1 bg-bg-secondary rounded font-mono"
                  >
                    {depId}
                  </span>
                ))}
              </div>
            </div>
          )}

          {run.status === 'running' && run.progress !== undefined && (
            <div>
              <span className="text-text-muted text-sm">Progress: {Math.round(run.progress)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
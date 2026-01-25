import { useState, useMemo } from 'react';
import {
  History,
  GitCompare,
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  RotateCcw,
  FileBox,
  X,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow, format } from 'date-fns';
import type { ModeId, ModeStatus } from '../types';

interface RunRecord {
  id: string;
  modeId: ModeId;
  status: ModeStatus;
  startedAt: string;
  completedAt?: string;
  duration?: number;
  artifactIds: string[];
  params?: Record<string, unknown>;
  error?: string;
}

// Mock run history data
const mockRunHistory: RunRecord[] = [
  {
    id: 'run-001',
    modeId: '0',
    status: 'completed',
    startedAt: new Date(Date.now() - 3600000).toISOString(),
    completedAt: new Date(Date.now() - 3540000).toISOString(),
    duration: 60000,
    artifactIds: ['art-001'],
  },
  {
    id: 'run-002',
    modeId: '1',
    status: 'completed',
    startedAt: new Date(Date.now() - 3500000).toISOString(),
    completedAt: new Date(Date.now() - 3400000).toISOString(),
    duration: 100000,
    artifactIds: ['art-002'],
  },
  {
    id: 'run-003',
    modeId: '2',
    status: 'failed',
    startedAt: new Date(Date.now() - 3300000).toISOString(),
    completedAt: new Date(Date.now() - 3280000).toISOString(),
    duration: 20000,
    artifactIds: [],
    error: 'Validation error: Target column not found in dataset',
  },
  {
    id: 'run-004',
    modeId: '2',
    status: 'completed',
    startedAt: new Date(Date.now() - 1800000).toISOString(),
    completedAt: new Date(Date.now() - 1700000).toISOString(),
    duration: 100000,
    artifactIds: ['art-003'],
    params: { target: 'churn', data: 'customer_data.csv' },
  },
];

export function RunHistory({ onClose }: { onClose: () => void }) {
  const [selectedRuns, setSelectedRuns] = useState<Set<string>>(new Set());
  const [filterMode, setFilterMode] = useState<ModeId | 'all'>('all');
  const [showCompare, setShowCompare] = useState(false);

  const filteredHistory = useMemo(() => {
    if (filterMode === 'all') return mockRunHistory;
    return mockRunHistory.filter((r) => r.modeId === filterMode);
  }, [filterMode]);

  const toggleRunSelection = (runId: string) => {
    setSelectedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else if (next.size < 2) {
        next.add(runId);
      }
      return next;
    });
  };

  const canCompare = selectedRuns.size === 2;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[80vh] bg-bg-secondary border border-border rounded-xl shadow-2xl overflow-hidden animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
          <div className="flex items-center gap-3">
            <History className="w-5 h-5 text-accent-blue" />
            <h2 className="text-lg font-semibold">Run History</h2>
          </div>
          <div className="flex items-center gap-3">
            {canCompare && (
              <button
                onClick={() => setShowCompare(true)}
                className="btn btn-primary"
              >
                <GitCompare className="w-4 h-4" />
                Compare Selected
              </button>
            )}
            <button onClick={onClose} className="btn btn-icon btn-ghost">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Filter */}
        <div className="px-6 py-3 border-b border-border-subtle flex items-center gap-2">
          <span className="text-sm text-text-secondary">Filter by mode:</span>
          <select
            value={filterMode}
            onChange={(e) => setFilterMode(e.target.value as ModeId | 'all')}
            className="input-base px-3 py-1.5 text-sm"
          >
            <option value="all">All Modes</option>
            {['0', '0.5', '1', '2', '3', '4', '5', '6', '6.5', '7'].map((m) => (
              <option key={m} value={m}>Mode {m}</option>
            ))}
          </select>
          {selectedRuns.size > 0 && (
            <span className="text-sm text-text-muted ml-auto">
              {selectedRuns.size}/2 selected for comparison
            </span>
          )}
        </div>

        {/* Run List */}
        <div className="overflow-y-auto max-h-[calc(80vh-140px)]">
          {filteredHistory.length === 0 ? (
            <div className="p-12 text-center text-text-muted">
              <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No runs found</p>
            </div>
          ) : (
            <div className="divide-y divide-border-subtle">
              {filteredHistory.map((run) => (
                <RunHistoryItem
                  key={run.id}
                  run={run}
                  selected={selectedRuns.has(run.id)}
                  onToggleSelect={() => toggleRunSelection(run.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Compare Modal */}
        {showCompare && canCompare && (
          <CompareView
            runIds={Array.from(selectedRuns)}
            runs={mockRunHistory}
            onClose={() => setShowCompare(false)}
          />
        )}
      </div>
    </div>
  );
}

function RunHistoryItem({
  run,
  selected,
  onToggleSelect,
}: {
  run: RunRecord;
  selected: boolean;
  onToggleSelect: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const StatusIcon = getStatusIcon(run.status);
  const statusColor = getStatusColor(run.status);

  return (
    <div className={clsx('transition-colors', selected && 'bg-accent-blue/5')}>
      <div className="flex items-center gap-4 px-6 py-4">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
          className="w-4 h-4 rounded border-border-subtle bg-bg-tertiary accent-accent-blue"
        />

        {/* Expand */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 hover:bg-bg-hover rounded"
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-text-tertiary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-tertiary" />
          )}
        </button>

        {/* Status */}
        <StatusIcon className={clsx('w-5 h-5', statusColor)} />

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium">Mode {run.modeId}</span>
            <span className={clsx('status-pill', `status-pill-${run.status}`)}>
              {run.status}
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm text-text-secondary mt-0.5">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {formatDistanceToNow(new Date(run.startedAt), { addSuffix: true })}
            </span>
            {run.duration && (
              <span>{(run.duration / 1000).toFixed(1)}s</span>
            )}
            {run.artifactIds.length > 0 && (
              <span className="flex items-center gap-1">
                <FileBox className="w-3.5 h-3.5" />
                {run.artifactIds.length} artifact{run.artifactIds.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-icon" title="Rerun">
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-6 pb-4 ml-14 space-y-3">
          {run.params && (
            <div>
              <div className="text-xs text-text-muted mb-1">Parameters</div>
              <div className="bg-bg-primary rounded-md p-3 font-mono text-sm">
                {Object.entries(run.params).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-accent-blue">{key}</span>
                    <span className="text-text-muted">: </span>
                    <span className="text-accent-orange">"{String(value)}"</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {run.error && (
            <div>
              <div className="text-xs text-status-error mb-1">Error</div>
              <div className="bg-status-error/10 border border-status-error/30 rounded-md p-3 text-sm text-status-error">
                {run.error}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span>Run ID: {run.id}</span>
            <span>•</span>
            <span>Started: {format(new Date(run.startedAt), 'PPpp')}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function CompareView({
  runIds,
  runs,
  onClose,
}: {
  runIds: string[];
  runs: RunRecord[];
  onClose: () => void;
}) {
  const [run1, run2] = runIds.map((id) => runs.find((r) => r.id === id)!);

  return (
    <div className="absolute inset-0 bg-bg-secondary z-10 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle sticky top-0 bg-bg-secondary">
        <div className="flex items-center gap-3">
          <GitCompare className="w-5 h-5 text-accent-purple" />
          <h2 className="text-lg font-semibold">Compare Runs</h2>
        </div>
        <button onClick={onClose} className="btn btn-secondary">
          Back to History
        </button>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-2 divide-x divide-border-subtle">
        {[run1, run2].map((run) => (
          <div key={run.id} className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-lg font-medium">Mode {run.modeId}</span>
              <span className={clsx('status-pill', `status-pill-${run.status}`)}>
                {run.status}
              </span>
            </div>

            <div className="space-y-4">
              <CompareRow label="Started" value={format(new Date(run.startedAt), 'PPpp')} />
              <CompareRow label="Duration" value={run.duration ? `${(run.duration / 1000).toFixed(1)}s` : '-'} />
              <CompareRow label="Artifacts" value={`${run.artifactIds.length} created`} />
              
              {run.params && (
                <div>
                  <div className="text-xs text-text-muted mb-1">Parameters</div>
                  <div className="bg-bg-primary rounded-md p-3 font-mono text-sm">
                    {Object.entries(run.params).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-accent-blue">{key}</span>: {String(value)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {run.error && (
                <div>
                  <div className="text-xs text-status-error mb-1">Error</div>
                  <div className="bg-status-error/10 rounded-md p-3 text-sm text-status-error">
                    {run.error}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Diff Summary */}
      <div className="px-6 py-4 border-t border-border-subtle bg-bg-tertiary">
        <h3 className="font-medium mb-2">Differences</h3>
        <ul className="text-sm text-text-secondary space-y-1">
          {run1.status !== run2.status && (
            <li>• Status: <span className="text-text-primary">{run1.status}</span> → <span className="text-text-primary">{run2.status}</span></li>
          )}
          {run1.duration !== run2.duration && (
            <li>• Duration changed by {Math.abs((run1.duration || 0) - (run2.duration || 0)) / 1000}s</li>
          )}
          {run1.artifactIds.length !== run2.artifactIds.length && (
            <li>• Artifact count: {run1.artifactIds.length} → {run2.artifactIds.length}</li>
          )}
        </ul>
      </div>
    </div>
  );
}

function CompareRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-text-muted mb-0.5">{label}</div>
      <div className="text-sm">{value}</div>
    </div>
  );
}

function getStatusIcon(status: ModeStatus) {
  switch (status) {
    case 'completed': return CheckCircle2;
    case 'running': return Loader2;
    case 'failed': return XCircle;
    default: return Clock;
  }
}

function getStatusColor(status: ModeStatus) {
  switch (status) {
    case 'completed': return 'text-status-success';
    case 'running': return 'text-status-running animate-spin';
    case 'failed': return 'text-status-error';
    default: return 'text-text-muted';
  }
}

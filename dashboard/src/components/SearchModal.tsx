import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  X,
  FileBox,
  Terminal,
  MessageSquare,
  Layers,
  Clock,
  ArrowRight,
  Play,
  RefreshCw,
  Settings,
  Activity,
  Wifi,
  Zap,
  Command,
  History,
  Trash2,
  Copy,
  RotateCcw,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { useDashboardStore } from '../store';
import { api } from '../api/client';
import toast from 'react-hot-toast';

type SearchCategory = 'all' | 'actions' | 'activities' | 'artifacts' | 'modes' | 'recent';

interface SearchResult {
  id: string;
  type: 'action' | 'activity' | 'artifact' | 'mode' | 'recent';
  title: string;
  subtitle: string;
  timestamp?: string;
  icon: React.ElementType;
  action?: () => void;
  keywords?: string[];
}

export function SearchModal() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<SearchCategory>('all');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const { setSearchOpen, activities, artifacts, modes, setSelectedArtifact } = useDashboardStore();

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSearchOpen(false);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && results[selectedIndex]) {
        handleSelect(results[selectedIndex]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIndex]);

  const resetModes = useDashboardStore((s) => s.resetModes);
  const clearActivities = useDashboardStore((s) => s.clearActivities);
  const updateMode = useDashboardStore((s) => s.updateMode);
  const addActivity = useDashboardStore((s) => s.addActivity);

  // Run mode handler
  const handleRunMode = useCallback(async (modeId: string, modeName: string) => {
    try {
      await api.runMode(modeId);
      updateMode(modeId as any, { status: 'running' });
      addActivity({
        id: crypto.randomUUID(),
        type: 'mode_started',
        timestamp: new Date().toISOString(),
        modeId: modeId as any,
        content: `Starting ${modeName}`,
      });
      toast.success(`Starting Mode ${modeId}: ${modeName}`);
    } catch (error) {
      toast.error(`Failed to start mode: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [updateMode, addActivity]);

  // Available actions for command palette
  const actions: SearchResult[] = useMemo(() => [
    // Run modes
    {
      id: 'run-mode-0',
      type: 'action',
      title: 'Run Mode 0: EDA',
      subtitle: 'Start Exploratory Data Analysis',
      icon: Play,
      keywords: ['eda', 'analysis', 'explore', 'data'],
      action: () => handleRunMode('0', 'EDA'),
    },
    {
      id: 'run-mode-0.5',
      type: 'action',
      title: 'Run Mode 0.5: Opportunity',
      subtitle: 'Discover opportunities in your data',
      icon: Play,
      keywords: ['opportunity', 'discover'],
      action: () => handleRunMode('0.5', 'Opportunity'),
    },
    {
      id: 'run-mode-1',
      type: 'action',
      title: 'Run Mode 1: Decision Intel',
      subtitle: 'Build decision intelligence profile',
      icon: Play,
      keywords: ['decision', 'intelligence', 'profile'],
      action: () => handleRunMode('1', 'Decision Intel'),
    },
    {
      id: 'run-mode-2',
      type: 'action',
      title: 'Run Mode 2: Feasibility',
      subtitle: 'Assess feasibility of your approach',
      icon: Play,
      keywords: ['feasibility', 'assess'],
      action: () => handleRunMode('2', 'Feasibility'),
    },
    {
      id: 'run-mode-3',
      type: 'action',
      title: 'Run Mode 3: Strategy',
      subtitle: 'Define model strategy and features',
      icon: Play,
      keywords: ['strategy', 'model', 'features'],
      action: () => handleRunMode('3', 'Strategy'),
    },
    {
      id: 'run-mode-4',
      type: 'action',
      title: 'Run Mode 4: Business Case',
      subtitle: 'Generate business case scorecard',
      icon: Play,
      keywords: ['business', 'case', 'scorecard', 'roi'],
      action: () => handleRunMode('4', 'Business Case'),
    },
    {
      id: 'run-mode-5',
      type: 'action',
      title: 'Run Mode 5: Code Gen (Claude)',
      subtitle: 'Generate production code with Claude',
      icon: Play,
      keywords: ['code', 'generate', 'claude', 'implementation'],
      action: () => handleRunMode('5', 'Code Gen'),
    },
    {
      id: 'run-mode-6',
      type: 'action',
      title: 'Run Mode 6: Execution',
      subtitle: 'Execute and operationalize',
      icon: Play,
      keywords: ['execute', 'operations', 'deploy'],
      action: () => handleRunMode('6', 'Execution'),
    },
    {
      id: 'run-mode-7',
      type: 'action',
      title: 'Run Mode 7: Delivery',
      subtitle: 'Generate delivery manifest',
      icon: Play,
      keywords: ['delivery', 'manifest', 'final'],
      action: () => handleRunMode('7', 'Delivery'),
    },
    // Pipeline actions
    {
      id: 'run-pipeline',
      type: 'action',
      title: 'Run Full Pipeline',
      subtitle: 'Execute all modes in sequence (0→7)',
      icon: Zap,
      keywords: ['pipeline', 'full', 'all', 'sequence'],
      action: () => {
        handleRunMode('0', 'Full Pipeline');
        toast.success('Starting full pipeline from Mode 0');
      },
    },
    {
      id: 'retry-failed',
      type: 'action',
      title: 'Retry Failed Modes',
      subtitle: 'Retry all modes that failed',
      icon: RefreshCw,
      keywords: ['retry', 'failed', 'error'],
      action: () => {
        const failedModes = modes.filter(m => m.status === 'failed');
        if (failedModes.length === 0) {
          toast('No failed modes to retry');
        } else {
          failedModes.forEach(m => handleRunMode(m.id, m.name));
        }
      },
    },
    {
      id: 'reset-pipeline',
      type: 'action',
      title: 'Reset Pipeline',
      subtitle: 'Clear all progress and start fresh',
      icon: RotateCcw,
      keywords: ['reset', 'clear', 'fresh', 'restart'],
      action: () => {
        resetModes();
        clearActivities();
        toast.success('Pipeline reset to initial state');
      },
    },
    // System actions
    {
      id: 'clear-feed',
      type: 'action',
      title: 'Clear Activity Feed',
      subtitle: 'Remove all messages from the feed',
      icon: Trash2,
      keywords: ['clear', 'feed', 'messages', 'clean'],
      action: () => {
        clearActivities();
        toast.success('Activity feed cleared');
      },
    },
    {
      id: 'view-health',
      type: 'action',
      title: 'System Health',
      subtitle: 'View connection and backend status',
      icon: Activity,
      keywords: ['health', 'status', 'system', 'backend'],
      action: () => toast.success('Opening System Health panel'),
    },
    {
      id: 'check-connection',
      type: 'action',
      title: 'Check Connection',
      subtitle: 'Test backend connectivity',
      icon: Wifi,
      keywords: ['connection', 'test', 'ping', 'api'],
      action: async () => {
        try {
          const health = await api.health();
          toast.success(`Backend connected: ${health.status}`);
        } catch (error) {
          toast.error('Backend not reachable');
        }
      },
    },
    {
      id: 'open-settings',
      type: 'action',
      title: 'Settings',
      subtitle: 'Open application settings',
      icon: Settings,
      keywords: ['settings', 'config', 'preferences'],
      action: () => toast.success('Opening settings'),
    },
    {
      id: 'copy-project-path',
      type: 'action',
      title: 'Copy Project Path',
      subtitle: 'Copy the current project path to clipboard',
      icon: Copy,
      keywords: ['copy', 'path', 'project'],
      action: () => {
        const path = useDashboardStore.getState().currentProject?.path || '';
        navigator.clipboard.writeText(path);
        toast.success('Project path copied');
      },
    },
  ], [modes, handleRunMode, resetModes, clearActivities]);

  // Search results
  const results = useMemo((): SearchResult[] => {
    const q = query.toLowerCase().trim();
    const allResults: SearchResult[] = [];

    // Show recent commands when no query
    if (!q && (category === 'all' || category === 'recent')) {
      const recentCommands = useDashboardStore.getState().commandHistory.slice(0, 5);
      recentCommands.forEach((cmd, i) => {
        allResults.push({
          id: `recent-${i}`,
          type: 'recent',
          title: cmd,
          subtitle: 'Recent command',
          icon: History,
          action: () => {
            // Re-run the command
            useDashboardStore.getState().addActivity({
              id: crypto.randomUUID(),
              type: 'user_command',
              timestamp: new Date().toISOString(),
              content: cmd,
            });
          },
        });
      });
    }

    // Show actions when no query or when searching
    if (category === 'all' || category === 'actions') {
      const matchingActions = q
        ? actions.filter(
            (a) =>
              a.title.toLowerCase().includes(q) ||
              a.subtitle.toLowerCase().includes(q) ||
              (a.keywords && a.keywords.some(k => k.includes(q)))
          )
        : actions.slice(0, 7);
      allResults.push(...matchingActions);
    }

    if (!q) return allResults;

    // Search activities
    if (category === 'all' || category === 'activities') {
      activities
        .filter((a) => a.content?.toLowerCase().includes(q) || a.type.toLowerCase().includes(q))
        .slice(0, 5)
        .forEach((a) => {
          allResults.push({
            id: a.id,
            type: 'activity',
            title: a.content?.slice(0, 60) || a.type,
            subtitle: `${a.type} ${a.modeId ? `• Mode ${a.modeId}` : ''}`,
            timestamp: a.timestamp,
            icon: a.type === 'user_command' ? MessageSquare : Terminal,
          });
        });
    }

    // Search artifacts
    if (category === 'all' || category === 'artifacts') {
      artifacts
        .filter(
          (a) =>
            a.name.toLowerCase().includes(q) ||
            a.type.toLowerCase().includes(q) ||
            a.id.toLowerCase().includes(q)
        )
        .slice(0, 5)
        .forEach((a) => {
          allResults.push({
            id: a.id,
            type: 'artifact',
            title: a.name,
            subtitle: `${a.type} • Mode ${a.modeId}`,
            timestamp: a.createdAt,
            icon: FileBox,
          });
        });
    }

    // Search modes
    if (category === 'all' || category === 'modes') {
      modes
        .filter(
          (m) =>
            m.name.toLowerCase().includes(q) ||
            m.id.toLowerCase().includes(q) ||
            m.description.toLowerCase().includes(q)
        )
        .slice(0, 5)
        .forEach((m) => {
          allResults.push({
            id: m.id,
            type: 'mode',
            title: `Mode ${m.id}: ${m.name}`,
            subtitle: m.description,
            icon: Layers,
          });
        });
    }

    return allResults;
  }, [query, category, activities, artifacts, modes, actions]);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results]);

  const handleSelect = (result: SearchResult) => {
    if (result.type === 'action' && result.action) {
      result.action();
    } else if (result.type === 'artifact') {
      const artifact = artifacts.find((a) => a.id === result.id);
      if (artifact) setSelectedArtifact(artifact as any);
    }
    setSearchOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setSearchOpen(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-bg-secondary border border-border rounded-xl shadow-2xl overflow-hidden animate-fade-in">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
          <Command className="w-5 h-5 text-text-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search or type a command..."
            className="flex-1 bg-transparent text-text-primary placeholder:text-text-muted focus:outline-none"
          />
          <kbd className="hidden sm:block text-xs text-text-muted bg-bg-primary px-2 py-1 rounded">
            ⌘K
          </kbd>
          <button
            onClick={() => setSearchOpen(false)}
            className="p-1 hover:bg-bg-hover rounded"
          >
            <X className="w-5 h-5 text-text-muted" />
          </button>
        </div>

        {/* Categories */}
        <div className="flex gap-1 px-4 py-2 border-b border-border-subtle overflow-x-auto">
          <CategoryTab
            active={category === 'all'}
            onClick={() => setCategory('all')}
            label="All"
          />
          <CategoryTab
            active={category === 'actions'}
            onClick={() => setCategory('actions')}
            label="Actions"
          />
          <CategoryTab
            active={category === 'recent'}
            onClick={() => setCategory('recent')}
            label="Recent"
          />
          <CategoryTab
            active={category === 'artifacts'}
            onClick={() => setCategory('artifacts')}
            label="Artifacts"
          />
          <CategoryTab
            active={category === 'modes'}
            onClick={() => setCategory('modes')}
            label="Modes"
          />
          <CategoryTab
            active={category === 'activities'}
            onClick={() => setCategory('activities')}
            label="Feed"
          />
        </div>

        {/* Results */}
        <div className="max-h-96 overflow-y-auto">
          {results.length === 0 ? (
            <div className="p-8 text-center text-text-muted">
              <p>No results found for "{query}"</p>
            </div>
          ) : (
            <div className="py-2">
              {results.map((result, index) => (
                <SearchResultItem
                  key={result.id}
                  result={result}
                  selected={index === selectedIndex}
                  onClick={() => handleSelect(result)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-border-subtle flex items-center gap-4 text-xs text-text-muted">
          <span>
            <kbd className="bg-bg-primary px-1.5 py-0.5 rounded">↑↓</kbd> Navigate
          </span>
          <span>
            <kbd className="bg-bg-primary px-1.5 py-0.5 rounded">↵</kbd> Select
          </span>
          <span>
            <kbd className="bg-bg-primary px-1.5 py-0.5 rounded">esc</kbd> Close
          </span>
        </div>
      </div>
    </div>
  );
}

function CategoryTab({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'px-3 py-1 rounded-md text-sm transition-colors',
        active
          ? 'bg-accent-blue/20 text-accent-blue'
          : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
      )}
    >
      {label}
    </button>
  );
}

function SearchResultItem({
  result,
  selected,
  onClick,
}: {
  result: SearchResult;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = result.icon;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full flex items-center gap-3 px-4 py-2 text-left transition-colors',
        selected ? 'bg-bg-hover' : 'hover:bg-bg-tertiary'
      )}
    >
      <div className="w-8 h-8 rounded-lg bg-bg-tertiary flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-text-secondary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{result.title}</div>
        <div className="text-xs text-text-muted truncate">{result.subtitle}</div>
      </div>
      {result.timestamp && (
        <div className="flex items-center gap-1 text-2xs text-text-muted">
          <Clock className="w-3 h-3" />
          {formatDistanceToNow(new Date(result.timestamp), { addSuffix: true })}
        </div>
      )}
      {selected && <ArrowRight className="w-4 h-4 text-text-muted" />}
    </button>
  );
}

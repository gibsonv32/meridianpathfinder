import { useState, useCallback } from 'react';
import {
  ChevronRight,
  Play,
  Pause,
  Square,
  MoreHorizontal,
  Terminal,
  Clock,
  CheckCircle,
  AlertCircle,
  Cpu,
  Database,
  Network,
} from 'lucide-react';
import clsx from 'clsx';
import { useDashboardStore } from '../store';
import { api } from '../api/client';
import toast from 'react-hot-toast';

// Realistic mode data with proper states and timing
const MODE_CONFIGS = [
  { id: '0', name: 'Data Discovery', desc: 'Exploratory analysis and profiling', duration: '~3m', status: 'completed', progress: 100, lastRun: '2h ago' },
  { id: '0.5', name: 'Opportunity Mapping', desc: 'Business impact assessment', duration: '~2m', status: 'completed', progress: 100, lastRun: '1h ago' },
  { id: '1', name: 'Decision Intelligence', desc: 'Strategic decision framework', duration: '~4m', status: 'running', progress: 67, lastRun: 'now' },
  { id: '2', name: 'Feasibility Check', desc: 'Technical and business viability', duration: '~3m', status: 'queued', progress: 0, lastRun: 'never' },
  { id: '3', name: 'Model Architecture', desc: 'ML strategy and feature design', duration: '~5m', status: 'queued', progress: 0, lastRun: 'never' },
  { id: '4', name: 'Business Case', desc: 'ROI analysis and justification', duration: '~3m', status: 'queued', progress: 0, lastRun: 'never' },
  { id: '5', name: 'Code Generation', desc: 'Production-ready implementation', duration: '~8m', status: 'queued', progress: 0, lastRun: 'never' },
  { id: '6', name: 'Deployment', desc: 'Infrastructure and monitoring', duration: '~6m', status: 'queued', progress: 0, lastRun: 'never' },
  { id: '7', name: 'Handoff Package', desc: 'Documentation and transfer', duration: '~2m', status: 'queued', progress: 0, lastRun: 'never' },
];

const SYSTEM_METRICS = {
  cpu: 34,
  memory: 68,
  disk: 23,
  network: 12,
  apiLatency: '47ms',
  activeConnections: 3,
  queueDepth: 2,
};

export function MeridianPro() {
  const [activeMode] = useState<string | null>('1');
  const [selectedModes, setSelectedModes] = useState<Set<string>>(new Set());
  const [commandInput, setCommandInput] = useState('');
  const [systemExpanded, setSystemExpanded] = useState(false);
  
  const { activities, addActivity, addToCommandHistory } = useDashboardStore();

  // Get current running mode
  const runningMode = MODE_CONFIGS.find(m => m.status === 'running');
  const completedModes = MODE_CONFIGS.filter(m => m.status === 'completed');
  const pipelineProgress = (completedModes.length / MODE_CONFIGS.length) * 100;

  const handleModeAction = useCallback(async (modeId: string, action: 'run' | 'pause' | 'stop') => {
    try {
      switch (action) {
        case 'run':
          await api.runMode(modeId);
          toast.success(`Started Mode ${modeId}`);
          break;
        case 'pause':
          toast.success(`Paused Mode ${modeId}`);
          break;
        case 'stop':
          toast.success(`Stopped Mode ${modeId}`);
          break;
      }
      
      addActivity({
        id: crypto.randomUUID(),
        type: 'mode_started',
        timestamp: new Date().toISOString(),
        modeId: modeId as any,
        content: `Mode ${modeId} ${action}`,
      });
    } catch (error) {
      toast.error(`Failed to ${action} mode: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [addActivity]);

  const handleCommand = useCallback(async (command: string) => {
    if (!command.trim()) return;
    
    addToCommandHistory(command);
    addActivity({
      id: crypto.randomUUID(),
      type: 'user_command',
      timestamp: new Date().toISOString(),
      content: command,
    });

    if (command.startsWith('run ')) {
      const modeId = command.split(' ')[1];
      handleModeAction(modeId, 'run');
    } else if (command === 'status') {
      addActivity({
        id: crypto.randomUUID(),
        type: 'system_notice',
        timestamp: new Date().toISOString(),
        content: `Pipeline: ${completedModes.length}/${MODE_CONFIGS.length} complete • ${runningMode ? 'Running' : 'Idle'}`,
        severity: 'info',
      });
    }

    setCommandInput('');
  }, [addToCommandHistory, addActivity, completedModes.length, runningMode, handleModeAction]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Header - Intentionally asymmetric */}
      <header className="bg-white border-b border-slate-200 px-8 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-3">
              {/* Distinctive logo - not just a circle */}
              <div className="w-8 h-8 bg-slate-900 rounded-sm flex items-center justify-center">
                <div className="w-3 h-3 bg-white rounded-full"></div>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">MERIDIAN</h1>
                <p className="text-sm text-slate-500 -mt-1">Intelligence Platform</p>
              </div>
            </div>
            
            {/* Pipeline status - visual anchor */}
            <div className="hidden md:flex items-center space-x-3 pl-6 border-l border-slate-200">
              <div className="text-sm text-slate-600">
                {completedModes.length}/{MODE_CONFIGS.length} Complete
              </div>
              <div className="w-24 h-1 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-slate-900 transition-all duration-500"
                  style={{ width: `${pipelineProgress}%` }}
                />
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <SystemStatus expanded={systemExpanded} onToggle={() => setSystemExpanded(!systemExpanded)} />
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Main Content - Breaking the grid */}
        <main className="flex-1 p-8">
          {/* Current Activity - Hero without the clichés */}
          {runningMode && (
            <div className="mb-8 p-6 bg-white rounded-lg border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <h2 className="text-lg font-medium">Currently Running</h2>
                </div>
                <div className="flex items-center space-x-2">
                  <button 
                    onClick={() => handleModeAction(runningMode.id, 'pause')}
                    className="p-1 hover:bg-slate-100 rounded"
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => handleModeAction(runningMode.id, 'stop')}
                    className="p-1 hover:bg-slate-100 rounded"
                  >
                    <Square className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                  <h3 className="font-medium mb-1">Mode {runningMode.id}: {runningMode.name}</h3>
                  <p className="text-slate-600 text-sm mb-4">{runningMode.desc}</p>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Progress</span>
                      <span>{runningMode.progress}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${runningMode.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="text-sm">
                    <div className="text-slate-500">Estimated completion</div>
                    <div className="font-medium">~2 minutes</div>
                  </div>
                  <div className="text-sm">
                    <div className="text-slate-500">Started</div>
                    <div className="font-medium">3 minutes ago</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Modes Grid - Intentionally not uniform */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-medium">Pipeline Modes</h2>
              <div className="flex items-center space-x-2">
                {selectedModes.size > 0 && (
                  <button className="px-3 py-1 text-sm bg-slate-900 text-white rounded-md hover:bg-slate-800">
                    Run Selected ({selectedModes.size})
                  </button>
                )}
                <button className="p-1 hover:bg-slate-100 rounded">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {MODE_CONFIGS.map((mode, index) => (
                <ModeCard
                  key={mode.id}
                  mode={mode}
                  isActive={activeMode === mode.id}
                  isSelected={selectedModes.has(mode.id)}
                  onSelect={() => {
                    const newSelected = new Set(selectedModes);
                    if (newSelected.has(mode.id)) {
                      newSelected.delete(mode.id);
                    } else {
                      newSelected.add(mode.id);
                    }
                    setSelectedModes(newSelected);
                  }}
                  onAction={(action) => handleModeAction(mode.id, action)}
                  className={index === 0 ? 'md:col-span-2' : ''} // Break the grid
                />
              ))}
            </div>
          </div>

          {/* Command Interface - Functional, not decorative */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="flex items-center space-x-3">
              <Terminal className="w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCommand(commandInput)}
                placeholder="Enter command (run 1, status, help...)"
                className="flex-1 text-sm bg-transparent border-none outline-none"
              />
              <button
                onClick={() => handleCommand(commandInput)}
                className="p-1 hover:bg-slate-100 rounded"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </main>

        {/* Activity Sidebar - Information dense */}
        <aside className="w-80 bg-white border-l border-slate-200 p-6">
          <h3 className="font-medium mb-4">Recent Activity</h3>
          <div className="space-y-4">
            {activities.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                No activity yet. Run a mode to get started.
              </div>
            ) : (
              activities.slice(-8).reverse().map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

// Supporting Components

function ModeCard({ 
  mode, 
  isActive, 
  isSelected, 
  onSelect, 
  onAction, 
  className = '' 
}: {
  mode: typeof MODE_CONFIGS[0];
  isActive: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onAction: (action: 'run' | 'pause' | 'stop') => void;
  className?: string;
}) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'running': return 'text-blue-600';
      case 'failed': return 'text-red-600';
      default: return 'text-slate-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return CheckCircle;
      case 'running': return Clock;
      case 'failed': return AlertCircle;
      default: return Clock;
    }
  };

  const StatusIcon = getStatusIcon(mode.status);

  return (
    <div className={clsx(
      'p-4 border border-slate-200 rounded-lg hover:shadow-sm transition-shadow',
      isActive && 'ring-1 ring-slate-900',
      isSelected && 'bg-slate-50',
      className
    )}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="rounded border-slate-300"
          />
          <div className="text-xs text-slate-500 font-mono">MODE {mode.id}</div>
        </div>
        <StatusIcon className={clsx('w-4 h-4', getStatusColor(mode.status))} />
      </div>

      <h4 className="font-medium mb-1">{mode.name}</h4>
      <p className="text-sm text-slate-600 mb-4">{mode.desc}</p>

      {mode.status === 'running' && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Progress</span>
            <span>{mode.progress}%</span>
          </div>
          <div className="w-full h-1 bg-slate-100 rounded-full">
            <div 
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${mode.progress}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="text-xs text-slate-500">
          {mode.duration} • Last: {mode.lastRun}
        </div>
        <div className="flex items-center space-x-1">
          {mode.status === 'running' ? (
            <>
              <button 
                onClick={() => onAction('pause')}
                className="p-1 hover:bg-slate-100 rounded"
              >
                <Pause className="w-3 h-3" />
              </button>
              <button 
                onClick={() => onAction('stop')}
                className="p-1 hover:bg-slate-100 rounded"
              >
                <Square className="w-3 h-3" />
              </button>
            </>
          ) : (
            <button 
              onClick={() => onAction('run')}
              className="p-1 hover:bg-slate-100 rounded"
            >
              <Play className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function SystemStatus({ expanded, onToggle }: { expanded: boolean; onToggle: () => void }) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="flex items-center space-x-2 px-3 py-1 text-sm border border-slate-200 rounded-md hover:bg-slate-50"
      >
        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
        <span>System</span>
      </button>

      {expanded && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-white border border-slate-200 rounded-lg shadow-lg p-4 z-50">
          <h4 className="font-medium mb-3">System Health</h4>
          <div className="space-y-3">
            <MetricRow icon={Cpu} label="CPU" value={`${SYSTEM_METRICS.cpu}%`} />
            <MetricRow icon={Database} label="Memory" value={`${SYSTEM_METRICS.memory}%`} />
            <MetricRow icon={Network} label="API Latency" value={SYSTEM_METRICS.apiLatency} />
          </div>
        </div>
      )}
    </div>
  );
}

function MetricRow({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center space-x-2">
        <Icon className="w-3 h-3 text-slate-500" />
        <span>{label}</span>
      </div>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function ActivityItem({ activity }: { activity: any }) {
  return (
    <div className="flex items-start space-x-3 text-sm">
      <div className="w-1 h-1 bg-slate-400 rounded-full mt-2 flex-shrink-0"></div>
      <div className="flex-1">
        <p className="text-slate-900">{activity.content}</p>
        <p className="text-xs text-slate-500">
          {new Date(activity.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
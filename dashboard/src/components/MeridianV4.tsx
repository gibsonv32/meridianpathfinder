import { useState, useEffect, useRef } from 'react';
import {
  Activity,
  ChevronRight,
  Play,
  RotateCcw,
  Upload,
  Zap,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  PauseIcon as Pulse,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { useDashboardStore } from '../store';
import { SearchModal } from './SearchModal';
import { RunQueue } from './RunQueue';
import { api } from '../api/client';
import toast from 'react-hot-toast';

// Mode definitions to match the original design
const MODE_DEFINITIONS = {
  '0': { name: 'Data Analysis', description: 'Comprehensive exploratory data analysis', section: 'implementation' },
  '0.5': { name: 'Opportunity Discovery', description: 'Discover opportunities in your data', section: 'implementation' },
  '1': { name: 'Decision Intelligence', description: 'Build decision intelligence profile', section: 'implementation' },
  '2': { name: 'Feasibility Assessment', description: 'Assess feasibility of your approach', section: 'implementation' },
  '3': { name: 'Model Strategy', description: 'Define model strategy and features', section: 'implementation' },
  '4': { name: 'Business Case', description: 'Generate business case scorecard', section: 'implementation' },
  '5': { name: 'Production Code Generation', description: 'Generate high-quality, production-ready code', section: 'implementation' },
  '6': { name: 'Automated Execution', description: 'Deploy and execute generated solutions', section: 'implementation' },
  '6.5': { name: 'Results Interpretation', description: 'Analyze outputs and generate reports', section: 'implementation' },
  '7': { name: 'Delivery & Handoff', description: 'Package artifacts and documentation for stakeholders', section: 'delivery' },
} as const;

const QUICK_ACTIONS = [
  { label: '/run discovery', command: '/run mode 0.5' },
  { label: '/run implementation', command: '/run mode 5' },
  { label: '/status', command: '/status' },
];

export function MeridianV4() {
  const [commandInput, setCommandInput] = useState('');
  const [showRunQueue, setShowRunQueue] = useState(false);
  const commandRef = useRef<HTMLInputElement>(null);
  
  const {
    modes,
    activities,
    searchOpen,
    setSearchOpen,
    addActivity,
    addToCommandHistory,
  } = useDashboardStore();

  // Calculate pipeline progress
  const completedModes = modes.filter(m => m.status === 'completed').length;
  const totalModes = modes.length;
  const progressPercentage = totalModes > 0 ? (completedModes / totalModes) * 100 : 0;

  // Group modes by section
  const implementationModes = modes.filter(m => {
    const def = MODE_DEFINITIONS[m.id as keyof typeof MODE_DEFINITIONS];
    return def?.section === 'implementation';
  });
  
  const deliveryModes = modes.filter(m => {
    const def = MODE_DEFINITIONS[m.id as keyof typeof MODE_DEFINITIONS];
    return def?.section === 'delivery';
  });

  // Handle command submission
  const handleCommandSubmit = async (command: string) => {
    if (!command.trim()) return;

    addToCommandHistory(command);
    addActivity({
      id: crypto.randomUUID(),
      type: 'user_command',
      timestamp: new Date().toISOString(),
      content: command,
    });

    // Handle slash commands
    if (command.startsWith('/run mode ')) {
      const modeId = command.replace('/run mode ', '').trim();
      try {
        await api.runMode(modeId);
        toast.success(`Starting Mode ${modeId}`);
      } catch (error) {
        toast.error(`Failed to start mode: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } else if (command === '/status') {
      addActivity({
        id: crypto.randomUUID(),
        type: 'system_notice',
        timestamp: new Date().toISOString(),
        content: `Pipeline Status: ${completedModes}/${totalModes} modes completed`,
        severity: 'info',
      });
    }

    setCommandInput('');
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setSearchOpen]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-gray-700/50">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">M</span>
          </div>
          <div>
            <h1 className="text-xl font-bold">MERIDIAN Intelligence Platform</h1>
            <p className="text-sm text-gray-400">Dual-Model AI System</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <StatusIndicator label="GPT-03S" status="online" />
          <StatusIndicator label="Claude" status="online" />
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Panel - Pipeline & Controls */}
        <div className="w-80 p-6 border-r border-gray-700/50 space-y-8">
          {/* Pipeline Progress */}
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Pipeline</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{completedModes}/{totalModes} Complete</span>
                <span className="text-gray-400">{Math.round(progressPercentage)}%</span>
              </div>
              <div className="flex gap-1">
                {Array.from({ length: totalModes }).map((_, i) => (
                  <div
                    key={i}
                    className={clsx(
                      'h-2 rounded-full flex-1',
                      i < completedModes 
                        ? 'bg-green-500' 
                        : i === completedModes 
                        ? 'bg-blue-500' 
                        : 'bg-gray-700'
                    )}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Run Controls */}
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Run Controls</h2>
            <div className="space-y-3">
              <ActionButton
                icon={Zap}
                label="Run Analysis"
                variant="primary"
                onClick={() => handleCommandSubmit('/run mode 0')}
              />
              <ActionButton
                icon={Play}
                label="Generate Code"
                variant="secondary"
                onClick={() => handleCommandSubmit('/run mode 5')}
              />
              <ActionButton
                icon={RotateCcw}
                label="Reset Pipeline"
                variant="ghost"
                onClick={() => {
                  useDashboardStore.getState().resetModes();
                  toast.success('Pipeline reset');
                }}
              />
            </div>
          </div>

          {/* Documents */}
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Documents</h2>
            <DocumentDropZone />
          </div>

          {/* Session Info */}
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Session</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Mode:</span>
                <span>Dual-Model</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Load:</span>
                <span>42%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Uptime:</span>
                <span>2h 34m</span>
              </div>
            </div>
          </div>
        </div>

        {/* Center Panel - Implementation & Delivery */}
        <div className="flex-1 p-6 space-y-8 overflow-y-auto">
          {/* Implementation Section */}
          <div>
            <h2 className="text-lg font-semibold mb-6">IMPLEMENTATION</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {implementationModes.map((mode) => {
                const def = MODE_DEFINITIONS[mode.id as keyof typeof MODE_DEFINITIONS];
                return (
                  <ModeCard
                    key={mode.id}
                    mode={mode}
                    definition={def}
                    onRun={() => handleCommandSubmit(`/run mode ${mode.id}`)}
                  />
                );
              })}
            </div>
          </div>

          {/* Delivery Section */}
          <div>
            <h2 className="text-lg font-semibold mb-6">DELIVERY</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {deliveryModes.map((mode) => {
                const def = MODE_DEFINITIONS[mode.id as keyof typeof MODE_DEFINITIONS];
                return (
                  <ModeCard
                    key={mode.id}
                    mode={mode}
                    definition={def}
                    onRun={() => handleCommandSubmit(`/run mode ${mode.id}`)}
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Panel - Live Activity */}
        <div className="w-80 border-l border-gray-700/50">
          <div className="p-6">
            <h2 className="text-lg font-semibold mb-6">LIVE ACTIVITY</h2>
            <div className="space-y-4">
              {activities.length === 0 ? (
                <div className="text-center py-12">
                  <Pulse className="w-12 h-12 mx-auto mb-3 text-gray-500" />
                  <p className="text-gray-400 mb-2">No activity yet</p>
                  <p className="text-sm text-gray-500">Run a mode to see live output</p>
                </div>
              ) : (
                activities.slice(-10).reverse().map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Command Input */}
      <div className="border-t border-gray-700/50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1 relative">
              <input
                ref={commandRef}
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCommandSubmit(commandInput);
                  }
                }}
                placeholder="Type a MERIDIAN command or describe what you want to analyze..."
                className="w-full bg-gray-800/50 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder:text-gray-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
              />
              <ChevronRight className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400">Quick:</span>
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.command}
                onClick={() => handleCommandSubmit(action.command)}
                className="text-sm text-amber-400 hover:text-amber-300 transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Floating Action Button */}
      <div className="fixed bottom-8 right-8 z-20">
        <button
          onClick={() => setShowRunQueue(true)}
          className="w-14 h-14 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-105"
        >
          <Activity className="w-6 h-6 text-white" />
        </button>
      </div>

      {/* Modals and Overlays */}
      {searchOpen && <SearchModal />}
      {showRunQueue && (
        <>
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30" onClick={() => setShowRunQueue(false)} />
          <RunQueue onClose={() => setShowRunQueue(false)} className="fixed inset-y-0 right-0 w-96 z-40" />
        </>
      )}
    </div>
  );
}

// Helper Components

function StatusIndicator({ label, status }: { label: string; status: 'online' | 'offline' }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded-lg border border-gray-600">
      <div className={clsx(
        'w-2 h-2 rounded-full',
        status === 'online' ? 'bg-green-400' : 'bg-red-400'
      )} />
      <span className="text-sm font-medium text-gray-300">{label}</span>
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
  variant,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  variant: 'primary' | 'secondary' | 'ghost';
  onClick: () => void;
}) {
  const baseClasses = "flex items-center gap-3 w-full px-4 py-3 rounded-lg font-medium transition-colors";
  const variantClasses = {
    primary: "bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg",
    secondary: "bg-blue-600 hover:bg-blue-700 text-white",
    ghost: "border border-gray-600 hover:bg-gray-700 text-gray-300",
  };

  return (
    <button onClick={onClick} className={clsx(baseClasses, variantClasses[variant])}>
      <Icon className="w-5 h-5" />
      <span>{label}</span>
    </button>
  );
}

function ModeCard({
  mode,
  definition,
  onRun,
}: {
  mode: any;
  definition?: { name: string; description: string };
  onRun: () => void;
}) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed':
        return { color: 'text-green-400', bg: 'bg-green-900/30', icon: CheckCircle2 };
      case 'running':
        return { color: 'text-blue-400', bg: 'bg-blue-900/30', icon: Loader2 };
      case 'failed':
        return { color: 'text-red-400', bg: 'bg-red-900/30', icon: AlertCircle };
      default:
        return { color: 'text-gray-400', bg: 'bg-gray-800/50', icon: Clock };
    }
  };

  const config = getStatusConfig(mode.status);
  const Icon = config.icon;
  const isRunning = mode.status === 'running';
  const progress = isRunning ? 45 : mode.status === 'completed' ? 100 : 0; // Mock progress

  return (
    <div className={clsx(
      'relative p-5 rounded-lg border transition-all',
      config.bg,
      mode.status === 'completed' 
        ? 'border-green-600/30' 
        : mode.status === 'running' 
        ? 'border-blue-600/30' 
        : 'border-gray-700 hover:border-gray-600'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-gray-700 flex items-center justify-center">
            <span className="text-xs font-bold">M</span>
          </div>
          <div>
            <h3 className="font-semibold text-sm">Mode {mode.id}</h3>
            <div className="flex items-center gap-2 mt-1">
              {mode.status === 'running' && (
                <span className="text-xs px-2 py-0.5 rounded bg-blue-600 text-blue-100">
                  Claude
                </span>
              )}
              {mode.status === 'completed' && mode.id === '6.5' && (
                <span className="text-xs px-2 py-0.5 rounded bg-orange-600 text-orange-100">
                  hybrid
                </span>
              )}
            </div>
          </div>
        </div>
        <Icon className={clsx('w-5 h-5', config.color, isRunning && 'animate-spin')} />
      </div>

      {/* Content */}
      <div className="mb-4">
        <h4 className="font-medium mb-1">{definition?.name || mode.name}</h4>
        <p className="text-xs text-gray-400 leading-relaxed">
          {definition?.description || mode.description}
        </p>
      </div>

      {/* Progress and Status */}
      {isRunning && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-blue-400">Running...</span>
            <span className="text-gray-400">{progress}%</span>
          </div>
          <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">
          {mode.status === 'running' ? 'Last: now' : 
           mode.status === 'completed' ? 'Last: 2h ago' : 
           'Never run'}
        </span>
        {mode.status !== 'running' && (
          <button
            onClick={onRun}
            className="text-amber-400 hover:text-amber-300 font-medium"
          >
            Run
          </button>
        )}
      </div>
    </div>
  );
}

function ActivityItem({ activity }: { activity: any }) {
  const isRecent = new Date().getTime() - new Date(activity.timestamp).getTime() < 30000;
  
  return (
    <div className={clsx(
      'p-3 rounded-lg text-sm',
      isRecent ? 'bg-blue-900/20 border border-blue-600/30' : 'bg-gray-800/30'
    )}>
      <div className="flex items-start gap-3">
        <div className="w-6 h-6 rounded bg-gray-700 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Activity className="w-3 h-3" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="truncate">{activity.content || activity.type}</p>
          <p className="text-xs text-gray-500 mt-1">
            {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>
    </div>
  );
}

function DocumentDropZone() {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
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
      toast.success(`Uploading ${files.length} file${files.length > 1 ? 's' : ''}...`);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      toast.success(`Uploading ${files.length} file${files.length > 1 ? 's' : ''}...`);
    }
    e.target.value = '';
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={clsx(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
        isDragOver 
          ? 'border-amber-500 bg-amber-500/10' 
          : 'border-gray-600 hover:border-gray-500 text-gray-400'
      )}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.json,.yaml"
        onChange={handleFileSelect}
      />
      <Upload className="w-6 h-6 mx-auto mb-2" />
      <p className="text-sm">{isDragOver ? 'Drop files here' : 'Drop files or click'}</p>
    </div>
  );
}
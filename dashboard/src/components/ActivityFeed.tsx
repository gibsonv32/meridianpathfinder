import { useRef, useEffect, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Maximize2,
  Download,
  Pin,
  PinOff,
  MessageSquare,
  Terminal,
  FileBox,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { useDashboardStore } from '../store';
import type { ActivityItem, ToolExecution, ToolStatus } from '../types';
import toast from 'react-hot-toast';

export function ActivityFeed() {
  const activities = useDashboardStore((s) => s.activities);
  const feedRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new activities arrive
  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [activities, autoScroll]);

  // Detect manual scrolling
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop } = e.currentTarget;
    setAutoScroll(scrollTop < 50);
  };

  if (activities.length === 0) {
    return <EmptyState />;
  }

  return (
    <div
      ref={feedRef}
      onScroll={handleScroll}
      className="h-full overflow-y-auto px-6 py-4 space-y-3"
    >
      {activities.map((activity, index) => (
        <ActivityItemCard
          key={activity.id}
          activity={activity}
          isFirst={index === 0}
        />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-blue/20 to-accent-purple/20 flex items-center justify-center">
          <Sparkles className="w-8 h-8 text-accent-blue" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Ready to run</h2>
        <p className="text-text-secondary text-sm mb-6">
          Start by running a mode or typing a command below. 
          Your activity will appear here as a stream of messages.
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          <QuickAction label="Run Mode 0" command="/run mode 0" />
          <QuickAction label="Status" command="/status" />
          <QuickAction label="Help" command="/help" />
        </div>
      </div>
    </div>
  );
}

function QuickAction({ label, command }: { label: string; command: string }) {
  const addActivity = useDashboardStore((s) => s.addActivity);

  const handleClick = () => {
    addActivity({
      id: crypto.randomUUID(),
      type: 'user_command',
      timestamp: new Date().toISOString(),
      content: command,
    });
  };

  return (
    <button
      onClick={handleClick}
      className="px-3 py-1.5 rounded-md bg-bg-tertiary text-text-secondary hover:text-text-primary hover:bg-bg-hover border border-border-subtle text-sm transition-colors"
    >
      {label}
    </button>
  );
}

function ActivityItemCard({
  activity,
  isFirst,
}: {
  activity: ActivityItem;
  isFirst: boolean;
}) {
  const toggleActivityPin = useDashboardStore((s) => s.toggleActivityPin);

  const renderContent = () => {
    switch (activity.type) {
      case 'user_command':
        return <UserCommandCard content={activity.content || ''} />;
      case 'tool_execution':
        return activity.tool ? <ToolExecutionCard tool={activity.tool} /> : null;
      case 'mode_started':
      case 'mode_running':
      case 'mode_completed':
      case 'mode_failed':
        return <ModeStatusCard activity={activity} />;
      case 'artifact_created':
        return activity.artifact ? <ArtifactCreatedCard artifact={activity.artifact} /> : null;
      case 'system_notice':
        return <SystemNoticeCard activity={activity} />;
      case 'llm_response':
        return <LLMResponseCard content={activity.content || ''} />;
      default:
        return <GenericCard content={activity.content || activity.type} />;
    }
  };

  return (
    <div
      className={clsx(
        'group relative animate-fade-in',
        isFirst && 'animate-slide-up'
      )}
    >
      {/* Pin button (on hover) */}
      <button
        onClick={() => toggleActivityPin(activity.id)}
        className={clsx(
          'absolute -left-8 top-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity',
          activity.isPinned
            ? 'text-accent-yellow'
            : 'text-text-muted hover:text-text-secondary'
        )}
      >
        {activity.isPinned ? (
          <PinOff className="w-4 h-4" />
        ) : (
          <Pin className="w-4 h-4" />
        )}
      </button>

      {/* Timestamp */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-2xs text-text-muted">
          {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
        </span>
        {activity.modeId && (
          <span className="text-2xs text-text-muted bg-bg-tertiary px-1.5 py-0.5 rounded">
            Mode {activity.modeId}
          </span>
        )}
        {activity.isPinned && (
          <Pin className="w-3 h-3 text-accent-yellow" />
        )}
      </div>

      {/* Content */}
      {renderContent()}

      {/* Annotation */}
      {activity.annotation && (
        <div className="mt-2 pl-3 border-l-2 border-accent-yellow/50">
          <p className="text-sm text-text-secondary italic">{activity.annotation}</p>
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Activity Type Cards
// -----------------------------------------------------------------------------

function UserCommandCard({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 rounded-full bg-accent-blue/20 flex items-center justify-center flex-shrink-0 mt-0.5">
        <MessageSquare className="w-3.5 h-3.5 text-accent-blue" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-mono text-sm bg-bg-tertiary rounded-lg px-3 py-2 border border-border-subtle">
          {content}
        </div>
      </div>
    </div>
  );
}

function ToolExecutionCard({ tool }: { tool: ToolExecution }) {
  const [expanded, setExpanded] = useState(false);

  const copyOutput = () => {
    if (tool.output) {
      navigator.clipboard.writeText(tool.output);
      toast.success('Copied to clipboard');
    }
  };

  const StatusIcon = getToolStatusIcon(tool.status);
  const statusColor = getToolStatusColor(tool.status);

  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 rounded-full bg-bg-tertiary flex items-center justify-center flex-shrink-0 mt-0.5">
        <Terminal className="w-3.5 h-3.5 text-text-secondary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="tool-output">
          {/* Header */}
          <div
            className="tool-output-header cursor-pointer"
            onClick={() => setExpanded(!expanded)}
          >
            <div className="flex items-center gap-2 min-w-0">
              <button className="p-0.5">
                {expanded ? (
                  <ChevronDown className="w-4 h-4 text-text-tertiary" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-text-tertiary" />
                )}
              </button>
              <StatusIcon className={clsx('w-4 h-4', statusColor)} />
              <span className="text-sm truncate">{tool.summary}</span>
              <span className={clsx('status-pill', `status-pill-${tool.status}`)}>
                {tool.status}
              </span>
            </div>
            <div className="flex items-center gap-2 text-text-muted">
              {tool.runtime && (
                <span className="text-2xs">{(tool.runtime / 1000).toFixed(2)}s</span>
              )}
              {tool.exitCode !== undefined && (
                <span className="text-2xs">exit {tool.exitCode}</span>
              )}
            </div>
          </div>

          {/* Body (collapsible) */}
          {expanded && tool.output && (
            <div className="relative">
              <div className="tool-output-body">
                <pre className="text-xs">{tool.output}</pre>
              </div>
              {/* Actions */}
              <div className="absolute top-2 right-2 flex gap-1">
                <button
                  onClick={copyOutput}
                  className="btn btn-icon btn-ghost text-text-muted hover:text-text-primary"
                  title="Copy"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
                <button
                  className="btn btn-icon btn-ghost text-text-muted hover:text-text-primary"
                  title="Full screen"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
                <button
                  className="btn btn-icon btn-ghost text-text-muted hover:text-text-primary"
                  title="Download"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ModeStatusCard({ activity }: { activity: ActivityItem }) {
  const isRunning = activity.type === 'mode_running' || activity.type === 'mode_started';
  const isSuccess = activity.type === 'mode_completed';
  const isError = activity.type === 'mode_failed';

  const Icon = isRunning ? Loader2 : isSuccess ? CheckCircle2 : isError ? XCircle : AlertCircle;
  const iconColor = isRunning
    ? 'text-status-running'
    : isSuccess
    ? 'text-status-success'
    : isError
    ? 'text-status-error'
    : 'text-text-secondary';

  const bgColor = isRunning
    ? 'bg-status-running/10 border-status-running/30'
    : isSuccess
    ? 'bg-status-success/10 border-status-success/30'
    : isError
    ? 'bg-status-error/10 border-status-error/30'
    : 'bg-bg-tertiary border-border-subtle';

  const message =
    activity.type === 'mode_started'
      ? `Mode ${activity.modeId} started`
      : activity.type === 'mode_running'
      ? `Mode ${activity.modeId} running...`
      : activity.type === 'mode_completed'
      ? `Mode ${activity.modeId} completed`
      : `Mode ${activity.modeId} failed`;

  return (
    <div className={clsx('flex items-center gap-3 px-4 py-3 rounded-lg border', bgColor)}>
      <Icon className={clsx('w-5 h-5', iconColor, isRunning && 'animate-spin')} />
      <span className="font-medium">{message}</span>
      {activity.content && (
        <span className="text-text-secondary text-sm">{activity.content}</span>
      )}
    </div>
  );
}

function ArtifactCreatedCard({ artifact }: { artifact: any }) {
  const setSelectedArtifact = useDashboardStore((s) => s.setSelectedArtifact);

  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 rounded-full bg-accent-green/20 flex items-center justify-center flex-shrink-0 mt-0.5">
        <FileBox className="w-3.5 h-3.5 text-accent-green" />
      </div>
      <div className="flex-1">
        <div className="text-sm">
          <span className="text-text-secondary">Artifact created: </span>
          <button
            onClick={() => setSelectedArtifact(artifact)}
            className="font-medium text-accent-blue hover:underline"
          >
            {artifact.name}
          </button>
        </div>
        <div className="text-2xs text-text-muted mt-0.5">
          {artifact.type} • {artifact.id.slice(0, 8)}...
        </div>
      </div>
    </div>
  );
}

function SystemNoticeCard({ activity }: { activity: ActivityItem }) {
  const bgColor =
    activity.severity === 'error'
      ? 'bg-status-error/10 border-status-error/30 text-status-error'
      : activity.severity === 'warning'
      ? 'bg-status-warning/10 border-status-warning/30 text-status-warning'
      : 'bg-bg-tertiary border-border-subtle text-text-secondary';

  return (
    <div className={clsx('text-sm px-4 py-2 rounded-lg border', bgColor)}>
      {activity.content}
    </div>
  );
}

function LLMResponseCard({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 rounded-full bg-accent-purple/20 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Sparkles className="w-3.5 h-3.5 text-accent-purple" />
      </div>
      <div className="flex-1 prose prose-invert prose-sm max-w-none">
        <div className="text-sm text-text-primary whitespace-pre-wrap">{content}</div>
      </div>
    </div>
  );
}

function GenericCard({ content }: { content: string }) {
  return (
    <div className="text-sm text-text-secondary bg-bg-tertiary rounded-lg px-4 py-2">
      {content}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function getToolStatusIcon(status: ToolStatus) {
  switch (status) {
    case 'running':
      return Loader2;
    case 'success':
      return CheckCircle2;
    case 'error':
      return XCircle;
  }
}

function getToolStatusColor(status: ToolStatus) {
  switch (status) {
    case 'running':
      return 'text-status-running animate-spin';
    case 'success':
      return 'text-status-success';
    case 'error':
      return 'text-status-error';
  }
}

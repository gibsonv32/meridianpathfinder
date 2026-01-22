import clsx from 'clsx';

// =============================================================================
// Skeleton Loading Components
// =============================================================================

interface SkeletonProps {
  className?: string;
  animate?: boolean;
}

export function Skeleton({ className, animate = true }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'bg-bg-tertiary rounded',
        animate && 'animate-pulse',
        className
      )}
    />
  );
}

export function SkeletonText({ lines = 1, className }: { lines?: number; className?: string }) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={clsx(
            'h-4',
            i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}

export function SkeletonActivityItem() {
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-16 w-full rounded-lg" />
      </div>
    </div>
  );
}

export function SkeletonModeItem() {
  return (
    <div className="flex items-center gap-3 px-3 py-2">
      <Skeleton className="w-4 h-4 rounded-full" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

export function SkeletonArtifactCard() {
  return (
    <div className="p-4 border border-border-subtle rounded-lg space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <div className="flex-1 space-y-1">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
      <Skeleton className="h-20 w-full rounded" />
    </div>
  );
}

// =============================================================================
// Loading Spinners
// =============================================================================

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <svg
      className={clsx('animate-spin', sizeClasses[size], className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// =============================================================================
// Progress Indicators
// =============================================================================

export function ProgressBar({
  progress,
  className,
  showLabel = false,
}: {
  progress: number;
  className?: string;
  showLabel?: boolean;
}) {
  return (
    <div className={clsx('relative', className)}>
      <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className="h-full bg-accent-blue rounded-full transition-all duration-300 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      {showLabel && (
        <span className="absolute right-0 -top-5 text-2xs text-text-muted">
          {Math.round(progress)}%
        </span>
      )}
    </div>
  );
}

export function PulsingDot({ color = 'blue' }: { color?: 'blue' | 'green' | 'yellow' | 'red' }) {
  const colorClasses = {
    blue: 'bg-accent-blue',
    green: 'bg-status-success',
    yellow: 'bg-status-warning',
    red: 'bg-status-error',
  };

  return (
    <span className="relative flex h-2 w-2">
      <span
        className={clsx(
          'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
          colorClasses[color]
        )}
      />
      <span
        className={clsx(
          'relative inline-flex rounded-full h-2 w-2',
          colorClasses[color]
        )}
      />
    </span>
  );
}

// =============================================================================
// Empty States
// =============================================================================

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-bg-tertiary flex items-center justify-center mb-4 text-text-muted">
        {icon}
      </div>
      <h3 className="font-medium text-text-primary mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-text-secondary max-w-sm">{description}</p>
      )}
      {action && (
        <button onClick={action.onClick} className="btn btn-primary mt-4">
          {action.label}
        </button>
      )}
    </div>
  );
}

// =============================================================================
// Streaming Text
// =============================================================================

export function StreamingText({ text }: { text: string; speed?: number }) {
  // For actual streaming, you'd use a state and interval
  // This is a CSS-only approximation
  return (
    <span className="inline-block">
      {text}
      <span className="inline-block w-2 h-4 ml-0.5 bg-text-primary animate-pulse" />
    </span>
  );
}

// =============================================================================
// Typing Indicator
// =============================================================================

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      <span className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  );
}

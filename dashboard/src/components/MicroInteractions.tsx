import { useState, useEffect } from 'react';
import { Check, ThumbsUp } from 'lucide-react';
import clsx from 'clsx';

// =============================================================================
// Success Animation
// =============================================================================

export function SuccessCheckmark({ show }: { show: boolean }) {
  if (!show) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-50">
      <div className="w-20 h-20 rounded-full bg-status-success/20 flex items-center justify-center animate-scale-in">
        <Check className="w-10 h-10 text-status-success animate-draw-check" />
      </div>
    </div>
  );
}

// =============================================================================
// Ripple Effect Button
// =============================================================================

export function RippleButton({
  children,
  className,
  onClick,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const [ripples, setRipples] = useState<{ x: number; y: number; id: number }[]>([]);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const id = Date.now();

    setRipples((prev) => [...prev, { x, y, id }]);
    setTimeout(() => {
      setRipples((prev) => prev.filter((r) => r.id !== id));
    }, 600);

    onClick?.(e);
  };

  return (
    <button
      className={clsx('relative overflow-hidden', className)}
      onClick={handleClick}
      {...props}
    >
      {children}
      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          className="absolute rounded-full bg-white/30 animate-ripple pointer-events-none"
          style={{
            left: ripple.x,
            top: ripple.y,
            transform: 'translate(-50%, -50%)',
          }}
        />
      ))}
    </button>
  );
}

// =============================================================================
// Hover Card
// =============================================================================

export function HoverCard({
  children,
  content,
  className,
}: {
  children: React.ReactNode;
  content: React.ReactNode;
  className?: string;
}) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={clsx('relative inline-block', className)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {children}
      {isHovered && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 animate-fade-in">
          <div className="bg-bg-elevated border border-border rounded-lg shadow-xl p-3 min-w-48">
            {content}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1">
            <div className="border-8 border-transparent border-t-bg-elevated" />
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Number Counter Animation
// =============================================================================

export function AnimatedCounter({
  value,
  duration = 1000,
  className,
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const startValue = displayValue;
    const diff = value - startValue;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Ease out cubic

      setDisplayValue(Math.round(startValue + diff * eased));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return <span className={className}>{displayValue}</span>;
}

// =============================================================================
// Confetti Effect (simplified)
// =============================================================================

export function Confetti({ trigger }: { trigger: boolean }) {
  const [particles, setParticles] = useState<
    { id: number; x: number; color: string; delay: number }[]
  >([]);

  useEffect(() => {
    if (trigger) {
      const colors = ['#3b82f6', '#22c55e', '#eab308', '#a855f7', '#f97316'];
      const newParticles = Array.from({ length: 30 }).map((_, i) => ({
        id: i,
        x: Math.random() * 100,
        color: colors[Math.floor(Math.random() * colors.length)],
        delay: Math.random() * 500,
      }));
      setParticles(newParticles);

      const timer = setTimeout(() => setParticles([]), 2000);
      return () => clearTimeout(timer);
    }
  }, [trigger]);

  if (particles.length === 0) return null;

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-50">
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute w-2 h-2 rounded-full animate-confetti"
          style={{
            left: `${p.x}%`,
            top: '-10px',
            backgroundColor: p.color,
            animationDelay: `${p.delay}ms`,
          }}
        />
      ))}
    </div>
  );
}

// =============================================================================
// Slide Toggle
// =============================================================================

export function SlideToggle({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <label className={clsx('flex items-center gap-2 cursor-pointer', disabled && 'opacity-50 cursor-not-allowed')}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={clsx(
          'relative w-10 h-6 rounded-full transition-colors duration-200',
          checked ? 'bg-accent-blue' : 'bg-bg-tertiary'
        )}
      >
        <span
          className={clsx(
            'absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200',
            checked && 'translate-x-4'
          )}
        />
      </button>
      {label && <span className="text-sm text-text-secondary">{label}</span>}
    </label>
  );
}

// =============================================================================
// Feedback Buttons
// =============================================================================

export function FeedbackButtons({
  onFeedback,
}: {
  onFeedback: (type: 'helpful' | 'not_helpful') => void;
}) {
  const [selected, setSelected] = useState<'helpful' | 'not_helpful' | null>(null);

  const handleSelect = (type: 'helpful' | 'not_helpful') => {
    setSelected(type);
    onFeedback(type);
  };

  return (
    <div className="flex items-center gap-1">
      <span className="text-2xs text-text-muted mr-2">Was this helpful?</span>
      <button
        onClick={() => handleSelect('helpful')}
        className={clsx(
          'p-1.5 rounded transition-colors',
          selected === 'helpful'
            ? 'bg-status-success/20 text-status-success'
            : 'text-text-muted hover:text-text-secondary hover:bg-bg-hover'
        )}
      >
        <ThumbsUp className="w-4 h-4" />
      </button>
      <button
        onClick={() => handleSelect('not_helpful')}
        className={clsx(
          'p-1.5 rounded transition-colors rotate-180',
          selected === 'not_helpful'
            ? 'bg-status-error/20 text-status-error'
            : 'text-text-muted hover:text-text-secondary hover:bg-bg-hover'
        )}
      >
        <ThumbsUp className="w-4 h-4" />
      </button>
    </div>
  );
}

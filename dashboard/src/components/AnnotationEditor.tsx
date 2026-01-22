import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Check, Edit2 } from 'lucide-react';
import { useDashboardStore } from '../store';

interface AnnotationEditorProps {
  activityId: string;
  currentAnnotation?: string;
  onClose?: () => void;
}

export function AnnotationEditor({ activityId, currentAnnotation, onClose }: AnnotationEditorProps) {
  const [isEditing, setIsEditing] = useState(!currentAnnotation);
  const [text, setText] = useState(currentAnnotation || '');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const setActivityAnnotation = useDashboardStore((s) => s.setActivityAnnotation);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = () => {
    setActivityAnnotation(activityId, text.trim());
    setIsEditing(false);
    onClose?.();
  };

  const handleCancel = () => {
    setText(currentAnnotation || '');
    setIsEditing(false);
    onClose?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (!isEditing && currentAnnotation) {
    return (
      <div className="group relative mt-2 pl-3 border-l-2 border-accent-yellow/50">
        <p className="text-sm text-text-secondary italic pr-8">{currentAnnotation}</p>
        <button
          onClick={() => setIsEditing(true)}
          className="absolute top-0 right-0 p-1 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-bg-hover rounded"
        >
          <Edit2 className="w-3.5 h-3.5 text-text-muted" />
        </button>
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-start gap-2">
        <MessageSquare className="w-4 h-4 text-accent-yellow mt-2 flex-shrink-0" />
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a note (decision rationale, assumptions, etc.)"
          className="flex-1 input-base px-3 py-2 text-sm resize-none min-h-[60px]"
          rows={2}
        />
      </div>
      <div className="flex items-center gap-2 justify-end">
        <span className="text-2xs text-text-muted">⌘+Enter to save</span>
        <button onClick={handleCancel} className="btn btn-ghost text-sm">
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={!text.trim()}
          className="btn btn-primary text-sm"
        >
          <Check className="w-3.5 h-3.5" />
          Save Note
        </button>
      </div>
    </div>
  );
}

// Inline annotation button for activity items
export function AddAnnotationButton({ activityId }: { activityId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const activity = useDashboardStore((s) => s.activities.find((a) => a.id === activityId));

  if (activity?.annotation) {
    return null; // Already has annotation, show inline editor instead
  }

  if (isOpen) {
    return <AnnotationEditor activityId={activityId} onClose={() => setIsOpen(false)} />;
  }

  return (
    <button
      onClick={() => setIsOpen(true)}
      className="mt-2 flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
    >
      <MessageSquare className="w-3.5 h-3.5" />
      Add note
    </button>
  );
}

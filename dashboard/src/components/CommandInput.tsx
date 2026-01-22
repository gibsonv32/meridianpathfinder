import { useState, useRef, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Send,
  Paperclip,
  X,
  File,
  Image,
  FileText,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { useDashboardStore } from '../store';
import type { Attachment } from '../types';
import toast from 'react-hot-toast';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export function CommandInput() {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const historyIndexRef = useRef(-1);

  const {
    attachments,
    addAttachment,
    updateAttachment,
    removeAttachment,
    clearAttachments,
    addActivity,
    addToCommandHistory,
    commandHistory,
  } = useDashboardStore();

  // Handle file drops
  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      rejectedFiles.forEach((rejection) => {
        const error =
          rejection.errors[0]?.code === 'file-too-large'
            ? 'File too large (max 50MB)'
            : rejection.errors[0]?.code === 'file-invalid-type'
            ? 'Invalid file type'
            : 'Upload failed';
        toast.error(`${rejection.file.name}: ${error}`);
      });

      acceptedFiles.forEach((file) => {
        const attachment: Attachment = {
          id: crypto.randomUUID(),
          file,
          name: file.name,
          type: file.type,
          size: file.size,
          status: 'pending',
          progress: 0,
        };
        addAttachment(attachment);
        simulateUpload(attachment.id);
      });
    },
    [addAttachment]
  );

  // Simulate upload progress
  const simulateUpload = (id: string) => {
    updateAttachment(id, { status: 'uploading', progress: 0 });

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 30;
      if (progress >= 100) {
        clearInterval(interval);
        updateAttachment(id, {
          status: 'success',
          progress: 100,
          artifactId: crypto.randomUUID(),
        });
      } else {
        updateAttachment(id, { progress: Math.min(progress, 95) });
      }
    }, 200);
  };

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    noClick: true,
    noKeyboard: true,
    maxSize: MAX_FILE_SIZE,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'text/plain': ['.txt', '.md'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/pdf': ['.pdf'],
    },
  });

  // Handle submit
  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed && attachments.length === 0) return;

    // Add to command history
    if (trimmed) {
      addToCommandHistory(trimmed);
    }

    // Create activity
    addActivity({
      id: crypto.randomUUID(),
      type: 'user_command',
      timestamp: new Date().toISOString(),
      content: trimmed,
    });

    // Parse command
    if (trimmed.startsWith('/')) {
      handleSlashCommand(trimmed);
    }

    // Clear input
    setInput('');
    historyIndexRef.current = -1;
    clearAttachments();
  };

  // Handle slash commands
  const handleSlashCommand = (command: string) => {
    const parts = command.slice(1).split(/\s+/);
    const cmd = parts[0]?.toLowerCase();

    switch (cmd) {
      case 'run':
        // Simulate mode run
        const modeId = parts[2] || '0';
        addActivity({
          id: crypto.randomUUID(),
          type: 'mode_started',
          timestamp: new Date().toISOString(),
          modeId: modeId as any,
          content: `Starting mode ${modeId}...`,
        });
        break;
      case 'status':
        addActivity({
          id: crypto.randomUUID(),
          type: 'system_notice',
          timestamp: new Date().toISOString(),
          content: 'Project status: 3/10 modes completed. Current mode: idle.',
          severity: 'info',
        });
        break;
      case 'help':
        addActivity({
          id: crypto.randomUUID(),
          type: 'system_notice',
          timestamp: new Date().toISOString(),
          content:
            'Available commands:\n/run mode <N> - Run a specific mode\n/status - Show project status\n/artifacts - List artifacts\n/clear - Clear activity feed',
          severity: 'info',
        });
        break;
      default:
        addActivity({
          id: crypto.randomUUID(),
          type: 'system_notice',
          timestamp: new Date().toISOString(),
          content: `Unknown command: ${cmd}`,
          severity: 'warning',
        });
    }
  };

  // Handle keyboard
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    } else if (e.key === 'Enter' && e.shiftKey) {
      // Allow multiline
    } else if (e.key === 'ArrowUp' && !input && commandHistory.length > 0) {
      e.preventDefault();
      const newIndex = Math.min(historyIndexRef.current + 1, commandHistory.length - 1);
      historyIndexRef.current = newIndex;
      setInput(commandHistory[newIndex] || '');
    } else if (e.key === 'ArrowDown' && historyIndexRef.current >= 0) {
      e.preventDefault();
      const newIndex = historyIndexRef.current - 1;
      historyIndexRef.current = newIndex;
      setInput(newIndex >= 0 ? commandHistory[newIndex] : '');
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div
      {...getRootProps()}
      className={clsx(
        'border-t border-border-subtle bg-bg-secondary p-4',
        isDragActive && 'ring-2 ring-accent-blue ring-inset'
      )}
    >
      <input {...getInputProps()} />

      {/* Drop overlay */}
      {isDragActive && (
        <div className="absolute inset-0 bg-accent-blue/10 flex items-center justify-center z-10 pointer-events-none">
          <div className="text-accent-blue font-medium">Drop files here</div>
        </div>
      )}

      {/* Attachments */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {attachments.map((attachment) => (
            <AttachmentChip
              key={attachment.id}
              attachment={attachment}
              onRemove={() => removeAttachment(attachment.id)}
            />
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-3">
        <button
          onClick={open}
          className="btn btn-icon btn-ghost text-text-secondary hover:text-text-primary mb-1"
          title="Attach file"
        >
          <Paperclip className="w-5 h-5" />
        </button>

        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or message... (Enter to send, Shift+Enter for newline)"
            className={clsx(
              'w-full px-4 py-3 pr-12 rounded-xl input-base resize-none',
              'min-h-[48px] max-h-[200px]'
            )}
            rows={1}
          />

          {/* Hint */}
          {!input && (
            <div className="absolute left-4 bottom-full mb-1 text-2xs text-text-muted">
              Try: <code className="bg-bg-primary px-1 rounded">/run mode 0</code> or{' '}
              <code className="bg-bg-primary px-1 rounded">/help</code>
            </div>
          )}
        </div>

        <button
          onClick={handleSubmit}
          disabled={!input.trim() && attachments.length === 0}
          className={clsx(
            'btn btn-primary mb-1',
            (!input.trim() && attachments.length === 0) && 'opacity-50 cursor-not-allowed'
          )}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Attachment Chip
// -----------------------------------------------------------------------------

function AttachmentChip({
  attachment,
  onRemove,
}: {
  attachment: Attachment;
  onRemove: () => void;
}) {
  const Icon = getFileIcon(attachment.type);
  const isUploading = attachment.status === 'uploading';
  const isError = attachment.status === 'error';

  return (
    <div
      className={clsx(
        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
        'bg-bg-tertiary border',
        isError ? 'border-status-error/50' : 'border-border-subtle'
      )}
    >
      {isUploading ? (
        <Loader2 className="w-4 h-4 text-text-secondary animate-spin" />
      ) : isError ? (
        <AlertCircle className="w-4 h-4 text-status-error" />
      ) : (
        <Icon className="w-4 h-4 text-text-secondary" />
      )}

      <span className="max-w-32 truncate">{attachment.name}</span>

      {isUploading && (
        <span className="text-2xs text-text-muted">{Math.round(attachment.progress)}%</span>
      )}

      <button
        onClick={onRemove}
        className="p-0.5 hover:bg-bg-hover rounded"
      >
        <X className="w-3.5 h-3.5 text-text-muted hover:text-text-primary" />
      </button>
    </div>
  );
}

function getFileIcon(type: string) {
  if (type.startsWith('image/')) return Image;
  if (type === 'application/json' || type === 'text/csv') return FileText;
  return File;
}

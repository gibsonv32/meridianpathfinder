import { useState } from 'react';
import { AlertTriangle, Trash2, RotateCcw, RefreshCw } from 'lucide-react';
import clsx from 'clsx';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  icon?: React.ReactNode;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'warning',
  icon,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  const variantStyles = {
    danger: {
      bg: 'bg-status-error/10',
      border: 'border-status-error/30',
      icon: 'text-status-error',
      button: 'btn-danger',
    },
    warning: {
      bg: 'bg-status-warning/10',
      border: 'border-status-warning/30',
      icon: 'text-status-warning',
      button: 'bg-status-warning/20 text-status-warning hover:bg-status-warning/30',
    },
    info: {
      bg: 'bg-accent-blue/10',
      border: 'border-accent-blue/30',
      icon: 'text-accent-blue',
      button: 'btn-primary',
    },
  };

  const styles = variantStyles[variant];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Dialog */}
      <div className="relative w-full max-w-md bg-bg-secondary border border-border rounded-xl shadow-2xl overflow-hidden animate-fade-in">
        <div className="p-6">
          {/* Icon */}
          <div className={clsx('w-12 h-12 rounded-full flex items-center justify-center mb-4', styles.bg, styles.border, 'border')}>
            {icon || <AlertTriangle className={clsx('w-6 h-6', styles.icon)} />}
          </div>

          {/* Title & Message */}
          <h3 className="text-lg font-semibold mb-2">{title}</h3>
          <p className="text-text-secondary text-sm">{message}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-subtle bg-bg-tertiary">
          <button onClick={onClose} className="btn btn-secondary">
            {cancelLabel}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={clsx('btn', styles.button)}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// Pre-built confirmation dialogs for common actions
export function useConfirmDialog() {
  const [dialogState, setDialogState] = useState<{
    isOpen: boolean;
    props: Omit<ConfirmDialogProps, 'isOpen' | 'onClose'>;
  }>({
    isOpen: false,
    props: {
      onConfirm: () => {},
      title: '',
      message: '',
    },
  });

  const showDialog = (props: Omit<ConfirmDialogProps, 'isOpen' | 'onClose'>) => {
    setDialogState({ isOpen: true, props });
  };

  const closeDialog = () => {
    setDialogState((prev) => ({ ...prev, isOpen: false }));
  };

  const confirmDelete = (itemName: string, onConfirm: () => void) => {
    showDialog({
      title: 'Delete ' + itemName + '?',
      message: `This action cannot be undone. Are you sure you want to delete this ${itemName.toLowerCase()}?`,
      confirmLabel: 'Delete',
      variant: 'danger',
      icon: <Trash2 className="w-6 h-6 text-status-error" />,
      onConfirm,
    });
  };

  const confirmRerun = (modeName: string, onConfirm: () => void) => {
    showDialog({
      title: 'Rerun ' + modeName + '?',
      message: 'This will start a new run with the same parameters. Any in-progress runs will not be affected.',
      confirmLabel: 'Rerun',
      variant: 'info',
      icon: <RotateCcw className="w-6 h-6 text-accent-blue" />,
      onConfirm,
    });
  };

  const confirmOverwrite = (artifactName: string, onConfirm: () => void) => {
    showDialog({
      title: 'Overwrite ' + artifactName + '?',
      message: 'An artifact with this name already exists. Running this mode will create a new version.',
      confirmLabel: 'Continue',
      variant: 'warning',
      icon: <RefreshCw className="w-6 h-6 text-status-warning" />,
      onConfirm,
    });
  };

  const Dialog = () => (
    <ConfirmDialog
      isOpen={dialogState.isOpen}
      onClose={closeDialog}
      {...dialogState.props}
    />
  );

  return {
    Dialog,
    showDialog,
    confirmDelete,
    confirmRerun,
    confirmOverwrite,
  };
}

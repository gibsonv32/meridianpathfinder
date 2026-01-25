import { useState } from 'react';
import { Link2, Copy, Check, Mail, ExternalLink } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';

interface ShareableLinkProps {
  type: 'run' | 'artifact' | 'activity';
  id: string;
  title?: string;
}

export function ShareableLink({ type, id, title }: ShareableLinkProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const baseUrl = window.location.origin;
  const shareUrl = `${baseUrl}/${type}/${id}`;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    toast.success('Link copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEmailShare = () => {
    const subject = encodeURIComponent(`MERIDIAN ${type}: ${title || id}`);
    const body = encodeURIComponent(`Check out this ${type} in MERIDIAN:\n\n${shareUrl}`);
    window.open(`mailto:?subject=${subject}&body=${body}`);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-icon btn-ghost"
        title="Share link"
      >
        <Link2 className="w-4 h-4" />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

          {/* Popover */}
          <div className="absolute right-0 top-full mt-2 w-80 bg-bg-secondary border border-border rounded-lg shadow-xl z-50 overflow-hidden animate-fade-in">
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Link2 className="w-4 h-4 text-accent-blue" />
                <span className="font-medium">Share {type}</span>
              </div>

              {/* URL Input */}
              <div className="flex items-center gap-2 mb-4">
                <input
                  type="text"
                  value={shareUrl}
                  readOnly
                  className="flex-1 input-base px-3 py-2 text-sm font-mono truncate"
                />
                <button
                  onClick={handleCopy}
                  className={clsx(
                    'btn btn-icon',
                    copied ? 'btn-primary' : 'btn-secondary'
                  )}
                >
                  {copied ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* Share Options */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleEmailShare}
                  className="btn btn-ghost flex-1 text-sm"
                >
                  <Mail className="w-4 h-4" />
                  Email
                </button>
                <button
                  onClick={() => window.open(shareUrl, '_blank')}
                  className="btn btn-ghost flex-1 text-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open
                </button>
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-border-subtle bg-bg-tertiary">
              <p className="text-2xs text-text-muted">
                Anyone with this link can view this {type} if they have project access.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Copy ID button for quick sharing
export function CopyIdButton({ id, label = 'ID' }: { id: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(id);
    setCopied(true);
    toast.success(`${label} copied`);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-bg-tertiary hover:bg-bg-hover text-2xs font-mono text-text-secondary transition-colors"
      title={`Copy ${label}`}
    >
      {copied ? (
        <Check className="w-3 h-3 text-status-success" />
      ) : (
        <Copy className="w-3 h-3" />
      )}
      {id.slice(0, 8)}...
    </button>
  );
}

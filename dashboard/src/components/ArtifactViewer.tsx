import { useState } from 'react';
import {
  X,
  Download,
  Copy,
  ExternalLink,
  FileBox,
  Clock,
  Hash,
  GitBranch,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { useDashboardStore } from '../store';
import toast from 'react-hot-toast';

export function ArtifactViewer() {
  const selectedArtifact = useDashboardStore((s) => s.selectedArtifact);
  const setSelectedArtifact = useDashboardStore((s) => s.setSelectedArtifact);
  const [activeTab, setActiveTab] = useState<'preview' | 'metadata' | 'lineage'>('preview');

  if (!selectedArtifact) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(selectedArtifact.id);
    toast.success('Artifact ID copied');
  };

  const handleDownload = () => {
    // In real implementation, trigger download from API
    toast.success('Download started');
  };

  return (
    <aside className="w-96 bg-bg-secondary border-l border-border-subtle flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border-subtle">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center flex-shrink-0">
            <FileBox className="w-5 h-5 text-accent-blue" />
          </div>
          <div className="min-w-0">
            <h2 className="font-semibold truncate">{selectedArtifact.name}</h2>
            <div className="text-xs text-text-secondary">{selectedArtifact.type}</div>
          </div>
        </div>
        <button
          onClick={() => setSelectedArtifact(null)}
          className="btn btn-icon btn-ghost"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 p-3 border-b border-border-subtle">
        <button onClick={handleDownload} className="btn btn-secondary flex-1">
          <Download className="w-4 h-4" />
          Download
        </button>
        <button onClick={handleCopyId} className="btn btn-ghost">
          <Copy className="w-4 h-4" />
        </button>
        <button className="btn btn-ghost">
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border-subtle">
        <TabButton
          active={activeTab === 'preview'}
          onClick={() => setActiveTab('preview')}
          label="Preview"
        />
        <TabButton
          active={activeTab === 'metadata'}
          onClick={() => setActiveTab('metadata')}
          label="Metadata"
        />
        <TabButton
          active={activeTab === 'lineage'}
          onClick={() => setActiveTab('lineage')}
          label="Lineage"
        />
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'preview' && <PreviewTab artifact={selectedArtifact} />}
        {activeTab === 'metadata' && <MetadataTab artifact={selectedArtifact} />}
        {activeTab === 'lineage' && <LineageTab artifact={selectedArtifact} />}
      </div>
    </aside>
  );
}

function TabButton({
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
        'flex-1 py-2.5 text-sm font-medium transition-colors',
        active
          ? 'text-text-primary border-b-2 border-accent-blue'
          : 'text-text-tertiary hover:text-text-secondary border-b-2 border-transparent'
      )}
    >
      {label}
    </button>
  );
}

function PreviewTab({ artifact }: { artifact: any }) {
  // For demo purposes, show mock content based on type
  const isJson = artifact.type.includes('JSON') || artifact.name.endsWith('.json');
  const isCsv = artifact.name.endsWith('.csv');

  if (isJson) {
    return (
      <div className="p-4">
        <div className="bg-bg-primary rounded-lg border border-border-subtle p-4 font-mono text-sm overflow-x-auto">
          <JsonTreeView
            data={{
              artifact_id: artifact.id,
              artifact_type: artifact.type,
              mode_id: artifact.modeId,
              created_at: artifact.createdAt,
              content: {
                summary: 'Example artifact content',
                metrics: {
                  accuracy: 0.92,
                  precision: 0.89,
                  recall: 0.94,
                },
                recommendations: [
                  'Consider ensemble methods',
                  'Feature engineering for categorical vars',
                ],
              },
            }}
          />
        </div>
      </div>
    );
  }

  if (isCsv) {
    return (
      <div className="p-4">
        <div className="bg-bg-primary rounded-lg border border-border-subtle overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="px-3 py-2 text-left text-text-secondary font-medium">Column</th>
                <th className="px-3 py-2 text-left text-text-secondary font-medium">Type</th>
                <th className="px-3 py-2 text-left text-text-secondary font-medium">Non-null</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border-subtle">
                <td className="px-3 py-2">customer_id</td>
                <td className="px-3 py-2 text-text-secondary">int64</td>
                <td className="px-3 py-2 text-text-secondary">10000</td>
              </tr>
              <tr className="border-b border-border-subtle">
                <td className="px-3 py-2">revenue</td>
                <td className="px-3 py-2 text-text-secondary">float64</td>
                <td className="px-3 py-2 text-text-secondary">9850</td>
              </tr>
              <tr>
                <td className="px-3 py-2">churn</td>
                <td className="px-3 py-2 text-text-secondary">bool</td>
                <td className="px-3 py-2 text-text-secondary">10000</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-text-muted mt-2">Showing schema preview. Full data available for download.</p>
      </div>
    );
  }

  return (
    <div className="p-4 text-center text-text-secondary">
      <FileBox className="w-12 h-12 mx-auto mb-3 opacity-50" />
      <p>Preview not available for this file type</p>
      <button className="btn btn-secondary mt-3">
        <Download className="w-4 h-4" />
        Download to view
      </button>
    </div>
  );
}

function MetadataTab({ artifact }: { artifact: any }) {
  return (
    <div className="p-4 space-y-4">
      <MetadataItem
        icon={Hash}
        label="Artifact ID"
        value={artifact.id}
        mono
      />
      <MetadataItem
        icon={FileBox}
        label="Type"
        value={artifact.type}
      />
      <MetadataItem
        icon={Clock}
        label="Created"
        value={formatDistanceToNow(new Date(artifact.createdAt), { addSuffix: true })}
      />
      <MetadataItem
        icon={artifact.verified ? CheckCircle2 : XCircle}
        label="Verified"
        value={artifact.verified ? 'Yes' : 'No'}
        valueColor={artifact.verified ? 'text-status-success' : 'text-status-error'}
      />
      {artifact.checksum && (
        <MetadataItem
          icon={Hash}
          label="Checksum"
          value={artifact.checksum.slice(0, 16) + '...'}
          mono
        />
      )}
    </div>
  );
}

function MetadataItem({
  icon: Icon,
  label,
  value,
  mono,
  valueColor,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  mono?: boolean;
  valueColor?: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="w-4 h-4 text-text-tertiary mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="text-xs text-text-secondary mb-0.5">{label}</div>
        <div
          className={clsx(
            'text-sm truncate',
            mono && 'font-mono',
            valueColor || 'text-text-primary'
          )}
        >
          {value}
        </div>
      </div>
    </div>
  );
}

function LineageTab({ artifact }: { artifact: any }) {
  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <GitBranch className="w-4 h-4 text-text-tertiary" />
        <span className="text-sm text-text-secondary">Artifact Lineage</span>
      </div>

      <div className="space-y-2">
        {/* Current artifact */}
        <div className="flex items-center gap-2 px-3 py-2 bg-accent-blue/10 border border-accent-blue/30 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-accent-blue" />
          <span className="text-sm font-medium">{artifact.name}</span>
          <span className="text-xs text-text-muted ml-auto">current</span>
        </div>

        {/* Parent artifacts (mock) */}
        {artifact.parentArtifacts?.map((parentId: string) => (
          <div
            key={parentId}
            className="flex items-center gap-2 px-3 py-2 bg-bg-tertiary border border-border-subtle rounded-lg ml-4"
          >
            <div className="w-2 h-2 rounded-full bg-text-muted" />
            <span className="text-sm text-text-secondary">Parent: {parentId.slice(0, 8)}...</span>
          </div>
        )) || (
          <div className="text-sm text-text-muted pl-4">No parent artifacts</div>
        )}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// JSON Tree Viewer
// -----------------------------------------------------------------------------

function JsonTreeView({ data, depth = 0 }: { data: any; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (data === null) return <span className="text-text-muted">null</span>;
  if (typeof data === 'boolean') return <span className="text-accent-yellow">{String(data)}</span>;
  if (typeof data === 'number') return <span className="text-accent-green">{data}</span>;
  if (typeof data === 'string') return <span className="text-accent-orange">"{data}"</span>;

  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-text-muted">[]</span>;
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 hover:text-accent-blue"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className="text-text-muted">[{data.length}]</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-border-subtle pl-2 mt-1 space-y-1">
            {data.map((item, i) => (
              <div key={i}>
                <span className="text-text-muted">{i}: </span>
                <JsonTreeView data={item} depth={depth + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) return <span className="text-text-muted">{'{}'}</span>;
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 hover:text-accent-blue"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className="text-text-muted">{'{'}{keys.length}{'}'}</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-border-subtle pl-2 mt-1 space-y-1">
            {keys.map((key) => (
              <div key={key}>
                <span className="text-accent-blue">{key}</span>
                <span className="text-text-muted">: </span>
                <JsonTreeView data={data[key]} depth={depth + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return <span>{String(data)}</span>;
}

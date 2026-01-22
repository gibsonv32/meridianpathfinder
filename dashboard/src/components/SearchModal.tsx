import { useState, useEffect, useRef, useMemo } from 'react';
import {
  Search,
  X,
  FileBox,
  Terminal,
  MessageSquare,
  Layers,
  Clock,
  ArrowRight,
} from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import { useDashboardStore } from '../store';

type SearchCategory = 'all' | 'activities' | 'artifacts' | 'modes';

interface SearchResult {
  id: string;
  type: 'activity' | 'artifact' | 'mode';
  title: string;
  subtitle: string;
  timestamp?: string;
  icon: React.ElementType;
}

export function SearchModal() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<SearchCategory>('all');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const { setSearchOpen, activities, artifacts, modes, setSelectedArtifact } = useDashboardStore();

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSearchOpen(false);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && results[selectedIndex]) {
        handleSelect(results[selectedIndex]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIndex]);

  // Search results
  const results = useMemo((): SearchResult[] => {
    if (!query.trim()) return [];

    const q = query.toLowerCase();
    const allResults: SearchResult[] = [];

    // Search activities
    if (category === 'all' || category === 'activities') {
      activities
        .filter((a) => a.content?.toLowerCase().includes(q) || a.type.toLowerCase().includes(q))
        .slice(0, 5)
        .forEach((a) => {
          allResults.push({
            id: a.id,
            type: 'activity',
            title: a.content?.slice(0, 60) || a.type,
            subtitle: `${a.type} ${a.modeId ? `• Mode ${a.modeId}` : ''}`,
            timestamp: a.timestamp,
            icon: a.type === 'user_command' ? MessageSquare : Terminal,
          });
        });
    }

    // Search artifacts
    if (category === 'all' || category === 'artifacts') {
      artifacts
        .filter(
          (a) =>
            a.name.toLowerCase().includes(q) ||
            a.type.toLowerCase().includes(q) ||
            a.id.toLowerCase().includes(q)
        )
        .slice(0, 5)
        .forEach((a) => {
          allResults.push({
            id: a.id,
            type: 'artifact',
            title: a.name,
            subtitle: `${a.type} • Mode ${a.modeId}`,
            timestamp: a.createdAt,
            icon: FileBox,
          });
        });
    }

    // Search modes
    if (category === 'all' || category === 'modes') {
      modes
        .filter(
          (m) =>
            m.name.toLowerCase().includes(q) ||
            m.id.toLowerCase().includes(q) ||
            m.description.toLowerCase().includes(q)
        )
        .slice(0, 5)
        .forEach((m) => {
          allResults.push({
            id: m.id,
            type: 'mode',
            title: `Mode ${m.id}: ${m.name}`,
            subtitle: m.description,
            icon: Layers,
          });
        });
    }

    return allResults;
  }, [query, category, activities, artifacts, modes]);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results]);

  const handleSelect = (result: SearchResult) => {
    if (result.type === 'artifact') {
      const artifact = artifacts.find((a) => a.id === result.id);
      if (artifact) setSelectedArtifact(artifact as any);
    }
    setSearchOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setSearchOpen(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-bg-secondary border border-border rounded-xl shadow-2xl overflow-hidden animate-fade-in">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
          <Search className="w-5 h-5 text-text-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search activities, artifacts, modes..."
            className="flex-1 bg-transparent text-text-primary placeholder:text-text-muted focus:outline-none"
          />
          <button
            onClick={() => setSearchOpen(false)}
            className="p-1 hover:bg-bg-hover rounded"
          >
            <X className="w-5 h-5 text-text-muted" />
          </button>
        </div>

        {/* Categories */}
        <div className="flex gap-1 px-4 py-2 border-b border-border-subtle">
          <CategoryTab
            active={category === 'all'}
            onClick={() => setCategory('all')}
            label="All"
          />
          <CategoryTab
            active={category === 'activities'}
            onClick={() => setCategory('activities')}
            label="Activities"
          />
          <CategoryTab
            active={category === 'artifacts'}
            onClick={() => setCategory('artifacts')}
            label="Artifacts"
          />
          <CategoryTab
            active={category === 'modes'}
            onClick={() => setCategory('modes')}
            label="Modes"
          />
        </div>

        {/* Results */}
        <div className="max-h-96 overflow-y-auto">
          {query.trim() === '' ? (
            <div className="p-8 text-center text-text-muted">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Start typing to search...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center text-text-muted">
              <p>No results found for "{query}"</p>
            </div>
          ) : (
            <div className="py-2">
              {results.map((result, index) => (
                <SearchResultItem
                  key={result.id}
                  result={result}
                  selected={index === selectedIndex}
                  onClick={() => handleSelect(result)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-border-subtle flex items-center gap-4 text-xs text-text-muted">
          <span>
            <kbd className="bg-bg-primary px-1.5 py-0.5 rounded">↑↓</kbd> Navigate
          </span>
          <span>
            <kbd className="bg-bg-primary px-1.5 py-0.5 rounded">↵</kbd> Select
          </span>
          <span>
            <kbd className="bg-bg-primary px-1.5 py-0.5 rounded">esc</kbd> Close
          </span>
        </div>
      </div>
    </div>
  );
}

function CategoryTab({
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
        'px-3 py-1 rounded-md text-sm transition-colors',
        active
          ? 'bg-accent-blue/20 text-accent-blue'
          : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
      )}
    >
      {label}
    </button>
  );
}

function SearchResultItem({
  result,
  selected,
  onClick,
}: {
  result: SearchResult;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = result.icon;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full flex items-center gap-3 px-4 py-2 text-left transition-colors',
        selected ? 'bg-bg-hover' : 'hover:bg-bg-tertiary'
      )}
    >
      <div className="w-8 h-8 rounded-lg bg-bg-tertiary flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-text-secondary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{result.title}</div>
        <div className="text-xs text-text-muted truncate">{result.subtitle}</div>
      </div>
      {result.timestamp && (
        <div className="flex items-center gap-1 text-2xs text-text-muted">
          <Clock className="w-3 h-3" />
          {formatDistanceToNow(new Date(result.timestamp), { addSuffix: true })}
        </div>
      )}
      {selected && <ArrowRight className="w-4 h-4 text-text-muted" />}
    </button>
  );
}

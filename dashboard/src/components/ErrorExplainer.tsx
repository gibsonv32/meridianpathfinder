import { useState } from 'react';
import {
  AlertCircle,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Sparkles,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';

interface ErrorExplainerProps {
  error: string;
  context?: {
    modeId?: string;
    command?: string;
    exitCode?: number;
    logs?: string;
  };
}

interface Explanation {
  summary: string;
  cause: string;
  solutions: string[];
  docsLink?: string;
}

// Mock LLM-generated explanations based on error patterns
const generateExplanation = (error: string, _context?: any): Explanation => {
  const errorLower = error.toLowerCase();

  if (errorLower.includes('target column not found')) {
    return {
      summary: 'The specified target column does not exist in your dataset.',
      cause: 'The column name passed to --target does not match any column in the CSV file. This could be due to a typo, case sensitivity, or the column being named differently.',
      solutions: [
        'Check the exact column names in your CSV file using `head -1 data.csv`',
        'Ensure the column name is case-sensitive (e.g., "Churn" vs "churn")',
        'Verify no extra whitespace in column names',
        'Try running Mode 0 (EDA) first to see all available columns',
      ],
      docsLink: '/docs/modes/mode-2#target-column',
    };
  }

  if (errorLower.includes('validation error') || errorLower.includes('pydantic')) {
    return {
      summary: 'Input validation failed - the provided data does not match expected format.',
      cause: 'The input parameters or data structure does not conform to the expected schema. This usually means a required field is missing or has an incorrect type.',
      solutions: [
        'Review the command parameters and ensure all required fields are provided',
        'Check data types (strings vs numbers, lists vs single values)',
        'Run with --help to see the expected parameter format',
        'Validate your JSON input if providing structured data',
      ],
    };
  }

  if (errorLower.includes('api key') || errorLower.includes('authentication')) {
    return {
      summary: 'Authentication failed - API key is missing or invalid.',
      cause: 'The LLM provider (Anthropic/OpenAI) rejected the request due to missing or invalid credentials.',
      solutions: [
        'Set ANTHROPIC_API_KEY environment variable',
        'Check that your API key is valid and not expired',
        'Verify the key has sufficient permissions/credits',
        'Run `meridian llm status` to check connectivity',
      ],
      docsLink: '/docs/configuration#llm-setup',
    };
  }

  if (errorLower.includes('gate blocked') || errorLower.includes('prerequisite')) {
    return {
      summary: 'Mode prerequisites not met - a required earlier mode must complete first.',
      cause: 'MERIDIAN enforces a gated workflow where certain modes depend on artifacts from previous modes.',
      solutions: [
        'Run `meridian status` to see which modes are complete',
        'Complete the prerequisite mode(s) before running this one',
        'Check that required artifacts exist in .meridian/artifacts/',
        'Use --force to override (not recommended for production)',
      ],
      docsLink: '/docs/concepts/gates',
    };
  }

  if (errorLower.includes('memory') || errorLower.includes('oom')) {
    return {
      summary: 'Out of memory - the operation exceeded available RAM or GPU memory.',
      cause: 'Large datasets or models can exhaust system memory, especially when loading into pandas or running ML operations.',
      solutions: [
        'Reduce dataset size or use sampling for initial exploration',
        'Process data in chunks using `chunksize` parameter',
        'Increase system swap space or use a machine with more RAM',
        'For GPU OOM, reduce batch size or use model quantization',
      ],
    };
  }

  // Generic fallback
  return {
    summary: 'An error occurred during execution.',
    cause: 'The specific cause could not be automatically determined from the error message.',
    solutions: [
      'Review the full error message and stack trace above',
      'Check the MERIDIAN logs at .meridian/logs/',
      'Search the documentation for the error message',
      'Run with LOG_LEVEL=DEBUG for more detailed output',
    ],
    docsLink: '/docs/troubleshooting',
  };
};

export function ErrorExplainer({ error, context }: ErrorExplainerProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [explanation, setExplanation] = useState<Explanation | null>(
    () => generateExplanation(error, context)
  );

  const handleCopyError = () => {
    const fullError = [
      `Error: ${error}`,
      context?.modeId && `Mode: ${context.modeId}`,
      context?.command && `Command: ${context.command}`,
      context?.exitCode !== undefined && `Exit code: ${context.exitCode}`,
      context?.logs && `\nLogs:\n${context.logs}`,
    ]
      .filter(Boolean)
      .join('\n');

    navigator.clipboard.writeText(fullError);
    toast.success('Error details copied');
  };

  const handleRegenerate = async () => {
    setIsGenerating(true);
    // Simulate LLM call
    await new Promise((r) => setTimeout(r, 1500));
    setExplanation(generateExplanation(error, context));
    setIsGenerating(false);
  };

  return (
    <div className="bg-status-error/5 border border-status-error/20 rounded-lg overflow-hidden">
      {/* Error Header */}
      <div
        className="flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-status-error/10 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <AlertCircle className="w-5 h-5 text-status-error flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-status-error">Error</div>
          <div className="text-sm text-text-secondary mt-0.5 truncate">{error}</div>
        </div>
        <button className="p-1">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-text-tertiary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-tertiary" />
          )}
        </button>
      </div>

      {/* Expanded Content */}
      {isExpanded && explanation && (
        <div className="border-t border-status-error/20">
          {/* AI Explanation */}
          <div className="px-4 py-3 bg-bg-tertiary/50">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-accent-purple" />
              <span className="text-xs font-medium text-accent-purple">AI Explanation</span>
              <button
                onClick={handleRegenerate}
                disabled={isGenerating}
                className="ml-auto text-xs text-text-muted hover:text-text-secondary flex items-center gap-1"
              >
                {isGenerating ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )}
                Regenerate
              </button>
            </div>
            <p className="text-sm text-text-primary">{explanation.summary}</p>
          </div>

          {/* Cause */}
          <div className="px-4 py-3 border-t border-border-subtle">
            <div className="text-xs font-medium text-text-muted mb-1">Likely Cause</div>
            <p className="text-sm text-text-secondary">{explanation.cause}</p>
          </div>

          {/* Solutions */}
          <div className="px-4 py-3 border-t border-border-subtle">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="w-4 h-4 text-accent-yellow" />
              <span className="text-xs font-medium text-text-muted">Suggested Solutions</span>
            </div>
            <ul className="space-y-2">
              {explanation.solutions.map((solution, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-accent-blue font-mono">{i + 1}.</span>
                  <span className="text-text-secondary">{solution}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 px-4 py-3 border-t border-border-subtle bg-bg-tertiary">
            <button onClick={handleCopyError} className="btn btn-secondary text-sm">
              <Copy className="w-3.5 h-3.5" />
              Copy Error
            </button>
            {explanation.docsLink && (
              <a
                href={explanation.docsLink}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost text-sm"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View Docs
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

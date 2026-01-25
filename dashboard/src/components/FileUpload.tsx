import { useState, useRef, useCallback } from 'react';
import {
  Upload,
  X,
  File,
  FileText,
  FileImage,
  FileSpreadsheet,
  Loader2,
  CheckCircle2,
  RefreshCw,
  Eye,
} from 'lucide-react';
import clsx from 'clsx';
import { formatBytes } from '../utils/format';

export interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  status: 'queued' | 'uploading' | 'processing' | 'complete' | 'failed';
  progress?: number;
  documentId?: string;
  error?: string;
  preview?: string;
}

interface FileUploadProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
  onFileRemoved: (fileId: string) => void;
  maxFiles?: number;
  maxFileSize?: number;
  acceptedTypes?: string[];
  className?: string;
  dropZoneText?: string;
  showPreview?: boolean;
}

const SUPPORTED_TYPES = {
  'application/pdf': { icon: File, label: 'PDF', color: 'text-red-500' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    icon: FileText,
    label: 'DOCX',
    color: 'text-blue-500',
  },
  'text/plain': { icon: FileText, label: 'TXT', color: 'text-gray-500' },
  'text/markdown': { icon: FileText, label: 'MD', color: 'text-purple-500' },
  'text/csv': { icon: FileSpreadsheet, label: 'CSV', color: 'text-green-500' },
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
    icon: FileSpreadsheet,
    label: 'XLSX',
    color: 'text-green-600',
  },
  'image/png': { icon: FileImage, label: 'PNG', color: 'text-blue-400' },
  'image/jpeg': { icon: FileImage, label: 'JPG', color: 'text-blue-400' },
  'application/json': { icon: FileText, label: 'JSON', color: 'text-yellow-500' },
  'application/x-yaml': { icon: FileText, label: 'YAML', color: 'text-orange-500' },
  'text/yaml': { icon: FileText, label: 'YAML', color: 'text-orange-500' },
};

export function FileUpload({
  onFilesUploaded,
  onFileRemoved,
  maxFiles = 10,
  maxFileSize = 50 * 1024 * 1024, // 50MB
  acceptedTypes = Object.keys(SUPPORTED_TYPES),
  className,
  dropZoneText = "Drop documents to attach",
  showPreview = true,
}: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isFileTypeSupported = useCallback(
    (type: string) => {
      return acceptedTypes.some((acceptedType) => {
        if (acceptedType.includes('*')) {
          const baseType = acceptedType.split('/')[0];
          return type.startsWith(baseType);
        }
        return type === acceptedType;
      });
    },
    [acceptedTypes]
  );

  const validateFile = useCallback(
    (file: File): { valid: boolean; error?: string } => {
      if (file.size > maxFileSize) {
        return { valid: false, error: `File size exceeds ${formatBytes(maxFileSize)}` };
      }
      if (!isFileTypeSupported(file.type)) {
        return { valid: false, error: 'Unsupported file type' };
      }
      return { valid: true };
    },
    [maxFileSize, isFileTypeSupported]
  );

  const simulateUpload = useCallback(async (file: UploadedFile): Promise<UploadedFile> => {
    // Simulate upload progress
    return new Promise((resolve) => {
      setUploadedFiles((prev) =>
        prev.map((f) => (f.id === file.id ? { ...f, status: 'uploading', progress: 0 } : f))
      );

      const interval = setInterval(() => {
        setUploadedFiles((prev) => {
          const updated = prev.map((f) => {
            if (f.id === file.id) {
              const newProgress = Math.min((f.progress || 0) + Math.random() * 30, 100);
              if (newProgress >= 100) {
                clearInterval(interval);
                resolve({
                  ...f,
                  status: 'complete' as const,
                  progress: 100,
                  documentId: `doc_${Math.random().toString(36).substr(2, 9)}`,
                });
                return { ...f, status: 'complete' as const, progress: 100 };
              }
              return { ...f, progress: newProgress };
            }
            return f;
          });
          return updated;
        });
      }, 100);
    });
  }, []);

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      const newFiles: UploadedFile[] = [];

      for (const file of fileArray) {
        if (uploadedFiles.length + newFiles.length >= maxFiles) {
          console.warn(`Maximum ${maxFiles} files allowed`);
          break;
        }

        const validation = validateFile(file);
        const uploadFile: UploadedFile = {
          id: Math.random().toString(36).substr(2, 9),
          name: file.name,
          type: file.type,
          size: file.size,
          status: validation.valid ? 'queued' : 'failed',
          error: validation.error,
        };

        newFiles.push(uploadFile);
      }

      setUploadedFiles((prev) => [...prev, ...newFiles]);

      // Start uploading valid files
      for (const file of newFiles.filter((f) => f.status === 'queued')) {
        try {
          await simulateUpload(file);
        } catch (error) {
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.id === file.id
                ? { ...f, status: 'failed', error: 'Upload failed' }
                : f
            )
          );
        }
      }

      onFilesUploaded(newFiles);
    },
    [uploadedFiles, maxFiles, validateFile, simulateUpload, onFilesUploaded]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFiles(files);
      }
    },
    [handleFiles]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFiles(files);
      }
      // Reset input to allow selecting the same file again
      e.target.value = '';
    },
    [handleFiles]
  );

  const removeFile = useCallback(
    (fileId: string) => {
      setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId));
      onFileRemoved(fileId);
    },
    [onFileRemoved]
  );

  const retryUpload = useCallback(
    async (fileId: string) => {
      const file = uploadedFiles.find((f) => f.id === fileId);
      if (file) {
        setUploadedFiles((prev) =>
          prev.map((f) => (f.id === fileId ? { ...f, status: 'queued', error: undefined } : f))
        );
        try {
          await simulateUpload(file);
        } catch (error) {
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.id === fileId ? { ...f, status: 'failed', error: 'Upload failed' } : f
            )
          );
        }
      }
    },
    [uploadedFiles, simulateUpload]
  );


  const getFileTypeInfo = useCallback((type: string) => {
    return SUPPORTED_TYPES[type as keyof typeof SUPPORTED_TYPES] || { 
      icon: File, 
      label: 'FILE', 
      color: 'text-gray-500' 
    };
  }, []);

  return (
    <div className={className}>
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={clsx(
          'relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
          isDragOver
            ? 'border-accent-blue bg-accent-blue/5'
            : 'border-border-subtle hover:border-accent-blue/50 hover:bg-bg-hover'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
        />

        <Upload className="w-8 h-8 mx-auto mb-3 text-text-muted" />
        <p className="text-sm text-text-primary mb-1">
          {isDragOver ? dropZoneText : 'Click to upload or drag and drop'}
        </p>
        <p className="text-xs text-text-muted">
          PDF, DOCX, TXT, MD, CSV, XLSX, JSON, YAML up to {formatBytes(maxFileSize)}
        </p>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {uploadedFiles.map((file) => (
            <FileUploadItem
              key={file.id}
              file={file}
              onRemove={() => removeFile(file.id)}
              onRetry={() => retryUpload(file.id)}
              showPreview={showPreview}
              typeInfo={getFileTypeInfo(file.type)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface FileUploadItemProps {
  file: UploadedFile;
  onRemove: () => void;
  onRetry: () => void;
  showPreview: boolean;
  typeInfo: { icon: React.ElementType; label: string; color: string };
}

function FileUploadItem({ file, onRemove, onRetry, showPreview, typeInfo }: FileUploadItemProps) {
  const Icon = typeInfo.icon;

  return (
    <div className="flex items-center gap-3 p-3 bg-bg-tertiary rounded-lg border border-border-subtle">
      {/* File Icon */}
      <div
        className={clsx(
          'w-8 h-8 rounded flex items-center justify-center flex-shrink-0',
          file.status === 'complete'
            ? 'bg-status-success/20'
            : file.status === 'failed'
            ? 'bg-status-error/20'
            : 'bg-bg-secondary'
        )}
      >
        <Icon
          className={clsx(
            'w-4 h-4',
            file.status === 'complete'
              ? 'text-status-success'
              : file.status === 'failed'
              ? 'text-status-error'
              : typeInfo.color
          )}
        />
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <div className="truncate text-sm font-medium">{file.name}</div>
          <span className={clsx('text-xs px-1.5 py-0.5 rounded font-medium', typeInfo.color)}>
            {typeInfo.label}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span>{formatBytes(file.size)}</span>
          {file.status === 'uploading' && file.progress !== undefined && (
            <span>• {Math.round(file.progress)}%</span>
          )}
          {file.status === 'complete' && file.documentId && (
            <span>• ID: {file.documentId}</span>
          )}
          {file.error && <span className="text-status-error">• {file.error}</span>}
        </div>

        {/* Progress bar for uploading files */}
        {file.status === 'uploading' && file.progress !== undefined && (
          <div className="mt-1 w-full h-1 bg-bg-primary rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-blue transition-all"
              style={{ width: `${file.progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Status Icon */}
      <div className="flex items-center gap-1">
        {file.status === 'uploading' && <Loader2 className="w-4 h-4 text-accent-blue animate-spin" />}
        {file.status === 'processing' && <Loader2 className="w-4 h-4 text-accent-yellow animate-spin" />}
        {file.status === 'complete' && <CheckCircle2 className="w-4 h-4 text-status-success" />}
        {file.status === 'failed' && (
          <button
            onClick={onRetry}
            className="p-1 hover:bg-bg-hover rounded transition-colors"
            title="Retry upload"
          >
            <RefreshCw className="w-4 h-4 text-status-error" />
          </button>
        )}

        {/* Preview button for completed files */}
        {file.status === 'complete' && showPreview && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              // TODO: Implement preview
              console.log('Preview file:', file);
            }}
            className="p-1 hover:bg-bg-hover rounded transition-colors"
            title="Preview file"
          >
            <Eye className="w-4 h-4 text-text-muted" />
          </button>
        )}

        {/* Remove button */}
        <button
          onClick={onRemove}
          className="p-1 hover:bg-bg-hover rounded transition-colors"
          title="Remove file"
        >
          <X className="w-4 h-4 text-text-muted" />
        </button>
      </div>
    </div>
  );
}
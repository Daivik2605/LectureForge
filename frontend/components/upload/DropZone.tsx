'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileIcon, X } from 'lucide-react';

import { cn } from '@/lib/utils';
import { formatFileSize } from '@/lib/utils';

interface DropZoneProps {
  file: File | null;
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
}

export function DropZone({ file, onFileSelect, onFileRemove }: DropZoneProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError('File is too large. Maximum size is 50MB.');
        } else if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError('Invalid file type. Please upload a .ppt, .pptx, .pdf, or .txt file.');
        } else {
          setError('Invalid file.');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.ms-powerpoint': ['.ppt'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation':
        ['.pptx'],
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  if (file) {
    return (
      <div className="border-2 border-dashed rounded-lg p-6 bg-secondary/20">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-lg">
            <FileIcon className="h-8 w-8 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{file.name}</p>
            <p className="text-sm text-muted-foreground">
              {formatFileSize(file.size)}
            </p>
          </div>
          <button
            onClick={onFileRemove}
            className="p-2 hover:bg-destructive/10 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-destructive" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-primary/50',
          error && 'border-destructive'
        )}
      >
        <input {...getInputProps()} />
        <Upload
          className={cn(
            'h-12 w-12 mx-auto mb-4',
            isDragActive ? 'text-primary' : 'text-muted-foreground'
          )}
        />
        <p className="text-lg font-medium mb-1">
          {isDragActive ? 'Drop your file here' : 'Drag & drop your file'}
        </p>
        <p className="text-sm text-muted-foreground mb-4">
          or click to browse files
        </p>
        <p className="text-xs text-muted-foreground">
          Supported formats: PPT, PPTX (presentations) • PDF, TXT (policy documents)
        </p>
      </div>
      {error && (
        <p className="text-sm text-destructive mt-2">{error}</p>
      )}
    </div>
  );
}

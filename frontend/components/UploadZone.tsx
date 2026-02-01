"use client";

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { uploadDocument, waitForRedaction, getRedactedDownloadUrl } from '@/lib/api';
import toast from 'react-hot-toast';

interface UploadZoneProps {
  onUploadComplete?: () => void;
  className?: string;
}

const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function UploadZone({ onUploadComplete, className }: UploadZoneProps) {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const validateFile = (file: File): string | null => {
    // Validate file type
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Invalid file type. Only PDF, JPG, and PNG files are allowed.';
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return 'File too large. Maximum size is 10MB.';
    }

    return null;
  };

  const handleFileUpload = useCallback(async (file: File) => {
    // Validate file
    const error = validateFile(file);
    if (error) {
      toast.error(error);
      return;
    }

    setIsUploading(true);

    try {
      // Upload file
      const uploadResult = await uploadDocument(file);
      const documentId = uploadResult.document_id;

      toast.success('File uploaded successfully!');

      // Trigger redaction progress tracking
      const redactionToast = toast.loading('Processing redaction...', {
        duration: Infinity,
      });

      try {
        // Wait for redaction to complete with progress updates
        const result = await waitForRedaction(documentId, (status) => {
          if (status === 'redacting') {
            toast.loading('Processing redaction...', {
              id: redactionToast,
            });
          }
        });

        if (result.success) {
          toast.success('Redaction complete! Redirecting to review...', {
            id: redactionToast,
            duration: 2000,
          });

          // Refresh document list
          onUploadComplete?.();

          // Redirect to approval page after a short delay
          setTimeout(() => {
            router.push(`/approval/${documentId}`);
          }, 1500);
        } else {
          toast.error(result.error || 'Redaction failed', {
            id: redactionToast,
            duration: 5000,
          });
        }
      } catch (redactionError) {
        const errorMessage = redactionError instanceof Error
          ? redactionError.message
          : 'Redaction processing failed';
        toast.error(errorMessage, {
          id: redactionToast,
          duration: 5000,
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      toast.error(errorMessage);
    } finally {
      setIsUploading(false);
    }
  }, [onUploadComplete]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!isUploading) {
      setIsDragging(true);
    }
  }, [isUploading]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (isUploading) return;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [isUploading, handleFileUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (isUploading) return;

    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  }, [isUploading, handleFileUpload]);

  return (
    <div
      className={cn(
        'relative border-2 border-dashed rounded-2xl p-16 transition-all duration-200 min-h-[280px] flex flex-col items-center justify-center',
        isUploading
          ? 'border-border bg-muted/20 cursor-not-allowed'
          : isDragging
          ? 'border-primary bg-primary/5 cursor-pointer'
          : 'border-border hover:border-primary/50 hover:bg-muted/30 cursor-pointer',
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        accept=".pdf,.jpg,.jpeg,.png"
        onChange={handleFileSelect}
        disabled={isUploading}
      />

      <div className="flex flex-col items-center text-center pointer-events-none">
        <div className={cn(
          'w-20 h-20 rounded-2xl flex items-center justify-center mb-6 transition-colors duration-200',
          isUploading
            ? 'bg-primary/10'
            : isDragging
            ? 'bg-primary/10'
            : 'bg-muted'
        )}>
          {isUploading ? (
            <Loader2 className="w-10 h-10 text-primary animate-spin" />
          ) : isDragging ? (
            <Upload className="w-10 h-10 text-primary" />
          ) : (
            <FileText className="w-10 h-10 text-muted-foreground" />
          )}
        </div>

        <h3 className="text-xl font-semibold text-foreground mb-2">
          {isUploading
            ? 'Uploading...'
            : isDragging
            ? 'Drop to upload'
            : 'Drop files to upload'}
        </h3>

        <p className="text-muted-foreground mb-4">
          {isUploading
            ? 'Please wait while your file is being uploaded'
            : 'or click to browse from your computer'}
        </p>

        <p className="text-sm text-muted-foreground/70">
          PDF, JPG, PNG • Maximum 10MB per file
        </p>
      </div>
    </div>
  );
}

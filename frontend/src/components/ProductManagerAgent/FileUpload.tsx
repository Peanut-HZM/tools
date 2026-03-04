import React, { useState, useCallback, useRef } from 'react';

interface FileUploadProps {
  conversationId: string;
  onUploadComplete?: (result: any) => void;
  onUploadError?: (error: string) => void;
  disabled?: boolean;
}

interface UploadState {
  isDragging: boolean;
  isUploading: boolean;
  progress: number;
  error: string | null;
  success: boolean;
}

const ACCEPTED_FILES = '.md,.docx,.doc,.pdf';
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const FileUpload: React.FC<FileUploadProps> = ({
  conversationId,
  onUploadComplete,
  onUploadError,
  disabled = false,
}) => {
  const [state, setState] = useState<UploadState>({
    isDragging: false,
    isUploading: false,
    progress: 0,
  } as UploadState);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    // Check file type
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_FILES.includes(fileExt)) {
      return `不支持的文件格式 "${fileExt}"。支持：Markdown, Word, PDF`;
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `文件过大 (${(file.size / 1024 / 1024).toFixed(2)}MB)。最大支持 10MB`;
    }

    return null;
  };

  const handleUpload = useCallback(async (file: File) => {
    const error = validateFile(file);
    if (error) {
      setState(prev => ({ ...prev, error, success: false }));
      onUploadError?.(error);
      return;
    }

    setState(prev => ({ 
      ...prev, 
      isUploading: true, 
      progress: 0,
      error: null,
      success: false 
    }));

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90)
        }));
      }, 200);

      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL || '/api/v1'}/messages/upload?conversation_id=${conversationId}`,
        {
          method: 'POST',
          body: formData,
          headers: {
            // Don't set Content-Type - browser will set it with boundary
          }
        }
      );

      clearInterval(progressInterval);
      setState(prev => ({ ...prev, progress: 100 }));

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上传失败');
      }

      const result = await response.json();
      
      setState(prev => ({
        ...prev,
        isUploading: false,
        progress: 100,
        success: true
      }));

      onUploadComplete?.(result);

      // Reset success state after 3 seconds
      setTimeout(() => {
        setState(prev => ({ ...prev, success: false }));
      }, 3000);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '上传失败';
      setState(prev => ({
        ...prev,
        isUploading: false,
        error: errorMessage,
        success: false
      }));
      onUploadError?.(errorMessage);
    }
  }, [conversationId, onUploadComplete, onUploadError]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setState(prev => ({ ...prev, isDragging: true }));
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setState(prev => ({ ...prev, isDragging: false }));
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setState(prev => ({ ...prev, isDragging: false }));

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
  }, [disabled, handleUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
    // Reset input value to allow selecting same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [handleUpload]);

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleButtonClick}
        className={`
          relative border-2 border-dashed rounded-lg p-6 cursor-pointer
          transition-all duration-200 ease-in-out
          ${state.isDragging 
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILES}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />

        <div className="text-center">
          {/* Upload Icon */}
          <div className="mx-auto h-12 w-12 text-gray-400">
            {state.isUploading ? (
              <svg className="animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
          </div>

          {/* Text */}
          <div className="mt-4">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {state.isUploading ? (
                <span>上传中... {state.progress}%</span>
              ) : state.isDragging ? (
                <span className="text-blue-600 dark:text-blue-400">松开以上传文件</span>
              ) : (
                <span>拖拽文件到此处，或<span className="text-blue-600 dark:text-blue-400">点击选择</span></span>
              )}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              支持 Markdown (.md), Word (.docx), PDF (.pdf) | 最大 10MB
            </p>
          </div>

          {/* Progress Bar */}
          {state.isUploading && (
            <div className="mt-4 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-200"
                style={{ width: `${state.progress}%` }}
              />
            </div>
          )}

          {/* Success Message */}
          {state.success && (
            <div className="mt-4 p-2 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded">
              <svg className="inline w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              上传成功！
            </div>
          )}

          {/* Error Message */}
          {state.error && (
            <div className="mt-4 p-2 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 rounded">
              <svg className="inline w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              {state.error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileUpload;

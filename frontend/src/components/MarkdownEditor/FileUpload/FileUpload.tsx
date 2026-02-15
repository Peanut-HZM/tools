import { useState, useRef, useCallback } from 'react';
import { uploadMarkdownToOss, readMarkdownFromOss } from '../../../api/markdownEditorApi';
import { fileUploadService } from '../../../services/fileUploadService';
import { useFileStore } from '../../../stores/fileStore';
import './FileUpload.css';

interface FileUploadProps {
  onFileUploaded?: (content: string, filename: string, filePath: string) => void;
  onError?: (error: string) => void;
  onUploadComplete?: () => void;
}

export default function FileUpload({ onFileUploaded, onError, onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { refreshOssFiles } = useFileStore();

  const handleFile = useCallback(async (file: File) => {
    const validation = fileUploadService.validateFile(file);
    if (!validation.valid) {
      onError?.(validation.error || 'Invalid file');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      const uploadResult = await fileUploadService.uploadFile(file, {
        onProgress: (progress) => {
          setUploadProgress(progress);
        },
      });
      
      const readResult = await readMarkdownFromOss(uploadResult.file_path);
      await refreshOssFiles();
      
      onFileUploaded?.(readResult.content, uploadResult.filename, uploadResult.file_path);
      onUploadComplete?.();
    } catch (error) {
      onError?.(error instanceof Error ? error.message : '上传失败');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  }, [onFileUploaded, onError, onUploadComplete, refreshOssFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [handleFile]);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div
      className={`file-upload-container ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".md,.markdown,.txt"
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
      />
      
      {isUploading ? (
        <div className="upload-status">
          <div className="spinner"></div>
          <span>上传中... {uploadProgress}%</span>
          {uploadProgress > 0 && (
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
            </div>
          )}
        </div>
      ) : (
        <div className="upload-content">
          <div className="upload-icon">
            <svg viewBox="0 0 1024 1024" width="48" height="48">
              <path
                fill="currentColor"
                d="M854.6 288.7L639.4 73.4c-6-6-14.2-9.4-22.7-9.4H192c-17.7 0-32 14.3-32 32v832c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32V311.3c0-8.5-3.4-16.7-9.4-22.6zM602 137.8L790.2 326H602V137.8zM792 888H232V136h302v216a42 42 0 0 0 42 42h216v494z"
              />
            </svg>
          </div>
          <div className="upload-text">
            <p className="upload-title">点击或拖拽文件到此处上传</p>
            <p className="upload-hint">支持 .md, .markdown, .txt 格式</p>
          </div>
        </div>
      )}
    </div>
  );
}

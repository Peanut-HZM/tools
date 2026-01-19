import { useState, useRef, useCallback } from 'react';
import { uploadMarkdownToOss, readMarkdownFromOss, OssUploadMarkdownResponse } from '../../../api/markdownEditorApi';
import './FileUpload.css';

interface FileUploadProps {
  onFileUploaded: (content: string, filename: string, filePath: string) => void;
  onError?: (error: string) => void;
}

export default function FileUpload({ onFileUploaded, onError }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    // Validate file type
    const allowedExtensions = ['.md', '.markdown', '.txt'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
      onError?.('只支持上传 .md, .markdown, .txt 格式的文件');
      return;
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      onError?.('文件大小不能超过 10MB');
      return;
    }

    setIsUploading(true);
    try {
      // Upload to OSS
      const uploadResult: OssUploadMarkdownResponse = await uploadMarkdownToOss(file);
      
      // Read content from OSS
      const readResult = await readMarkdownFromOss(uploadResult.file_path);
      
      // Callback with content
      onFileUploaded(readResult.content, uploadResult.filename, uploadResult.file_path);
    } catch (error) {
      onError?.(error instanceof Error ? error.message : '上传失败');
    } finally {
      setIsUploading(false);
    }
  }, [onFileUploaded, onError]);

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
          <span>上传中...</span>
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

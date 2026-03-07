/**
 * OSS 文件上传组件
 * 支持拖拽上传、进度显示、文件类型验证
 */
import React, { useState, useRef } from 'react';
import axios from 'axios';

interface OssUploaderProps {
  value?: string;
  onChange: (url: string) => void;
  accept?: string;
  maxSize?: number; // MB
  uploadPath?: string;
  disabled?: boolean;
  multiple?: boolean;
  onUploadStart?: () => void;
  onUploadComplete?: (url: string) => void;
  onUploadError?: (error: Error) => void;
}

interface UploadFile {
  name: string;
  size: number;
  type: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  url?: string;
}

const OssUploader: React.FC<OssUploaderProps> = ({
  value,
  onChange,
  accept,
  maxSize = 10,
  uploadPath = 'course-images',
  disabled = false,
  multiple = false,
  onUploadStart,
  onUploadComplete,
  onUploadError,
}) => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [uploadFile, setUploadFile] = useState<UploadFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getUploadToken = async (filename: string, fileType: string): Promise<string> => {
    // TODO: 从后端获取 OSS 上传 token
    // 这里模拟返回 token
    const response = await axios.post('/api/oss/upload-token', {
      filename,
      file_type: fileType,
      path: uploadPath,
    });
    return response.data.upload_token;
  };

  const uploadToOss = async (file: File): Promise<string> => {
    const token = await getUploadToken(file.name, file.type);

    // TODO: 实现真实的 OSS 上传逻辑
    // 这里使用 FormData 上传
    const formData = new FormData();
    formData.append('file', file);
    formData.append('token', token);

    const uploadUrl = 'https://your-oss-bucket.oss-cn-shanghai.aliyuncs.com';

    const response = await axios.post(uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total!);
        setProgress(percentCompleted);
        setUploadFile((prev) => prev ? { ...prev, progress: percentCompleted } : null);
      },
    });

    // 返回文件 URL
    const fileUrl = `${uploadUrl}/${file.name}`;
    return fileUrl;
  };

  const validateFile = (file: File): string | null => {
    // 验证文件类型
    if (accept) {
      const acceptedTypes = accept.split(',').map((t) => t.trim());
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      const fileType = file.type;

      const isAccepted = acceptedTypes.some((type) => {
        if (type.startsWith('.')) {
          return fileExtension === type.toLowerCase();
        }
        if (type.endsWith('/*')) {
          return fileType.startsWith(type.slice(0, -2));
        }
        return fileType === type;
      });

      if (!isAccepted) {
        return `不支持的文件类型：${fileExtension || file.type}`;
      }
    }

    // 验证文件大小
    if (file.size > maxSize * 1024 * 1024) {
      return `文件大小超过限制 (${maxSize}MB)`;
    }

    return null;
  };

  const handleUpload = async (file: File) => {
    const error = validateFile(file);
    if (error) {
      setUploadFile({
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 0,
        status: 'error',
        error,
      });
      onUploadError?.(new Error(error));
      return;
    }

    setUploading(true);
    setProgress(0);
    onUploadStart?.();

    setUploadFile({
      name: file.name,
      size: file.size,
      type: file.type,
      progress: 0,
      status: 'uploading',
    });

    try {
      const url = await uploadToOss(file);
      setUploadFile({
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 100,
        status: 'success',
        url,
      });
      onChange(url);
      onUploadComplete?.(url);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '上传失败';
      setUploadFile((prev) =>
        prev ? { ...prev, status: 'error', error: errorMessage } : null
      );
      onUploadError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          dragOver
            ? 'border-cyan-500 bg-cyan-500/10'
            : disabled
            ? 'border-slate-700 bg-slate-800/30 cursor-not-allowed'
            : 'border-slate-600 hover:border-cyan-500/50 hover:bg-slate-700/30'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />

        {uploading ? (
          <div className="space-y-3">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400 mx-auto"></div>
            <p className="text-slate-300">正在上传...</p>
            {uploadFile && (
              <div className="max-w-md mx-auto">
                <div className="flex items-center justify-between text-sm text-slate-400 mb-1">
                  <span className="truncate">{uploadFile.name}</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ) : value ? (
          <div className="space-y-3">
            <div className="text-green-400 text-4xl mb-2">
              <i className="fas fa-check-circle"></i>
            </div>
            <p className="text-white font-medium">上传成功</p>
            {uploadFile && (
              <p className="text-slate-400 text-sm">
                {uploadFile.name} ({formatFileSize(uploadFile.size)})
              </p>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleClick();
              }}
              className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors text-sm"
            >
              重新上传
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-cyan-400 text-5xl mb-4">
              <i className="fas fa-cloud-upload-alt"></i>
            </div>
            <p className="text-white font-medium">点击或拖拽文件到此处上传</p>
            <p className="text-slate-400 text-sm">
              支持 {accept || '所有文件'}，最大 {maxSize}MB
            </p>
          </div>
        )}
      </div>

      {/* File Preview */}
      {value && !uploading && (
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 flex-1 min-w-0">
              <div className="w-10 h-10 bg-cyan-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                <i className="fas fa-file text-cyan-400"></i>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium truncate">{value.split('/').pop()}</p>
                <p className="text-slate-400 text-sm">{value}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <a
                href={value}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                title="查看文件"
              >
                <i className="fas fa-external-link-alt text-slate-400"></i>
              </a>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  navigator.clipboard.writeText(value);
                }}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                title="复制链接"
              >
                <i className="fas fa-copy text-slate-400"></i>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {uploadFile?.status === 'error' && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <div className="flex items-center space-x-2 text-red-400">
            <i className="fas fa-exclamation-circle"></i>
            <span className="font-medium">{uploadFile.error}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default OssUploader;

/**
 * 文件预览模态框
 */
import React from 'react';
import { CrossFile } from '../../../services/crossShare';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  ImageViewer,
  VideoViewer,
  AudioViewer,
  MarkdownViewer,
  PdfViewer,
  ExcelViewer,
  JsonViewer,
  TextViewer,
  UnsupportedViewer,
} from './preview';
import { getViewerType } from './preview/types';

interface FilePreviewModalProps {
  /** 当前预览的文件 */
  file: CrossFile | null;
  /** 文件签名 URL */
  previewUrl: string | null;
  /** 是否打开 */
  isOpen: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 下载回调 */
  onDownload: () => void;
}

export const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  file,
  previewUrl,
  isOpen,
  onClose,
  onDownload,
}) => {
  if (!isOpen || !file || !previewUrl) {
    return null;
  }

  const viewerType = getViewerType(file);

  const renderViewer = () => {
    const props = {
      url: previewUrl,
      fileName: file.file_name,
      fileSize: file.file_size,
      fileId: file.id,
    };

    switch (viewerType) {
      case 'ImageViewer':
        return <ImageViewer {...props} />;
      case 'VideoViewer':
        return <VideoViewer {...props} />;
      case 'AudioViewer':
        return <AudioViewer {...props} />;
      case 'MarkdownViewer':
        return <MarkdownViewer {...props} />;
      case 'PdfViewer':
        return <PdfViewer {...props} />;
      case 'ExcelViewer':
        return <ExcelViewer {...props} />;
      case 'JsonViewer':
        return <JsonViewer {...props} />;
      case 'TextViewer':
        return <TextViewer {...props} />;
      default:
        return <UnsupportedViewer {...props} />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/70"
        onClick={onClose}
      />

      {/* 模态框内容 */}
      <Card className="relative w-[90vw] h-[90vh] shadow-lg overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">
              {viewerType === 'ImageViewer' && '🖼️'}
              {viewerType === 'VideoViewer' && '🎬'}
              {viewerType === 'AudioViewer' && '🎵'}
              {viewerType === 'MarkdownViewer' && '📝'}
              {viewerType === 'PdfViewer' && '📕'}
              {viewerType === 'ExcelViewer' && '📊'}
              {viewerType === 'JsonViewer' && '📋'}
              {viewerType === 'TextViewer' && '📄'}
              {viewerType === 'UnsupportedViewer' && '📎'}
            </span>
            <span className="text-lg font-semibold text-ink truncate max-w-md">
              {file.file_name}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <Button
              size="sm"
              variant="default"
              onClick={onDownload}
              className="text-white"
            >
              ⬇️ 下载
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={onClose}
            >
              ✕
            </Button>
          </div>
        </div>

        {/* 预览内容区域 */}
        <div className="flex-1 overflow-hidden">
          {renderViewer()}
        </div>

        {/* 底部信息栏 */}
        <div className="flex-shrink-0 px-6 py-3 border-t border-border bg-surface-1">
          <div className="flex items-center justify-between text-sm text-ink-muted">
            <span>
              文件大小：{(file.file_size / 1024).toFixed(2)} KB
              {file.file_size > 1024 * 1024 && ` (${(file.file_size / 1024 / 1024).toFixed(2)} MB)`}
            </span>
            <span>
              上传时间：{new Date(file.created_at).toLocaleString('zh-CN')}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
};

/**
 * 不支持的预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const UnsupportedViewer: React.FC<PreviewProps> = ({ fileName, fileSize }) => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center text-ink-muted bg-surface-1">
      <div className="text-6xl mb-4">📄</div>
      <div className="text-xl text-ink-muted mb-2">暂不支持预览此文件类型</div>
      <div className="text-sm text-ink-faint">{fileName}</div>
      <div className="text-xs text-ink-faint mt-1">{fileSize} bytes</div>
      <div className="mt-6 text-ink-faint">请下载后查看</div>
    </div>
  );
};

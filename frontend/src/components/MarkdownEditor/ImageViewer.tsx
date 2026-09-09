/**
 * ImageViewer - 图片文件查看器
 *
 * 显示 base64 编码的图片数据，支持缩放控制。
 * content 接收 base64 编码的图片数据（来自 FileRawContent.data）。
 */
import React, { useState } from 'react';

/** ImageViewer 组件接口 */
interface ImageViewerProps {
  /** base64 编码的图片数据（来自 FileRawContent.data） */
  content: string | null;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

const ImageViewer: React.FC<ImageViewerProps> = ({ content, fileName }) => {
  const [zoom, setZoom] = useState(1);

  if (!content) {
    return (
      <div className="flex items-center justify-center h-full text-ink-muted">
        <div className="text-center">
          <div className="text-lg mb-2">无图片内容</div>
        </div>
      </div>
    );
  }

  const imageData = `data:image/*;base64,${content}`;

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：显示文件名 + 缩放控件 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">
          {fileName || '图片'}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(0.1, z - 0.1))}
            className="px-2 py-1 text-sm rounded bg-surface-2 hover:bg-surface-3"
          >
            缩小
          </button>
          <span className="text-sm text-ink min-w-[60px] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(5, z + 0.1))}
            className="px-2 py-1 text-sm rounded bg-surface-2 hover:bg-surface-3"
          >
            放大
          </button>
          <button
            onClick={() => setZoom(1)}
            className="px-2 py-1 text-sm rounded bg-surface-2 hover:bg-surface-3"
          >
            重置
          </button>
        </div>
      </div>

      {/* 图片显示区域 */}
      <div className="flex-1 overflow-auto bg-surface-3 flex items-center justify-center p-4">
        <img
          src={imageData}
          alt={fileName || '图片'}
          style={{ transform: `scale(${zoom})`, transition: 'transform 0.2s' }}
          className="max-w-full max-h-full object-contain"
        />
      </div>
    </div>
  );
};

export default ImageViewer;

/**
 * PptxViewer - PowerPoint 文件查看器
 *
 * 两条渲染路径（由后端 /files/pptx-preview 自动选择）：
 * 1. PDF 高保真路径（LibreOffice 可用）：iframe 原生渲染 slide-pdf 接口返回的 PDF，
 *    保留主题/母版/形状/SmartArt 视觉效果，支持 .ppt 和 .pptx
 * 2. HTML 降级路径（无 LibreOffice）：python-pptx 生成的自包含 HTML，
 *    sandbox iframe 渲染，仅支持 .pptx，视觉效果有损失
 */
import React, { useState, useEffect, useRef } from 'react';
import { getPptxPreview, getSlidePdfUrl } from '../../api/markdownEditorApi';

/** PptxViewer 组件接口 */
interface PptxViewerProps {
  /** 文件路径（用于调用后端转换接口） */
  filePath: string;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

type PreviewMode = 'loading' | 'pdf' | 'html' | 'error';

const PptxViewer: React.FC<PptxViewerProps> = ({ filePath, fileName }) => {
  const [mode, setMode] = useState<PreviewMode>('loading');
  const [html, setHtml] = useState('');
  const [slideCount, setSlideCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let cancelled = false;
    let blobUrl: string | null = null;

    const loadPreview = async () => {
      setMode('loading');
      setError(null);
      try {
        const data = await getPptxPreview(filePath);
        if (cancelled) return;

        if (data.type === 'pdf') {
          // 高保真路径：iframe 原生渲染 PDF（URL 携带 token）
          setMode('pdf');
        } else {
          // 降级路径：自包含 HTML 用 blob URL + sandbox 渲染
          blobUrl = URL.createObjectURL(new Blob([data.html], { type: 'text/html' }));
          if (iframeRef.current) {
            iframeRef.current.src = blobUrl;
          }
          setHtml(data.html);
          setSlideCount(data.slide_count);
          setMode('html');
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : '未知错误');
        setMode('error');
      }
    };

    loadPreview();

    return () => {
      cancelled = true;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [filePath]);

  const displayName = fileName || 'PowerPoint 演示文稿';

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：文件名 + 幻灯片页数（HTML 路径时） */}
      <div className="flex items-center px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">
          {displayName}
          {mode === 'html' && slideCount > 0 && (
            <span className="ml-2">（共 {slideCount} 页）</span>
          )}
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden bg-surface-3 relative">
        {mode === 'error' ? (
          <div className="text-center text-danger py-8 px-4">
            {error}
          </div>
        ) : mode === 'pdf' ? (
          /* PDF 路径：浏览器原生 PDF 查看器（无 sandbox，PDF 插件需要完整权限） */
          <iframe
            src={getSlidePdfUrl(filePath)}
            className="w-full h-full border-0"
            title="PPTX 预览"
            style={{ minHeight: '100%' }}
          />
        ) : (
          /* HTML 路径：sandbox iframe 渲染 blob URL */
          <iframe
            ref={iframeRef}
            sandbox="allow-scripts"
            className="w-full h-full border-0"
            title="PPTX 预览"
            style={{ minHeight: '100%' }}
          />
        )}
        {mode === 'loading' && (
          <div className="absolute inset-0 flex items-center justify-center text-ink-muted">
            加载 PPTX 中...
          </div>
        )}
      </div>
    </div>
  );
};

export default PptxViewer;

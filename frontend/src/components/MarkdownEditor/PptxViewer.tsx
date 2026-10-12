/**
 * PptxViewer - PowerPoint 文件查看器
 *
 * 通过后端 /files/pptx-preview 接口将 .pptx 转换为自包含 HTML，
 * 在 sandbox iframe（blob URL）中渲染。支持文本/图片/表格/组合形状，
 * 按幻灯片分页展示。
 *
 * 旧版 .ppt 二进制格式无法解析，接口返回错误时展示提示。
 */
import React, { useState, useEffect, useRef } from 'react';
import { getPptxPreview } from '../../api/markdownEditorApi';

/** PptxViewer 组件接口 */
interface PptxViewerProps {
  /** 文件路径（用于调用后端转换接口） */
  filePath: string;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

const PptxViewer: React.FC<PptxViewerProps> = ({ filePath, fileName }) => {
  const [html, setHtml] = useState('');
  const [slideCount, setSlideCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let cancelled = false;
    let blobUrl: string | null = null;

    const loadPreview = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getPptxPreview(filePath);
        if (cancelled) return;
        blobUrl = URL.createObjectURL(new Blob([data.html], { type: 'text/html' }));
        if (iframeRef.current) {
          iframeRef.current.src = blobUrl;
        }
        setHtml(data.html);
        setSlideCount(data.slide_count);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : '未知错误');
        setHtml('');
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
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

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：文件名 + 幻灯片页数 */}
      <div className="flex items-center px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">
          {fileName || 'PowerPoint 演示文稿'}
          {slideCount > 0 && <span className="ml-2">（共 {slideCount} 页）</span>}
        </div>
      </div>

      {/* PPTX 内容区域 */}
      <div className="flex-1 overflow-hidden bg-surface-3">
        {error ? (
          <div className="text-center text-danger py-8 px-4">
            {error}
          </div>
        ) : (
          <iframe
            ref={iframeRef}
            sandbox="allow-scripts"
            className="w-full h-full border-0"
            title="PPTX 预览"
            style={{ minHeight: '100%' }}
          />
        )}
        {loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center text-ink-muted">
            加载 PPTX 中...
          </div>
        )}
      </div>
    </div>
  );
};

export default PptxViewer;

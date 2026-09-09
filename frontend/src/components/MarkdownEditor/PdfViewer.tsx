/**
 * PdfViewer - PDF 文件查看器
 *
 * 使用 react-pdf 渲染 PDF 文档，支持翻页。
 * content 接收 base64 编码的 PDF 数据（来自 FileRawContent.data）。
 */
import React, { useState, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// 设置 pdf.js worker 路径（使用 CDN，避免本地打包 worker 文件）
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

/** PdfViewer 组件接口 */
interface PdfViewerProps {
  /** base64 编码的 PDF 数据（来自 FileRawContent.data） */
  content: string | null;
  /** 文件名（可选，显示在工具栏） */
  fileName?: string;
}

const PdfViewer: React.FC<PdfViewerProps> = ({ content, fileName }) => {
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [error, setError] = useState<string | null>(null);

  // 将 base64 转换为 data URL，使用 useMemo 避免每次渲染重建
  const pdfData = useMemo(
    () => (content ? `data:application/pdf;base64,${content}` : null),
    [content]
  );

  /** PDF 文档加载成功回调 */
  const onDocumentLoadSuccess = ({ numPages: total }: { numPages: number }) => {
    setNumPages(total);
    setError(null);
  };

  /** PDF 文档加载失败回调 */
  const onDocumentLoadError = (err: Error) => {
    setError(`PDF 加载失败：${err.message}`);
  };

  // 无内容时显示占位提示
  if (!content) {
    return (
      <div className="flex items-center justify-center h-full text-ink-muted">
        <div className="text-center">
          <div className="text-lg mb-2">无 PDF 内容</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏：显示文件名 + 翻页控件 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-1">
        <div className="text-sm text-ink-muted">{fileName || 'PDF 文档'}</div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
            disabled={pageNumber <= 1}
            className="px-2 py-1 text-sm rounded bg-surface-2 hover:bg-surface-3 disabled:opacity-50"
          >
            上一页
          </button>
          <span className="text-sm text-ink">
            {pageNumber} / {numPages || '?'}
          </span>
          <button
            onClick={() => setPageNumber((p) => Math.min(numPages, p + 1))}
            disabled={pageNumber >= numPages}
            className="px-2 py-1 text-sm rounded bg-surface-2 hover:bg-surface-3 disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      </div>

      {/* PDF 内容区域：支持滚动 */}
      <div className="flex-1 overflow-auto bg-surface-3 p-4">
        {error ? (
          <div className="text-center text-danger py-8">{error}</div>
        ) : (
          <Document
            file={pdfData}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="text-center text-ink-muted py-8">加载 PDF 中...</div>
            }
          >
            <Page pageNumber={pageNumber} width={800} />
          </Document>
        )}
      </div>
    </div>
  );
};

export default PdfViewer;

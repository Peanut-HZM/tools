/**
 * PDF 预览器
 */
import React from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { PreviewProps } from './types';
import { Button } from "@/components/ui/Button";

// 设置 PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export const PdfViewer: React.FC<PreviewProps> = ({ url }) => {
  const [numPages, setNumPages] = React.useState<number>(0);
  const [pageNumber, setPageNumber] = React.useState<number>(1);
  const [error, setError] = React.useState(false);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1);
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-accent-danger">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>PDF 加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center bg-canvas overflow-auto">
      <div className="sticky top-0 z-10 flex items-center gap-4 bg-surface-1 px-4 py-2 border-b border-border">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setPageNumber(prev => Math.max(prev - 1, 1))}
          disabled={pageNumber <= 1}
        >
          上一页
        </Button>
        <span className="text-ink">
          第 {pageNumber} 页 / 共 {numPages} 页
        </span>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setPageNumber(prev => Math.min(prev + 1, numPages))}
          disabled={pageNumber >= numPages}
        >
          下一页
        </Button>
      </div>
      <div className="flex-1 flex items-center justify-center p-4">
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={() => setError(true)}
          loading={
            <div className="text-ink-muted">加载 PDF 中...</div>
          }
          error={null}
        >
          <Page
            pageNumber={pageNumber}
            width={Math.min(800, window.innerWidth - 100)}
            renderAnnotationLayer={true}
            renderTextLayer={true}
          />
        </Document>
      </div>
    </div>
  );
};

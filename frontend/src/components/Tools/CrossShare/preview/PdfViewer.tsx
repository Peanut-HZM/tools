/**
 * PDF 预览器
 */
import React from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { PreviewProps } from './types';

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
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>PDF 加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center bg-slate-900 overflow-auto">
      <div className="sticky top-0 z-10 flex items-center gap-4 bg-slate-800 px-4 py-2 border-b border-slate-700">
        <button
          onClick={() => setPageNumber(prev => Math.max(prev - 1, 1))}
          disabled={pageNumber <= 1}
          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200"
        >
          上一页
        </button>
        <span className="text-slate-200">
          第 {pageNumber} 页 / 共 {numPages} 页
        </span>
        <button
          onClick={() => setPageNumber(prev => Math.min(prev + 1, numPages))}
          disabled={pageNumber >= numPages}
          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200"
        >
          下一页
        </button>
      </div>
      <div className="flex-1 flex items-center justify-center p-4">
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={() => setError(true)}
          loading={
            <div className="text-slate-400">加载 PDF 中...</div>
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

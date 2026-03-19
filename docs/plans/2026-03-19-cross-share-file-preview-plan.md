# CrossShare File Preview Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 CrossShare 文件管理添加预览功能，支持图片、视频、音频、Markdown、PDF、Excel、JSON、文本等格式的在线预览

**Architecture:**
- 纯前端解析方案，通过 OSS 签名 URL 加载文件
- 模态框预览交互，根据文件类型动态选择预览器组件
- 新增预览模态框和各类预览器子组件

**Tech Stack:**
- React 18, TypeScript, Tailwind CSS
- react-markdown, remark-gfm, react-pdf, xlsx, react-player, react-json-view

---

## Task 1: 安装依赖包

**Files:**
- Modify: `frontend/package.json`

**Steps:**

### Step 1: 安装预览相关依赖

```bash
cd frontend
npm install react-markdown remark-gfm react-pdf xlsx react-player react-json-view
```

Expected: Packages installed successfully

### Step 2: 验证依赖安装

```bash
cd frontend
npm list react-markdown react-pdf xlsx react-player react-json-view
```

Expected: All packages listed with versions

### Step 3: 提交

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "deps: 安装文件预览相关依赖包"
```

---

## Task 2: 创建预览器组件目录和基础类型

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/index.ts`
- Create: `frontend/src/components/Tools/CrossShare/preview/types.ts`

### Step 1: 创建类型定义文件

**File:** `frontend/src/components/Tools/CrossShare/preview/types.ts`

```typescript
/**
 * 预览器类型枚举
 */
export type ViewerType =
  | 'ImageViewer'
  | 'VideoViewer'
  | 'AudioViewer'
  | 'MarkdownViewer'
  | 'PdfViewer'
  | 'ExcelViewer'
  | 'JsonViewer'
  | 'TextViewer';

/**
 * 预览器属性接口
 */
export interface ViewerProps {
  /** OSS 签名后的文件 URL */
  fileUrl: string;
  /** 文件名 */
  fileName: string;
  /** 文件大小（字节） */
  fileSize?: number;
}

/**
 * 文件扩展名到预览器类型的映射表
 */
export const EXTENSION_TO_VIEWER: Record<string, ViewerType> = {
  // 图片
  jpg: 'ImageViewer',
  jpeg: 'ImageViewer',
  png: 'ImageViewer',
  gif: 'ImageViewer',
  webp: 'ImageViewer',
  svg: 'ImageViewer',
  bmp: 'ImageViewer',
  // 视频
  mp4: 'VideoViewer',
  webm: 'VideoViewer',
  avi: 'VideoViewer',
  mov: 'VideoViewer',
  mkv: 'VideoViewer',
  // 音频
  mp3: 'AudioViewer',
  wav: 'AudioViewer',
  aac: 'AudioViewer',
  ogg: 'AudioViewer',
  flac: 'AudioViewer',
  // 文档
  md: 'MarkdownViewer',
  markdown: 'MarkdownViewer',
  pdf: 'PdfViewer',
  xlsx: 'ExcelViewer',
  xls: 'ExcelViewer',
  csv: 'ExcelViewer',
  json: 'JsonViewer',
  // 文本（降级）
  txt: 'TextViewer',
  doc: 'TextViewer',
  docx: 'TextViewer',
};

/**
 * 根据文件类型和扩展名获取预览器类型
 */
export function getViewerType(fileType: string, fileName: string): ViewerType {
  const ext = fileName.toLowerCase().split('.').pop() || '';

  // 根据 FileType 枚举快速判断大类
  switch (fileType) {
    case 'image':
      return 'ImageViewer';
    case 'video':
      return 'VideoViewer';
    case 'audio':
      return 'AudioViewer';
    case 'text':
      if (ext === 'md' || ext === 'markdown') return 'MarkdownViewer';
      if (ext === 'json') return 'JsonViewer';
      return 'TextViewer';
    case 'document':
      if (ext === 'pdf') return 'PdfViewer';
      if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') return 'ExcelViewer';
      return 'TextViewer'; // Word 等降级为文本
    default:
      // 根据扩展名判断
      return EXTENSION_TO_VIEWER[ext] || 'TextViewer';
  }
}
```

### Step 2: 创建统一导出文件

**File:** `frontend/src/components/Tools/CrossShare/preview/index.ts`

```typescript
// 预览器类型和工具函数
export * from './types';

// 预览器组件（懒加载）
export { ImageViewer } from './ImageViewer';
export { VideoViewer } from './VideoViewer';
export { AudioViewer } from './AudioViewer';
export { MarkdownViewer } from './MarkdownViewer';
export { PdfViewer } from './PdfViewer';
export { ExcelViewer } from './ExcelViewer';
export { JsonViewer } from './JsonViewer';
export { TextViewer } from './TextViewer';
```

### Step 3: 验证类型定义

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/types.ts
```

Expected: No errors

### Step 4: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/
git commit -m "feat: 创建预览器类型定义和导出文件"
```

---

## Task 3: 创建图片预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/ImageViewer.tsx`

### Step 1: 创建图片预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/ImageViewer.tsx`

```typescript
import React, { useState } from 'react';
import { ViewerProps } from './types';

/**
 * 图片预览器
 * 支持缩放、拖拽、全屏查看
 */
export const ImageViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  const [scale, setScale] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleZoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
  const handleReset = () => {
    setScale(1);
    setError(null);
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center text-red-400">
          <div className="text-4xl mb-2">⚠️</div>
          <div>图片加载失败</div>
          <div className="text-sm text-slate-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate max-w-md">{fileName}</div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleZoomOut}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm"
            title="缩小"
          >
            🔍-
          </button>
          <span className="text-sm text-slate-300 w-12 text-center">{Math.round(scale * 100)}%</span>
          <button
            onClick={handleZoomIn}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm"
            title="放大"
          >
            🔍+
          </button>
          <button
            onClick={handleReset}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm"
            title="重置"
          >
            ↻
          </button>
        </div>
      </div>

      {/* 图片容器 */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-4">
        {isLoading && (
          <div className="text-slate-400">加载中...</div>
        )}
        <img
          src={fileUrl}
          alt={fileName}
          className={`max-w-full max-h-full object-contain transition-transform duration-200 ${isLoading ? 'hidden' : 'block'}`}
          style={{ transform: `scale(${scale})` }}
          onLoad={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false);
            setError('无法加载图片');
          }}
        />
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/ImageViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/ImageViewer.tsx
git commit -m "feat: 创建图片预览器组件"
```

---

## Task 4: 创建视频预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/VideoViewer.tsx`

### Step 1: 创建视频预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/VideoViewer.tsx`

```typescript
import React from 'react';
import ReactPlayer from 'react-player';
import { ViewerProps } from './types';

/**
 * 视频预览器
 * 支持 MP4, WebM, AVI, MOV, MKV 等格式
 */
export const VideoViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  return (
    <div className="flex flex-col h-full bg-slate-900">
      <div className="px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate">{fileName}</div>
      </div>
      <div className="flex-1 flex items-center justify-center p-4">
        <ReactPlayer
          url={fileUrl}
          width="100%"
          height="100%"
          controls
          playing={false}
          config={{
            file: {
              attributes: {
                crossOrigin: 'anonymous',
              },
            },
          }}
        />
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/VideoViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/VideoViewer.tsx
git commit -m "feat: 创建视频预览器组件"
```

---

## Task 5: 创建音频预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx`

### Step 1: 创建音频预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx`

```typescript
import React from 'react';
import ReactPlayer from 'react-player';
import { ViewerProps } from './types';

/**
 * 音频预览器
 * 支持 MP3, WAV, AAC, OGG, FLAC 等格式
 */
export const AudioViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  return (
    <div className="flex flex-col h-full bg-slate-900">
      <div className="px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate">{fileName}</div>
      </div>
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-6xl text-center mb-6">🎵</div>
          <ReactPlayer
            url={fileUrl}
            width="100%"
            controls
            playing={false}
            config={{
              file: {
                attributes: {
                  crossOrigin: 'anonymous',
                },
              },
            }}
          />
        </div>
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/AudioViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx
git commit -m "feat: 创建音频预览器组件"
```

---

## Task 6: 创建 Markdown 预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/MarkdownViewer.tsx`

### Step 1: 创建 Markdown 预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/MarkdownViewer.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ViewerProps } from './types';

/**
 * Markdown 预览器
 * 支持 GFM 语法（表格、任务列表等）
 */
export const MarkdownViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  const [content, setContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const text = await response.text();
        setContent(text);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchContent();
  }, [fileUrl]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-slate-400">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center text-red-400">
          <div className="text-4xl mb-2">⚠️</div>
          <div>Markdown 加载失败</div>
          <div className="text-sm text-slate-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      <div className="px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate">{fileName}</div>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <article className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </article>
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/MarkdownViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/MarkdownViewer.tsx
git commit -m "feat: 创建 Markdown 预览器组件"
```

---

## Task 7: 创建 PDF 预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/PdfViewer.tsx`

### Step 1: 创建 PDF 预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/PdfViewer.tsx`

```typescript
import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import { ViewerProps } from './types';

// 设置 PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/**
 * PDF 预览器
 * 支持多页、缩放
 */
export const PdfViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1);
    setIsLoading(false);
  }

  const handlePrevious = () => setPageNumber(prev => Math.max(prev - 1, 1));
  const handleNext = () => setPageNumber(prev => Math.min(prev + 1, numPages));
  const handleZoomIn = () => setScale(prev => Math.min(prev + 0.25, 2));
  const handleZoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-slate-400">加载 PDF...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center text-red-400">
          <div className="text-4xl mb-2">⚠️</div>
          <div>PDF 加载失败</div>
          <div className="text-sm text-slate-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate max-w-xs">{fileName}</div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handlePrevious}
            disabled={pageNumber <= 1}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm disabled:opacity-50"
          >
            ←
          </button>
          <span className="text-sm text-slate-300">
            {pageNumber} / {numPages}
          </span>
          <button
            onClick={handleNext}
            disabled={pageNumber >= numPages}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm disabled:opacity-50"
          >
            →
          </button>
          <div className="w-px h-4 bg-slate-600 mx-2" />
          <button
            onClick={handleZoomOut}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm"
          >
            🔍-
          </button>
          <span className="text-sm text-slate-300 w-12 text-center">{Math.round(scale * 100)}%</span>
          <button
            onClick={handleZoomIn}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-slate-200 text-sm"
          >
            🔍+
          </button>
        </div>
      </div>

      {/* PDF 内容 */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-slate-900">
        <div className="shadow-lg">
          <Document
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={(e) => {
              setError(e.message);
              setIsLoading(false);
            }}
            loading={<div className="text-slate-400">加载中...</div>}
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderAnnotationLayer={true}
              renderTextLayer={true}
            />
          </Document>
        </div>
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/PdfViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/PdfViewer.tsx
git commit -m "feat: 创建 PDF 预览器组件"
```

---

## Task 8: 创建 Excel 预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/ExcelViewer.tsx`

### Step 1: 创建 Excel 预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/ExcelViewer.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { ViewerProps } from './types';

/**
 * Excel 预览器
 * 支持 xlsx, xls, csv 格式
 */
export const ExcelViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  const [data, setData] = useState<unknown[][]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [currentSheet, setCurrentSheet] = useState<string>('');

  useEffect(() => {
    const fetchExcel = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const arrayBuffer = await response.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });

        setSheetNames(workbook.SheetNames);
        const firstSheet = workbook.SheetNames[0];
        setCurrentSheet(firstSheet);

        const worksheet = workbook.Sheets[firstSheet];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as unknown[][];
        setData(jsonData);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchExcel();
  }, [fileUrl]);

  const handleSheetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setCurrentSheet(e.target.value);
  };

  // 重新读取选中的 sheet
  useEffect(() => {
    if (!currentSheet || isLoading) return;

    const loadSheet = async () => {
      try {
        const response = await fetch(fileUrl);
        const arrayBuffer = await response.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        const worksheet = workbook.Sheets[currentSheet];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as unknown[][];
        setData(jsonData);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      }
    };

    loadSheet();
  }, [currentSheet]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-slate-400">加载 Excel...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center text-red-400">
          <div className="text-4xl mb-2">⚠️</div>
          <div>Excel 加载失败</div>
          <div className="text-sm text-slate-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate">{fileName}</div>
        {sheetNames.length > 1 && (
          <select
            value={currentSheet}
            onChange={handleSheetChange}
            className="px-2 py-1 bg-slate-700 border border-slate-600 rounded text-slate-200 text-sm"
          >
            {sheetNames.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        )}
      </div>

      {/* 表格内容 */}
      <div className="flex-1 overflow-auto p-4">
        <div className="inline-block min-w-full align-middle">
          <table className="min-w-full divide-y divide-slate-700 border border-slate-700">
            <tbody className="divide-y divide-slate-700">
              {data.map((row, rowIndex) => (
                <tr key={rowIndex} className={rowIndex === 0 ? 'bg-slate-800' : ''}>
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className="px-4 py-2 text-sm text-slate-200 whitespace-nowrap border-r border-slate-700"
                    >
                      {cell !== null && cell !== undefined ? String(cell) : ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/ExcelViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/ExcelViewer.tsx
git commit -m "feat: 创建 Excel 预览器组件"
```

---

## Task 9: 创建 JSON 预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/JsonViewer.tsx`

### Step 1: 创建 JSON 预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/JsonViewer.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import ReactJson from 'react-json-view';
import { ViewerProps } from './types';

/**
 * JSON 预览器
 * 支持语法高亮、折叠/展开
 */
export const JsonViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  const [data, setData] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJson = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const jsonData = await response.json();
        setData(jsonData);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchJson();
  }, [fileUrl]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-slate-400">加载 JSON...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center text-red-400">
          <div className="text-4xl mb-2">⚠️</div>
          <div>JSON 加载失败</div>
          <div className="text-sm text-slate-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      <div className="px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate">{fileName}</div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <ReactJson
          src={data as never}
          theme="monokai"
          collapsed={2}
          enableClipboard={true}
          displayDataTypes={true}
          displayObjectSize={true}
          name={false}
          style={{
            backgroundColor: 'transparent',
            fontSize: '14px',
          }}
        />
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/JsonViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/JsonViewer.tsx
git commit -m "feat: 创建 JSON 预览器组件"
```

---

## Task 10: 创建文本预览器

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/preview/TextViewer.tsx`

### Step 1: 创建文本预览器组件

**File:** `frontend/src/components/Tools/CrossShare/preview/TextViewer.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { ViewerProps } from './types';

/**
 * 文本预览器
 * 用于 TXT、Word（降级）等纯文本格式
 */
export const TextViewer: React.FC<ViewerProps> = ({ fileUrl, fileName }) => {
  const [content, setContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const text = await response.text();
        setContent(text);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchContent();
  }, [fileUrl]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-slate-400">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center text-red-400">
          <div className="text-4xl mb-2">⚠️</div>
          <div>文本加载失败</div>
          <div className="text-sm text-slate-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      <div className="px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="text-sm text-slate-300 truncate">{fileName}</div>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <pre className="text-slate-200 text-sm font-mono whitespace-pre-wrap break-words">
          {content}
        </pre>
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/preview/TextViewer.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/preview/TextViewer.tsx
git commit -m "feat: 创建文本预览器组件"
```

---

## Task 11: 创建预览模态框组件

**Files:**
- Create: `frontend/src/components/Tools/CrossShare/FilePreviewModal.tsx`

### Step 1: 创建预览模态框组件

**File:** `frontend/src/components/Tools/CrossShare/FilePreviewModal.tsx`

```typescript
import React from 'react';
import { CrossFile } from '../../../services/crossShare';
import { getViewerType } from './preview/types';
import {
  ImageViewer,
  VideoViewer,
  AudioViewer,
  MarkdownViewer,
  PdfViewer,
  ExcelViewer,
  JsonViewer,
  TextViewer,
} from './preview';

interface FilePreviewModalProps {
  file: CrossFile | null;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * 文件预览模态框
 */
export const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  file,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !file) {
    return null;
  }

  // 获取下载链接（用于预览）
  const getPreviewUrl = async (): Promise<string> => {
    // 这里需要调用 API 获取签名后的下载链接
    // 暂时使用一个简单的方式：直接返回，由子组件处理
    return file.oss_url || '';
  };

  const viewerType = getViewerType(file.file_type, file.file_name);

  const renderViewer = () => {
    // 注意：实际使用时需要通过 API 获取签名后的下载链接
    // 这里为了简化，直接使用 oss_key 构建一个示例链接
    const previewUrl = `/api/cross-share/files/${file.id}/download-url`; // 需要后端支持

    switch (viewerType) {
      case 'ImageViewer':
        return <ImageViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'VideoViewer':
        return <VideoViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'AudioViewer':
        return <AudioViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'MarkdownViewer':
        return <MarkdownViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'PdfViewer':
        return <PdfViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'ExcelViewer':
        return <ExcelViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'JsonViewer':
        return <JsonViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
      case 'TextViewer':
      default:
        return <TextViewer fileUrl={previewUrl} fileName={file.file_name} fileSize={file.file_size} />;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-6xl h-[85vh] flex flex-col overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-3 bg-slate-900 border-b border-slate-700">
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
            </span>
            <h3 className="text-lg font-semibold text-slate-100 truncate max-w-md">
              {file.file_name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors text-2xl"
            title="关闭"
          >
            ✕
          </button>
        </div>

        {/* 预览内容 */}
        <div className="flex-1 overflow-hidden">
          {renderViewer()}
        </div>

        {/* 底部信息 */}
        <div className="px-6 py-3 bg-slate-900 border-t border-slate-700 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            文件大小：{(file.file_size / 1024 / 1024).toFixed(2)} MB
          </div>
          <a
            href={`/api/cross-share/files/${file.id}/download`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            ⬇️ 下载原文件
          </a>
        </div>
      </div>
    </div>
  );
};
```

### Step 2: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/FilePreviewModal.tsx
```

Expected: No errors

### Step 3: 提交

```bash
git add frontend/src/components/Tools/CrossShare/FilePreviewModal.tsx
git commit -m "feat: 创建文件预览模态框组件"
```

---

## Task 12: 修改 FilePanel 添加预览按钮

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/FilePanel.tsx`

### Step 1: 修改导入

在文件顶部添加导入：

```typescript
import { FilePreviewModal } from './FilePreviewModal';
```

### Step 2: 添加状态

在组件内添加状态：

```typescript
const [previewFile, setPreviewFile] = useState<CrossFile | null>(null);
const [isPreviewOpen, setIsPreviewOpen] = useState(false);
```

### Step 3: 添加预览处理函数

```typescript
const handlePreview = async (file: CrossFile) => {
  try {
    // 这里可以先获取下载链接，然后在模态框中显示
    // 简化处理：直接打开模态框，由模态框内部获取链接
    setPreviewFile(file);
    setIsPreviewOpen(true);
  } catch (error) {
    console.error('Failed to open preview:', error);
  }
};
```

### Step 4: 在文件列表中添加预览按钮

修改文件列表中的按钮区域：

```typescript
<div className="flex items-center space-x-2">
  <button
    onClick={() => handlePreview(file)}
    className="px-3 py-1.5 text-sm bg-blue-900/30 hover:bg-blue-900/50 text-blue-400 rounded-lg transition-colors"
  >
    👁️ 预览
  </button>
  <button
    onClick={() => handleDownload(file)}
    className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
  >
    ⬇️ 下载
  </button>
  <button
    onClick={() => handleDelete(file.id)}
    className="px-3 py-1.5 text-sm bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded-lg transition-colors"
  >
    🗑️ 删除
  </button>
</div>
```

### Step 5: 在组件末尾添加模态框

```typescript
{/* 预览模态框 */}
<FilePreviewModal
  file={previewFile}
  isOpen={isPreviewOpen}
  onClose={() => {
    setIsPreviewOpen(false);
    setPreviewFile(null);
  }}
/>
```

### Step 6: 验证组件编译

```bash
cd frontend
npx tsc --noEmit src/components/Tools/CrossShare/FilePanel.tsx
```

Expected: No errors

### Step 7: 提交

```bash
git add frontend/src/components/Tools/CrossShare/FilePanel.tsx
git commit -m "feat: 在 FilePanel 中添加预览按钮和模态框"
```

---

## Task 13: 修改后端添加预览链接获取接口

**注意:** 实际上我们可以复用现有的下载链接接口，只需要前端正确处理即可。此任务简化为前端处理。

---

## Task 14: 完善预览链接获取逻辑

**Files:**
- Modify: `frontend/src/components/Tools/CrossShare/FilePreviewModal.tsx`
- Modify: `frontend/src/services/crossShare.ts`

### Step 1: 在 crossShare.ts 中添加获取预览链接方法

在 `fileApi` 中添加：

```typescript
/** 获取预览链接（用于模态框） */
getPreviewUrl: async (fileId: string): Promise<string> => {
  const response = await axios.post(`${API_BASE_URL}/files/${fileId}/download`, {}, {
    headers: getHeaders()
  });
  return response.data.download_url;
},
```

### Step 2: 修改 FilePreviewModal 使用新的 API

修改 `renderViewer` 函数，先获取预览链接：

```typescript
const [previewUrl, setPreviewUrl] = useState<string>('');

useEffect(() => {
  if (file) {
    fileApi.getPreviewUrl(file.id).then(setPreviewUrl);
  }
}, [file]);

// 然后在 renderViewer 中使用 previewUrl
```

### Step 3: 提交

```bash
git add frontend/src/services/crossShare.ts frontend/src/components/Tools/CrossShare/FilePreviewModal.tsx
git commit -m "feat: 添加预览链接获取逻辑"
```

---

## Task 15: 测试各类文件预览功能

**测试清单:**

### Step 1: 测试图片预览

- 上传 JPG、PNG、GIF 格式图片
- 验证预览显示正常
- 验证缩放功能

### Step 2: 测试视频预览

- 上传 MP4 格式视频
- 验证播放控制正常

### Step 3: 测试音频预览

- 上传 MP3 格式音频
- 验证播放控制正常

### Step 4: 测试 Markdown 预览

- 上传 .md 文件
- 验证渲染效果（含代码块、表格）

### Step 5: 测试 PDF 预览

- 上传 .pdf 文件
- 验证翻页、缩放功能

### Step 6: 测试 Excel 预览

- 上传 .xlsx 文件
- 验证表格显示、多工作表切换

### Step 7: 测试 JSON 预览

- 上传 .json 文件
- 验证语法高亮、折叠/展开

### Step 8: 测试文本预览

- 上传 .txt 文件
- 验证纯文本显示

### Step 9: 测试错误处理

- 上传损坏文件
- 验证错误提示

---

## 依赖关系

```
Task 1 (依赖包) → 所有组件任务
Task 2 (类型定义) → Task 3-12
Task 3-10 (预览器组件) → Task 11 (模态框)
Task 11 (模态框) → Task 12 (FilePanel 修改)
Task 12 → Task 14 (链接获取)
Task 14 → Task 15 (测试)
```

---

## 总结

共 15 个任务，预计完成时间：60-90 分钟

**核心文件清单:**
- `frontend/src/components/Tools/CrossShare/preview/types.ts`
- `frontend/src/components/Tools/CrossShare/preview/index.ts`
- `frontend/src/components/Tools/CrossShare/preview/ImageViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/VideoViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/AudioViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/MarkdownViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/PdfViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/ExcelViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/JsonViewer.tsx`
- `frontend/src/components/Tools/CrossShare/preview/TextViewer.tsx`
- `frontend/src/components/Tools/CrossShare/FilePreviewModal.tsx`
- `frontend/src/components/Tools/CrossShare/FilePanel.tsx` (修改)
- `frontend/src/services/crossShare.ts` (修改)

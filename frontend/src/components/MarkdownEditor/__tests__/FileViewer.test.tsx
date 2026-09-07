/**
 * FileViewer 路由组件测试
 *
 * 验证 FileViewer 根据文件扩展名正确路由到对应的查看器：
 * - 代码 / 文本文件 → 渲染 Editor（textarea）
 * - PDF / Excel / Word / 图片 / 未知类型 → 渲染 PlaceholderViewer
 */
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import FileViewer from '../FileViewer';

describe('FileViewer', () => {
  afterEach(() => {
    cleanup();
  });

  describe('代码文件路由', () => {
    it('Python 文件渲染编辑器', () => {
      render(<FileViewer filePath="app.py" fileContent="print('hi')" />);
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    it('TypeScript 文件渲染编辑器', () => {
      render(<FileViewer filePath="index.ts" fileContent="const x = 1" />);
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    it('CSS 文件渲染编辑器', () => {
      render(<FileViewer filePath="styles.css" fileContent="body {}" />);
      expect(screen.getByRole('textbox')).toBeTruthy();
    });
  });

  describe('文本文件路由', () => {
    it('Markdown 文件渲染编辑器', () => {
      render(<FileViewer filePath="README.md" fileContent="# Hello" />);
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    it('TXT 文件渲染编辑器', () => {
      render(<FileViewer filePath="notes.txt" fileContent="some notes" />);
      expect(screen.getByRole('textbox')).toBeTruthy();
    });
  });

  describe('二进制/富媒体文件占位', () => {
    it('PDF 文件显示占位查看器', () => {
      render(<FileViewer filePath="doc.pdf" fileContent={null} />);
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
      expect(screen.getByText(/PDF/)).toBeTruthy();
    });

    it('Excel 文件显示占位查看器', () => {
      render(<FileViewer filePath="data.xlsx" fileContent={null} />);
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
      expect(screen.getByText(/Excel/)).toBeTruthy();
    });

    it('Word 文件显示占位查看器', () => {
      render(<FileViewer filePath="report.docx" fileContent={null} />);
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
      expect(screen.getByText(/Word/)).toBeTruthy();
    });

    it('图片文件显示占位查看器', () => {
      render(<FileViewer filePath="photo.png" fileContent={null} />);
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
      expect(screen.getByText(/图片/)).toBeTruthy();
    });
  });

  describe('未知类型处理', () => {
    it('未知扩展名显示占位查看器', () => {
      render(<FileViewer filePath="file.xyz" fileContent={null} />);
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
    });

    it('无扩展名显示占位查看器', () => {
      render(<FileViewer filePath="Makefile" fileContent={null} />);
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
    });
  });

  describe('内容透传', () => {
    it('fileContent 为 null 时编辑器回退为空字符串', () => {
      render(<FileViewer filePath="app.py" fileContent={null} />);
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe('');
    });

    it('fileContent 正常透传给编辑器', () => {
      render(<FileViewer filePath="app.py" fileContent="hello world" />);
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe('hello world');
    });
  });
});

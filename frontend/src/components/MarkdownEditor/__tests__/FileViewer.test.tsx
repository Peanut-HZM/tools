/**
 * FileViewer 路由组件测试
 *
 * 验证 FileViewer 根据文件扩展名正确路由到对应的查看器：
 * - 代码文件 → 渲染 CodeEditor（Monaco Editor）
 * - 文本文件 → 渲染 Editor（textarea）
 * - PDF → 渲染 PdfViewer（react-pdf）
 * - Excel → 渲染 ExcelViewer（SheetJS）
 * - Word → 渲染 WordViewer（mammoth）
 * - 图片 / 未知类型 → 渲染 PlaceholderViewer
 */
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import FileViewer from '../FileViewer';
import type { EditorConfig } from '../../../types/markdownEditor';

/** 测试用 EditorConfig 配置 */
const mockEditorConfig: EditorConfig = {
  theme: 'dark',
  fontSize: 14,
  autoSaveInterval: 0,
  previewTheme: 'default',
  showLineNumbers: true,
  tabSize: 2,
  useSpaces: true,
  wordWrap: true,
  language: 'zh-CN',
};

/** 测试用 onSave 回调 */
const mockOnSave = vi.fn();

/**
 * Mock 的 Monaco Editor 组件
 * jsdom 无法承载真实 Monaco，使用带 data-testid 的占位 div
 */
function MockMonacoEditor(props: Record<string, unknown>) {
  return (
    <div data-testid="monaco-editor-mock" data-language={props.language as string}>
      <span data-testid="monaco-content">{(props.value as string) || ''}</span>
    </div>
  );
}

// Mock @monaco-editor/react（vi.mock 会自动提升到文件顶部）
vi.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: MockMonacoEditor,
}));

/**
 * Mock 的 PdfViewer 组件
 * jsdom 无法承载真实 react-pdf，使用带 data-testid 的占位 div
 */
function MockPdfViewer(props: Record<string, unknown>) {
  return (
    <div
      data-testid="pdf-viewer-mock"
      data-filename={props.fileName as string}
      data-has-content={props.content != null ? 'true' : 'false'}
    />
  );
}

// Mock PdfViewer（避免引入真实 react-pdf）
vi.mock('../PdfViewer', () => ({
  __esModule: true,
  default: MockPdfViewer,
}));

/**
 * Mock 的 ExcelViewer 组件
 * jsdom 无需真实的 SheetJS 解析，使用带 data-testid 的占位 div
 */
function MockExcelViewer(props: Record<string, unknown>) {
  return (
    <div
      data-testid="excel-viewer-mock"
      data-filename={props.fileName as string}
      data-has-content={props.content != null ? 'true' : 'false'}
    />
  );
}

// Mock ExcelViewer（避免引入真实 xlsx）
vi.mock('../ExcelViewer', () => ({
  __esModule: true,
  default: MockExcelViewer,
}));

/**
 * Mock 的 WordViewer 组件
 * jsdom 无需真实的 mammoth 解析，使用带 data-testid 的占位 div
 */
function MockWordViewer(props: Record<string, unknown>) {
  return (
    <div
      data-testid="word-viewer-mock"
      data-filename={props.fileName as string}
      data-has-content={props.content != null ? 'true' : 'false'}
    />
  );
}

// Mock WordViewer（避免引入真实 mammoth）
vi.mock('../WordViewer', () => ({
  __esModule: true,
  default: MockWordViewer,
}));

describe('FileViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('代码文件路由', () => {
    it('Python 文件渲染 Monaco CodeEditor', () => {
      render(
        <FileViewer
          filePath="app.py"
          fileContent="print('hi')"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByTestId('monaco-editor-mock')).toBeTruthy();
    });

    it('TypeScript 文件渲染 Monaco CodeEditor', () => {
      render(
        <FileViewer
          filePath="index.ts"
          fileContent="const x = 1"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByTestId('monaco-editor-mock')).toBeTruthy();
    });

    it('CSS 文件渲染 Monaco CodeEditor', () => {
      render(
        <FileViewer
          filePath="styles.css"
          fileContent="body {}"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByTestId('monaco-editor-mock')).toBeTruthy();
    });

    it('代码文件将 language 正确传递给 Monaco', () => {
      render(
        <FileViewer
          filePath="app.py"
          fileContent="print('hi')"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      const editor = screen.getByTestId('monaco-editor-mock');
      expect(editor.getAttribute('data-language')).toBe('python');
    });
  });

  describe('文本文件路由', () => {
    it('Markdown 文件渲染 textarea Editor（非 Monaco）', () => {
      render(
        <FileViewer
          filePath="README.md"
          fileContent="# Hello"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      // 文本文件走 Editor（textarea），不渲染 Monaco
      expect(screen.queryByTestId('monaco-editor-mock')).toBeNull();
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    it('TXT 文件渲染 textarea Editor（非 Monaco）', () => {
      render(
        <FileViewer
          filePath="notes.txt"
          fileContent="some notes"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.queryByTestId('monaco-editor-mock')).toBeNull();
      expect(screen.getByRole('textbox')).toBeTruthy();
    });
  });

  describe('二进制/富媒体文件', () => {
    it('PDF 文件渲染 PdfViewer（react-pdf）', () => {
      render(
        <FileViewer
          filePath="doc.pdf"
          fileContent="base64data"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByTestId('pdf-viewer-mock')).toBeTruthy();
      // 验证文件名透传
      expect(
        screen.getByTestId('pdf-viewer-mock').getAttribute('data-filename')
      ).toBe('doc.pdf');
      // 验证 base64 内容透传
      expect(
        screen.getByTestId('pdf-viewer-mock').getAttribute('data-has-content')
      ).toBe('true');
    });

    it('PDF 文件路径含目录时提取文件名', () => {
      render(
        <FileViewer
          filePath="/docs/reports/annual.pdf"
          fileContent="base64data"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(
        screen.getByTestId('pdf-viewer-mock').getAttribute('data-filename')
      ).toBe('annual.pdf');
    });

    it('Excel 文件渲染 ExcelViewer（SheetJS）', () => {
      render(
        <FileViewer
          filePath="data.xlsx"
          fileContent="base64data"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByTestId('excel-viewer-mock')).toBeTruthy();
      // 验证文件名透传
      expect(
        screen.getByTestId('excel-viewer-mock').getAttribute('data-filename')
      ).toBe('data.xlsx');
      // 验证 base64 内容透传
      expect(
        screen.getByTestId('excel-viewer-mock').getAttribute('data-has-content')
      ).toBe('true');
    });

    it('Excel 文件路径含目录时提取文件名', () => {
      render(
        <FileViewer
          filePath="/docs/reports/data.xlsx"
          fileContent="base64data"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(
        screen.getByTestId('excel-viewer-mock').getAttribute('data-filename')
      ).toBe('data.xlsx');
    });

    it('Word 文件渲染 WordViewer（mammoth）', () => {
      render(
        <FileViewer
          filePath="report.docx"
          fileContent="base64data"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByTestId('word-viewer-mock')).toBeTruthy();
      // 验证文件名透传
      expect(
        screen.getByTestId('word-viewer-mock').getAttribute('data-filename')
      ).toBe('report.docx');
      // 验证 base64 内容透传
      expect(
        screen.getByTestId('word-viewer-mock').getAttribute('data-has-content')
      ).toBe('true');
    });

    it('Word 文件路径含目录时提取文件名', () => {
      render(
        <FileViewer
          filePath="/docs/reports/report.docx"
          fileContent="base64data"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(
        screen.getByTestId('word-viewer-mock').getAttribute('data-filename')
      ).toBe('report.docx');
    });

    it('图片文件显示占位查看器', () => {
      render(
        <FileViewer
          filePath="photo.png"
          fileContent={null}
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
      expect(screen.getByText(/图片/)).toBeTruthy();
    });
  });

  describe('未知类型处理', () => {
    it('未知扩展名显示占位查看器', () => {
      render(
        <FileViewer
          filePath="file.xyz"
          fileContent={null}
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
    });

    it('无扩展名显示占位查看器', () => {
      render(
        <FileViewer
          filePath="Makefile"
          fileContent={null}
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      expect(screen.getByText(/不支持的文件类型/)).toBeTruthy();
    });
  });

  describe('内容透传', () => {
    it('代码文件 fileContent 为 null 时 Monaco 接收空字符串', () => {
      render(
        <FileViewer
          filePath="app.py"
          fileContent={null}
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      const contentEl = screen.getByTestId('monaco-content');
      expect(contentEl.textContent).toBe('');
    });

    it('代码文件 fileContent 正常透传给 Monaco', () => {
      render(
        <FileViewer
          filePath="app.py"
          fileContent="hello world"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      const contentEl = screen.getByTestId('monaco-content');
      expect(contentEl.textContent).toBe('hello world');
    });

    it('文本文件 fileContent 为 null 时 Editor 回退为空字符串', () => {
      render(
        <FileViewer
          filePath="README.md"
          fileContent={null}
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe('');
    });

    it('文本文件 fileContent 正常透传给 Editor', () => {
      render(
        <FileViewer
          filePath="README.md"
          fileContent="hello world"
          editorConfig={mockEditorConfig}
          onSave={mockOnSave}
        />
      );
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe('hello world');
    });
  });
});

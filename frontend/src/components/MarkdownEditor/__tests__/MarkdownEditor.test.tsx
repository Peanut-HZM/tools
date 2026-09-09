/**
 * MarkdownEditor 预览模式路由测试
 *
 * 验证预览模式下根据文件类型正确路由到不同的渲染组件：
 * - 代码文件（.py / .java / .sql 等）→ CodeEditor（只读模式）
 * - HTML 文件 → HtmlPreview
 * - Markdown / 文本文件 → Preview
 *
 * 由于 MarkdownEditor 依赖大量 Zustand store 与 react-router，
 * 统一 mock 以避免引入真实实现。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import MarkdownEditor from '../MarkdownEditor';

/* ------------------------------------------------------------------ */
/* Mock @monaco-editor/react（CodeEditor 内部依赖）                    */
/* ------------------------------------------------------------------ */
function MockMonacoEditor(props: Record<string, unknown>) {
  return (
    <div
      data-testid="monaco-editor-mock"
      data-language={props.language as string}
      data-readonly={String((props.options as Record<string, unknown>)?.readOnly)}
    >
      <span data-testid="monaco-value">{(props.value as string) || ''}</span>
    </div>
  );
}

vi.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: MockMonacoEditor,
}));

/* ------------------------------------------------------------------ */
/* Mock 重型子组件（jsdom 不兼容 react-pdf / xlsx / mammoth）         */
/* ------------------------------------------------------------------ */
vi.mock('../PdfViewer', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => (
    <div data-testid="pdf-viewer-mock" data-filename={props.fileName as string} />
  ),
}));

vi.mock('../ExcelViewer', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => (
    <div data-testid="excel-viewer-mock" data-filename={props.fileName as string} />
  ),
}));

vi.mock('../WordViewer', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => (
    <div data-testid="word-viewer-mock" data-filename={props.fileName as string} />
  ),
}));

/* ------------------------------------------------------------------ */
/* Mock react-router-dom                                              */
/* ------------------------------------------------------------------ */
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

/* ------------------------------------------------------------------ */
/* Mock Zustand stores                                                */
/* ------------------------------------------------------------------ */

/** 构造 fileStore 默认 mock */
function createFileStoreMock(overrides: Record<string, unknown> = {}) {
  return {
    directoryTree: [],
    currentFile: null,
    currentFilePath: '',
    rootPath: '',
    hasRootPath: true,
    expandedNodes: [],
    ossFiles: [],
    ossFilesLoading: false,
    isLoading: false,
    error: null,
    loadDirectoryTree: vi.fn(),
    openFile: vi.fn(),
    saveCurrentFile: vi.fn(),
    createFile: vi.fn(),
    deleteFile: vi.fn(),
    renameFile: vi.fn(),
    createDirectory: vi.fn(),
    deleteDirectory: vi.fn(),
    toggleNode: vi.fn(),
    clearError: vi.fn(),
    setRootPath: vi.fn(),
    loadRootPath: vi.fn(() => Promise.resolve({ exists: false })),
    loadOssFiles: vi.fn(),
    loadSubDirectory: vi.fn(),
    ...overrides,
  };
}

/** 构造 editorStore 默认 mock */
function createEditorStoreMock(overrides: Record<string, unknown> = {}) {
  return {
    content: '',
    cursorLine: 1,
    cursorColumn: 1,
    saveStatus: 'saved' as const,
    lastSaveTime: null,
    isDirty: false,
    setContent: vi.fn(),
    updateContent: vi.fn(),
    setCursorPosition: vi.fn(),
    markAsSaved: vi.fn(),
    setSaving: vi.fn(),
    setSaveError: vi.fn(),
    ...overrides,
  };
}

/** 构造 configStore 默认 mock */
function createConfigStoreMock(overrides: Record<string, unknown> = {}) {
  return {
    config: {
      theme: 'dark',
      fontSize: 14,
      autoSaveInterval: 0,
      previewTheme: 'default',
      showLineNumbers: true,
      tabSize: 2,
      useSpaces: true,
      wordWrap: true,
      language: 'zh-CN',
    },
    loadConfig: vi.fn(),
    saveConfig: vi.fn(),
    updateConfig: vi.fn(),
    setTheme: vi.fn(),
    ...overrides,
  };
}

let fileStoreMock: ReturnType<typeof createFileStoreMock>;
let editorStoreMock: ReturnType<typeof createEditorStoreMock>;
let configStoreMock: ReturnType<typeof createConfigStoreMock>;

vi.mock('../../../stores/fileStore', () => ({
  useFileStore: () => fileStoreMock,
}));

vi.mock('../../../stores/editorStore', () => ({
  useEditorStore: () => editorStoreMock,
}));

vi.mock('../../../stores/configStore', () => ({
  useConfigStore: () => configStoreMock,
}));

/* ------------------------------------------------------------------ */
/* Mock i18n                                                          */
/* ------------------------------------------------------------------ */
vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    language: 'zh-CN',
    setLanguage: vi.fn(),
    t: {
      editor: {
        title: 'Markdown Editor',
        preview: 'Preview',
        edit: 'Edit',
        selectFile: 'Select a file',
        unsavedChanges: 'Unsaved',
      },
      common: {
        openFolder: 'Open Folder',
        new: 'New',
        save: 'Save',
        cancel: 'Cancel',
        create: 'Create',
        settings: 'Settings',
        loading: 'Loading...',
        success: 'Success',
        folderName: 'Folder',
        fileName: 'File Name',
      },
      settings: { theme: 'Theme' },
      search: { results: 'CONTENTS', noResults: 'No headings', line: 'Line' },
      fileTree: { noFiles: 'No files', newFile: 'New File' },
    },
  }),
}));

/* ------------------------------------------------------------------ */
/* Mock 其他 hooks / 组件                                             */
/* ------------------------------------------------------------------ */
vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ toast: null, showToast: vi.fn() }),
}));

vi.mock('../../../api/markdownEditorApi', () => ({
  saveMarkdownToOss: vi.fn(),
  uploadMarkdownFile: vi.fn(),
  readMarkdownFromOss: vi.fn(),
}));

/* ------------------------------------------------------------------ */
/* 辅助函数                                                           */
/* ------------------------------------------------------------------ */

/**
 * 设置 store 并渲染 MarkdownEditor，然后点击"预览"按钮切换到预览模式
 */
function renderAndSwitchToPreview(filePath: string, fileContent: string) {
  fileStoreMock = createFileStoreMock({
    currentFile: { name: filePath, content: fileContent, path: filePath },
    currentFilePath: filePath,
  });
  editorStoreMock = createEditorStoreMock({ content: fileContent });

  const { container } = render(<MarkdownEditor />);

  // 点击"预览"按钮切换到预览模式
  // 使用 role 查询更可靠：按钮文本是 "Preview"，在 neon-button-group 中
  const buttons = screen.getAllByRole('button', { name: /Preview/i });
  fireEvent.click(buttons[0]);

  return container;
}

describe('MarkdownEditor 预览模式路由', () => {
  beforeEach(() => {
    fileStoreMock = createFileStoreMock();
    editorStoreMock = createEditorStoreMock();
    configStoreMock = createConfigStoreMock();
  });

  afterEach(() => {
    cleanup();
  });

  describe('预览模式 - 代码文件使用 CodeEditor 只读渲染', () => {
    it('Python 文件在预览模式下渲染 Monaco Editor（python 语言）', () => {
      renderAndSwitchToPreview('test.py', 'print("hello")');

      const editor = screen.getByTestId('monaco-editor-mock');
      expect(editor).toBeTruthy();
      expect(editor.getAttribute('data-language')).toBe('python');
      expect(editor.getAttribute('data-readonly')).toBe('true');
    });

    it('SQL 文件在预览模式下渲染 Monaco Editor（sql 语言）', () => {
      renderAndSwitchToPreview('query.sql', 'SELECT 1');

      const editor = screen.getByTestId('monaco-editor-mock');
      expect(editor.getAttribute('data-language')).toBe('sql');
      expect(editor.getAttribute('data-readonly')).toBe('true');
    });

    it('Java 文件在预览模式下渲染 Monaco Editor（java 语言）', () => {
      renderAndSwitchToPreview('App.java', 'class App {}');

      const editor = screen.getByTestId('monaco-editor-mock');
      expect(editor.getAttribute('data-language')).toBe('java');
      expect(editor.getAttribute('data-readonly')).toBe('true');
    });
  });

  describe('预览模式 - HTML 文件仍使用 HtmlPreview', () => {
    it('HTML 文件在预览模式下不渲染 Monaco Editor', () => {
      renderAndSwitchToPreview('page.html', '<h1>Hello</h1>');

      const editor = screen.queryByTestId('monaco-editor-mock');
      expect(editor).toBeNull();
    });
  });

  describe('预览模式 - Markdown 文件使用 Preview', () => {
    it('Markdown 文件在预览模式下不渲染 Monaco Editor', () => {
      renderAndSwitchToPreview('readme.md', '# Hello');

      const editor = screen.queryByTestId('monaco-editor-mock');
      expect(editor).toBeNull();
    });
  });
});

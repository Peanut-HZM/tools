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
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import MarkdownEditor from '../MarkdownEditor';
import { ExcelEditorProvider } from '../../../stores/excelEditorStore';
import * as markdownEditorApi from '../../../api/markdownEditorApi';

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
  useMonaco: () => null,
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
  isEditableExcel: (filePath?: string, readOnly?: boolean) =>
    !!filePath && filePath.toLowerCase().endsWith('.xlsx') && !readOnly,
}));

vi.mock('../WordViewer', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => (
    <div data-testid="word-viewer-mock" data-filename={props.fileName as string} />
  ),
}));

/* ------------------------------------------------------------------ */
/* Mock HtmlPreview（避免 jsdom 中 URL.createObjectURL 不可用）       */
/* ------------------------------------------------------------------ */
vi.mock('../Preview/HtmlPreview', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => (
    <div
      data-testid="html-preview-mock"
      data-theme={props.theme as string}
    >
      {(props.content as string) || ''}
    </div>
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
    refreshTree: vi.fn(),
    refreshingPath: null,
    refreshingAll: false,
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

/** 构造 excelEditorStore 默认 mock（可通过 overrides 控制 pending 操作） */
function createExcelEditorStoreMock(overrides: Record<string, unknown> = {}) {
  return {
    filePath: null,
    operations: [] as unknown[],
    hasPendingOperations: false,
    beginEdit: vi.fn(),
    pushOperation: vi.fn(),
    clearOperations: vi.fn(),
    ...overrides,
  };
}

let fileStoreMock: ReturnType<typeof createFileStoreMock>;
let editorStoreMock: ReturnType<typeof createEditorStoreMock>;
let configStoreMock: ReturnType<typeof createConfigStoreMock>;
let excelEditorStoreMock: ReturnType<typeof createExcelEditorStoreMock>;

vi.mock('../../../stores/fileStore', () => ({
  useFileStore: () => fileStoreMock,
}));

vi.mock('../../../stores/editorStore', () => ({
  useEditorStore: () => editorStoreMock,
}));

vi.mock('../../../stores/configStore', () => ({
  useConfigStore: () => configStoreMock,
}));

vi.mock('../../../stores/excelEditorStore', () => ({
  useExcelEditorStore: () =>
    excelEditorStoreMock ?? (excelEditorStoreMock = createExcelEditorStoreMock()),
  ExcelEditorProvider: ({ children }: { children: React.ReactNode }) => children,
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
/** 稳定的 showToast mock，便于断言调用参数 */
const mockShowToast = vi.fn();

vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ toast: null, showToast: mockShowToast }),
}));

vi.mock('../../../api/markdownEditorApi', () => ({
  saveMarkdownToOss: vi.fn(),
  uploadMarkdownFile: vi.fn(),
  readMarkdownFromOss: vi.fn(),
  saveExcelEdits: vi.fn(),
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

  const { container } = render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

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

  describe('TOC 面板显示逻辑 - 仅对 text 类型文件显示', () => {
    it('.md 文件在预览模式下显示 TOC 面板', () => {
      renderAndSwitchToPreview('readme.md', '# Title\n## Section');

      // TOC 面板容器应存在
      const tocSidebar = document.querySelector('.toc-sidebar');
      expect(tocSidebar).not.toBeNull();
    });

    it('.txt 文件在预览模式下显示 TOC 面板', () => {
      renderAndSwitchToPreview('notes.txt', 'Some plain text');

      const tocSidebar = document.querySelector('.toc-sidebar');
      expect(tocSidebar).not.toBeNull();
    });

    it('.sql 文件在预览模式下隐藏 TOC 面板', () => {
      renderAndSwitchToPreview('query.sql', 'SELECT * FROM users');

      const tocSidebar = document.querySelector('.toc-sidebar');
      expect(tocSidebar).toBeNull();
    });

    it('.py 文件在预览模式下隐藏 TOC 面板', () => {
      renderAndSwitchToPreview('app.py', 'print("hello")');

      const tocSidebar = document.querySelector('.toc-sidebar');
      expect(tocSidebar).toBeNull();
    });

    it('.html 文件在预览模式下隐藏 TOC 面板', () => {
      renderAndSwitchToPreview('page.html', '<h1>Hello</h1>');

      const tocSidebar = document.querySelector('.toc-sidebar');
      expect(tocSidebar).toBeNull();
    });

    it('未打开文件时（空路径）不显示 TOC 面板', () => {
      // 使用默认空 currentFilePath
      render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

      const tocSidebar = document.querySelector('.toc-sidebar');
      expect(tocSidebar).toBeNull();
    });
  });
});

describe('MarkdownEditor 搜索与刷新', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fileStoreMock = createFileStoreMock({
      currentFile: { name: 'readme.md', content: '# Hello', path: 'readme.md' },
      currentFilePath: 'readme.md',
    });
    editorStoreMock = createEditorStoreMock({ content: '# Hello' });
    configStoreMock = createConfigStoreMock();
  });

  afterEach(() => {
    cleanup();
  });

  it('点击搜索按钮打开搜索面板，且编辑模式自动切到预览', () => {
    render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

    // 编辑模式：editor-area 存在，view-mode 容器不存在
    expect(document.querySelector('.editor-area')).not.toBeNull();
    expect(document.querySelector('.content-area.view-mode')).toBeNull();

    fireEvent.click(screen.getByTitle(/搜索文件内容/));

    // 搜索面板打开
    expect(document.querySelector('.search-panel')).not.toBeNull();
    // 编辑模式已切到预览：editor-area 消失，view-mode 容器出现
    expect(document.querySelector('.editor-area')).toBeNull();
    expect(document.querySelector('.content-area.view-mode')).not.toBeNull();
  });

  it('工具栏刷新按钮以空路径调用 refreshTree', async () => {
    render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

    fireEvent.click(screen.getByTitle('刷新整棵文件树'));

    await waitFor(() => expect(fileStoreMock.refreshTree).toHaveBeenCalledWith(''));
  });

  it('刷新失败时显示错误 Toast', async () => {
    fileStoreMock = createFileStoreMock({
      currentFilePath: 'readme.md',
      refreshTree: vi.fn().mockRejectedValue(new Error('network down')),
    });
    render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

    fireEvent.click(screen.getByTitle('刷新整棵文件树'));

    await waitFor(() =>
      expect(mockShowToast).toHaveBeenCalledWith('刷新失败：network down', 'error')
    );
  });
});

describe('MarkdownEditor Excel 编辑保存', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  function setupExcelPending() {
    fileStoreMock = createFileStoreMock({
      currentFile: { name: 'a.xlsx', content: 'B64DATA==', path: 'a.xlsx' },
      currentFilePath: 'a.xlsx',
      openFile: vi.fn().mockResolvedValue(undefined),
    });
    editorStoreMock = createEditorStoreMock({ content: 'B64DATA==' });
    configStoreMock = createConfigStoreMock();
    excelEditorStoreMock = createExcelEditorStoreMock({
      hasPendingOperations: true,
      operations: [
        { op: 'set_cell', sheet: 'S1', row: 2, col: 1, value: 'x', kind: 'str' },
      ],
    });
  }

  it('有 Excel 操作时保存走 saveExcelEdits、清空操作并重载文件', async () => {
    setupExcelPending();
    vi.mocked(markdownEditorApi.saveExcelEdits).mockResolvedValue({
      success: true,
      message: 'ok',
    });

    render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() =>
      expect(markdownEditorApi.saveExcelEdits).toHaveBeenCalledWith('a.xlsx', [
        expect.objectContaining({ op: 'set_cell' }),
      ])
    );
    expect(excelEditorStoreMock.clearOperations).toHaveBeenCalled();
    expect(fileStoreMock.openFile).toHaveBeenCalledWith('a.xlsx');
    expect(editorStoreMock.markAsSaved).toHaveBeenCalled();
    // 不应走文本保存链路
    expect(fileStoreMock.saveCurrentFile).not.toHaveBeenCalled();
  });

  it('保存失败时设置 saveError 且不清空操作', async () => {
    setupExcelPending();
    vi.mocked(markdownEditorApi.saveExcelEdits).mockRejectedValue(new Error('disk full'));

    render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() =>
      expect(editorStoreMock.setSaveError).toHaveBeenCalledWith('disk full')
    );
    expect(excelEditorStoreMock.clearOperations).not.toHaveBeenCalled();
    expect(editorStoreMock.markAsSaved).not.toHaveBeenCalled();
  });

  it('无 Excel 操作时保存走原有 saveCurrentFile 链路', async () => {
    fileStoreMock = createFileStoreMock({
      currentFile: { name: 'a.md', content: '# hi', path: 'a.md' },
      currentFilePath: 'a.md',
      saveCurrentFile: vi.fn().mockResolvedValue(undefined),
    });
    editorStoreMock = createEditorStoreMock({ content: '# hi', isDirty: true });
    configStoreMock = createConfigStoreMock();
    excelEditorStoreMock = createExcelEditorStoreMock();

    render(
      <ExcelEditorProvider>
        <MarkdownEditor />
      </ExcelEditorProvider>
    );

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() =>
      expect(fileStoreMock.saveCurrentFile).toHaveBeenCalledWith('# hi')
    );
    expect(markdownEditorApi.saveExcelEdits).not.toHaveBeenCalled();
  });
});

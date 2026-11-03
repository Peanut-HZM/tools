/**
 * FileManager 名称搜索测试
 *
 * 覆盖「打开文件夹」对话框内的搜索能力：
 * - 按名称过滤（不区分大小写）
 * - 匹配数量与原数量提示
 * - 无匹配时的空状态文案
 * - 清除按钮恢复完整列表
 * - 选中的文件夹被搜索过滤掉时清除选中，确认目标回退到当前目录
 *
 * 注意：命中片段会被 <mark> 包裹，因此名称文本被拆成多个节点，
 * 断言统一读取名称列的 textContent 而不是 getByText 的精确文本匹配。
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import FileManager from '../FolderBrowserDialog/FileManager';
import type { FileManagerItem } from '../../../types/markdownEditor';

vi.mock('../../../api/markdownEditorApi', () => ({
  browseFileManager: vi.fn(),
  copyFileItem: vi.fn(),
  moveFileItem: vi.fn(),
  renameFileManagerItem: vi.fn(),
  deleteFileManagerItem: vi.fn(),
  createFileManagerItem: vi.fn(),
  getDownloadUrl: (path: string) => `/download?path=${encodeURIComponent(path)}`,
}));

import { browseFileManager } from '../../../api/markdownEditorApi';

const ITEMS: FileManagerItem[] = [
  {
    name: '.claude',
    path: '/work/.claude',
    type: 'directory',
    size: 0,
    modified_at: '2026-10-08T10:59:43',
    extension: '',
    is_previewable: false,
    is_hidden: true,
  },
  {
    name: 'docs',
    path: '/work/docs',
    type: 'directory',
    size: 0,
    modified_at: '2026-10-09T10:00:00',
    extension: '',
    is_previewable: false,
  },
  {
    name: 'CLAUDE.md',
    path: '/work/CLAUDE.md',
    type: 'file',
    size: 1024,
    modified_at: '2026-11-03T09:59:35',
    extension: '.md',
    is_previewable: true,
  },
  {
    name: 'README.md',
    path: '/work/README.md',
    type: 'file',
    size: 2048,
    modified_at: '2026-11-02T09:00:00',
    extension: '.md',
    is_previewable: true,
  },
];

const browseMock = vi.mocked(browseFileManager);

beforeEach(() => {
  browseMock.mockResolvedValue({
    current_path: '/work',
    breadcrumbs: [{ name: 'work', path: '/work' }],
    items: ITEMS,
    total: ITEMS.length,
    has_more: false,
  });
});

afterEach(() => {
  cleanup();
  browseMock.mockReset();
});

function searchBox() {
  return screen.getByPlaceholderText('按名称搜索文件和文件夹...') as HTMLInputElement;
}

/** 读取列表里所有可见条目名称（名称列的 textContent，忽略高亮拆分的 mark 节点） */
function visibleNames(): string[] {
  return Array.from(document.querySelectorAll('span.truncate')).map(
    (el) => el.textContent ?? '',
  );
}

/** 点击某个条目行（名称所在的 span 的父级可点击行） */
function clickName(name: string) {
  const span = Array.from(document.querySelectorAll('span.truncate')).find(
    (el) => el.textContent === name,
  );
  if (!span || !span.parentElement) throw new Error(`未找到条目: ${name}`);
  fireEvent.click(span.parentElement);
}

describe('FileManager 名称搜索', () => {
  it('按名称过滤且不区分大小写', async () => {
    render(<FileManager onConfirm={vi.fn()} initialPath="/work" />);
    await waitFor(() => expect(visibleNames()).toContain('README.md'));

    fireEvent.change(searchBox(), { target: { value: 'cla' } });

    const names = visibleNames();
    expect(names).toContain('CLAUDE.md');
    expect(names).toContain('.claude');
    expect(names).not.toContain('README.md');
    expect(names).not.toContain('docs');
    // 匹配数量 + 已过滤提示
    expect(screen.getByText('匹配 2 项')).toBeTruthy();
    expect(screen.getByText(/已过滤，原 4 项/)).toBeTruthy();
  });

  it('大写关键词同样命中（大小写不敏感）', async () => {
    render(<FileManager onConfirm={vi.fn()} initialPath="/work" />);
    await waitFor(() => expect(visibleNames()).toContain('README.md'));

    fireEvent.change(searchBox(), { target: { value: 'CLAU' } });

    const names = visibleNames();
    expect(names).toContain('CLAUDE.md');
    expect(names).toContain('.claude');
  });

  it('无匹配时展示空状态文案', async () => {
    render(<FileManager onConfirm={vi.fn()} initialPath="/work" />);
    await waitFor(() => expect(visibleNames()).toContain('README.md'));

    fireEvent.change(searchBox(), { target: { value: 'zzz' } });

    expect(screen.getByText('未找到匹配「zzz」的文件或文件夹')).toBeTruthy();
    expect(screen.getByText('匹配 0 项')).toBeTruthy();
    expect(visibleNames()).toHaveLength(0);
  });

  it('清除按钮恢复完整列表', async () => {
    render(<FileManager onConfirm={vi.fn()} initialPath="/work" />);
    await waitFor(() => expect(visibleNames()).toContain('README.md'));

    fireEvent.change(searchBox(), { target: { value: 'cla' } });
    expect(visibleNames()).not.toContain('README.md');

    fireEvent.click(screen.getByTitle('清除搜索 (Esc)'));

    await waitFor(() => expect(visibleNames()).toContain('README.md'));
    expect(visibleNames()).toContain('docs');
    expect(searchBox().value).toBe('');
  });

  it('选中的文件夹被过滤掉时清除选中并回退确认目标', async () => {
    render(<FileManager onConfirm={vi.fn()} initialPath="/work" />);
    await waitFor(() => expect(visibleNames()).toContain('docs'));

    fireEvent.change(searchBox(), { target: { value: 'docs' } });
    clickName('docs');
    expect(screen.getByText('将打开: /work/docs')).toBeTruthy();

    fireEvent.change(searchBox(), { target: { value: 'cla' } });

    await waitFor(() => expect(screen.getByText('将打开: /work')).toBeTruthy());
  });
});

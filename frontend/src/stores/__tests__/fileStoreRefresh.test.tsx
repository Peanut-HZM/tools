/**
 * refreshTree action 测试：整树刷新、子树刷新（绕过缓存）、文件夹已删除、其他错误
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup, act } from '@testing-library/react';
import { FileProvider, useFileStore } from '../fileStore';
import type { FileContextType } from '../fileStore';
import type { FileNode } from '../../types/markdownEditor';
import * as api from '../../api/markdownEditorApi';
import { ApiError } from '../../api/markdownEditorApi';

vi.mock('../../api/markdownEditorApi', async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return {
    ...actual,
    getDirectoryTree: vi.fn(),
    getRootPath: vi.fn(),
  };
});

vi.mock('../../utils/indexedDb', () => ({
  getMetadata: vi.fn(async () => null),
  saveMetadata: vi.fn(async () => undefined),
}));

const rootTree: FileNode = {
  name: 'root',
  path: '',
  type: 'directory',
  children: [{ name: 'docs', path: 'docs', type: 'directory', children: [] }],
};

const docsTree: FileNode = {
  name: 'docs',
  path: 'docs',
  type: 'directory',
  children: [{ name: 'new.md', path: 'docs/new.md', type: 'file' }],
};

let store: FileContextType | null = null;

function Probe() {
  store = useFileStore();
  return null;
}

beforeEach(() => {
  vi.clearAllMocks();
  store = null;
});

afterEach(cleanup);

async function renderProvider(): Promise<FileContextType> {
  render(
    <FileProvider>
      <Probe />
    </FileProvider>
  );
  return store!;
}

describe('refreshTree', () => {
  it('空路径刷新整树并重置 loading 状态', async () => {
    vi.mocked(api.getDirectoryTree).mockResolvedValue(rootTree);
    const s = await renderProvider();

    await act(async () => {
      await s.refreshTree('');
    });

    expect(api.getDirectoryTree).toHaveBeenCalledWith('', -1);
    expect(store!.directoryTree).toEqual(rootTree);
    expect(store!.refreshingAll).toBe(false);
  });

  it('子树刷新绕过缓存并合并到主树', async () => {
    vi.mocked(api.getDirectoryTree)
      .mockResolvedValueOnce(rootTree)
      .mockResolvedValueOnce(docsTree);
    const s = await renderProvider();

    await act(async () => {
      await s.refreshTree('');
    });
    await act(async () => {
      await s.refreshTree('docs');
    });

    expect(api.getDirectoryTree).toHaveBeenLastCalledWith('docs', -1);
    const docs = store!.directoryTree!.children![0];
    expect(docs.children!.map((c) => c.name)).toContain('new.md');
    expect(store!.refreshingPath).toBeNull();
  });

  it('文件夹已被外部删除时移除节点并抛出错误', async () => {
    vi.mocked(api.getDirectoryTree)
      .mockResolvedValueOnce(rootTree)
      .mockRejectedValueOnce(new ApiError('Directory not found: docs', 404));
    const s = await renderProvider();

    await act(async () => {
      await s.refreshTree('');
    });
    await expect(
      act(async () => {
        await s.refreshTree('docs');
      })
    ).rejects.toThrow('Directory not found');

    expect(store!.directoryTree!.children).toHaveLength(0);
    expect(store!.refreshingPath).toBeNull();
  });

  it('其他错误保持树不变并抛出', async () => {
    vi.mocked(api.getDirectoryTree)
      .mockResolvedValueOnce(rootTree)
      .mockRejectedValueOnce(new Error('network down'));
    const s = await renderProvider();

    await act(async () => {
      await s.refreshTree('');
    });
    await expect(
      act(async () => {
        await s.refreshTree('docs');
      })
    ).rejects.toThrow('network down');

    expect(store!.directoryTree!.children).toHaveLength(1);
    expect(store!.directoryTree!.children![0].children).toHaveLength(0);
  });
});

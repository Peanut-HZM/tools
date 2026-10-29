/**
 * revealFile action 测试：定位文件时展开祖先目录、按需加载缺失层级
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup, act } from '@testing-library/react';
import { FileProvider, useFileStore, ancestorDirsOf, findNodeByPath } from '../fileStore';
import type { FileContextType } from '../fileStore';
import type { FileNode } from '../../types/markdownEditor';
import * as api from '../../api/markdownEditorApi';

vi.mock('../../api/markdownEditorApi', async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return {
    ...actual,
    getDirectoryTree: vi.fn(),
    readFileRaw: vi.fn(),
  };
});

vi.mock('../../utils/indexedDb', () => ({
  getMetadata: vi.fn(async () => null),
  saveMetadata: vi.fn(async () => undefined),
  deleteMetadataByPrefix: vi.fn(async () => undefined),
}));

/** root → docs → guide → a.md */
const tree: FileNode = {
  name: 'root',
  path: '',
  type: 'directory',
  children: [
    {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [
        {
          name: 'guide',
          path: 'docs/guide',
          type: 'directory',
          children: [{ name: 'a.md', path: 'docs/guide/a.md', type: 'file' }],
        },
      ],
    },
  ],
};

let store: FileContextType | null = null;

function Probe() {
  store = useFileStore();
  return null;
}

beforeEach(() => {
  vi.clearAllMocks();
  store = null;
  // 默认整树加载返回固定测试树
  vi.mocked(api.getDirectoryTree).mockResolvedValue(tree);
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

describe('ancestorDirsOf', () => {
  it('返回从根到直接父目录的路径', () => {
    expect(ancestorDirsOf('a/b/c.md')).toEqual(['a', 'a/b']);
  });

  it('根级文件没有祖先目录', () => {
    expect(ancestorDirsOf('c.md')).toEqual([]);
  });
});

describe('findNodeByPath', () => {
  it('找到深层节点', () => {
    const node = findNodeByPath(tree, 'docs/guide/a.md');
    expect(node?.name).toBe('a.md');
  });

  it('路径不存在时返回 null', () => {
    expect(findNodeByPath(tree, 'docs/missing.md')).toBeNull();
  });
});

describe('revealFile', () => {
  it('文件已在树中时展开其祖先目录且不额外请求', async () => {
    const s = await renderProvider();
    await act(async () => {
      await s.loadDirectoryTree('', -1);
    });
    vi.mocked(api.getDirectoryTree).mockClear();

    await act(async () => {
      await store!.revealFile('docs/guide/a.md');
    });

    expect(store!.expandedNodes.has('docs')).toBe(true);
    expect(store!.expandedNodes.has('docs/guide')).toBe(true);
    expect(api.getDirectoryTree).not.toHaveBeenCalled();
  });

  it('目录缺失时按层级加载并把文件插入树中', async () => {
    const s = await renderProvider();
    await act(async () => {
      await s.loadDirectoryTree('', -1);
    });
    vi.mocked(api.getDirectoryTree).mockClear();

    const newDir: FileNode = {
      name: 'new',
      path: 'docs/new',
      type: 'directory',
      children: [{ name: 'b.md', path: 'docs/new/b.md', type: 'file' }],
    };
    vi.mocked(api.getDirectoryTree).mockResolvedValue(newDir);

    await act(async () => {
      await store!.revealFile('docs/new/b.md');
    });

    // 只加载缺失的那一层目录，且只列一层子项
    expect(api.getDirectoryTree).toHaveBeenCalledWith('docs/new', 0);
    expect(findNodeByPath(store!.directoryTree, 'docs/new/b.md')).not.toBeNull();
    expect(store!.expandedNodes.has('docs')).toBe(true);
    expect(store!.expandedNodes.has('docs/new')).toBe(true);
  });

  it('目录加载失败时仍展开已知祖先目录', async () => {
    const s = await renderProvider();
    await act(async () => {
      await s.loadDirectoryTree('', -1);
    });
    vi.mocked(api.getDirectoryTree).mockClear();
    vi.mocked(api.getDirectoryTree).mockRejectedValueOnce(new Error('not found'));
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    await act(async () => {
      await store!.revealFile('docs/missing/b.md');
    });

    expect(store!.expandedNodes.has('docs')).toBe(true);
    expect(store!.expandedNodes.has('docs/missing')).toBe(true);
    errorSpy.mockRestore();
  });

  it('根级文件不展开任何目录', async () => {
    const s = await renderProvider();
    await act(async () => {
      await s.loadDirectoryTree('', -1);
    });
    vi.mocked(api.getDirectoryTree).mockClear();

    await act(async () => {
      await store!.revealFile('a.md');
    });

    expect(store!.expandedNodes.size).toBe(0);
    expect(api.getDirectoryTree).not.toHaveBeenCalled();
  });

  it('空路径不做任何处理', async () => {
    const s = await renderProvider();
    await act(async () => {
      await s.loadDirectoryTree('', -1);
    });
    vi.mocked(api.getDirectoryTree).mockClear();

    await act(async () => {
      await store!.revealFile('');
    });

    expect(store!.expandedNodes.size).toBe(0);
    expect(api.getDirectoryTree).not.toHaveBeenCalled();
  });
});

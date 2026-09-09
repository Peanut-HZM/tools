/**
 * fileStore (FileProvider) 单元测试
 * 覆盖 openFile 在文本/二进制分支下的行为
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';

vi.mock('../../api/markdownEditorApi', () => ({
  getRootPath: vi.fn(),
  updateRootPath: vi.fn(),
  getDirectoryTree: vi.fn(),
  readFileRaw: vi.fn(),
  saveFile: vi.fn(),
  createFile: vi.fn(),
  deleteFile: vi.fn(),
  renameFile: vi.fn(),
  createDirectory: vi.fn(),
  deleteDirectory: vi.fn(),
  listOssFiles: vi.fn(),
}));

vi.mock('../../utils/indexedDb', () => ({
  getMetadata: vi.fn().mockResolvedValue(null),
  saveMetadata: vi.fn().mockResolvedValue(undefined),
}));

import * as api from '../../api/markdownEditorApi';
import { FileProvider, useFileStore } from '../fileStore';

const mockedReadFileRaw = api.readFileRaw as unknown as ReturnType<typeof vi.fn>;

function wrapper({ children }: { children: ReactNode }) {
  return <FileProvider>{children}</FileProvider>;
}

beforeEach(() => {
  mockedReadFileRaw.mockReset();
});

describe('fileStore.openFile', () => {
  it('文本文件：将 text 字段写入 currentFile.content', async () => {
    mockedReadFileRaw.mockResolvedValueOnce({
      path: '/notes/a.md',
      content_type: 'text/markdown',
      size: 12,
      modified: '2026-01-01T00:00:00Z',
      text: '# Hello',
    });

    const { result } = renderHook(() => useFileStore(), { wrapper });

    await act(async () => {
      await result.current.openFile('/notes/a.md');
    });

    await waitFor(() => {
      expect(result.current.currentFile).not.toBeNull();
    });

    expect(mockedReadFileRaw).toHaveBeenCalledWith('/notes/a.md');
    expect(result.current.currentFile?.path).toBe('/notes/a.md');
    expect(result.current.currentFile?.content).toBe('# Hello');
    expect(result.current.currentFilePath).toBe('/notes/a.md');
  });

  it('二进制文件：content 为 base64 数据（供 PdfViewer 等查看器渲染）', async () => {
    mockedReadFileRaw.mockResolvedValueOnce({
      path: '/assets/x.pdf',
      content_type: 'application/pdf',
      size: 3 * 1024 * 1024, // 3 MB
      modified: '2026-02-01T00:00:00Z',
      data: 'BASE64DATA',
    });

    const { result } = renderHook(() => useFileStore(), { wrapper });

    await act(async () => {
      await result.current.openFile('/assets/x.pdf');
    });

    await waitFor(() => {
      expect(result.current.currentFile).not.toBeNull();
    });

    // 二进制文件直接传递 base64 数据，由具体查看器负责渲染
    expect(result.current.currentFile?.content).toBe('BASE64DATA');
  });

  it('openFile 失败时：设置 error 并重新抛出', async () => {
    mockedReadFileRaw.mockRejectedValueOnce(new Error('boom'));

    const { result } = renderHook(() => useFileStore(), { wrapper });

    await act(async () => {
      try {
        await result.current.openFile('/missing');
      } catch {
        // 忽略
      }
    });

    expect(result.current.error).toBe('boom');
    expect(result.current.isLoading).toBe(false);
  });
});

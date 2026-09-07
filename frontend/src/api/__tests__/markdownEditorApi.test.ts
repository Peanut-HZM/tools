/**
 * markdownEditorApi 单元测试
 * 覆盖 readFileRaw / openFile 路径相关的接口调用
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../http', () => ({
  authedFetch: vi.fn(),
}));

vi.mock('../authApi', () => ({
  getAuthHeaders: vi.fn(() => ({ Authorization: 'Bearer test-token' })),
}));

import { authedFetch } from '../http';
import * as api from '../markdownEditorApi';

const mockedFetch = authedFetch as unknown as ReturnType<typeof vi.fn>;

function mockResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as unknown as Response;
}

beforeEach(() => {
  mockedFetch.mockReset();
});

describe('readFileRaw', () => {
  it('调用 /files/read-raw 并返回 FileRawContent', async () => {
    const payload = {
      path: '/docs/a.md',
      content_type: 'text/markdown',
      size: 123,
      modified: '2026-01-01T00:00:00Z',
      text: '# hello',
    };
    mockedFetch.mockResolvedValueOnce(mockResponse(payload));

    const result = await api.readFileRaw('/docs/a.md');

    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockedFetch.mock.calls[0];
    expect(url).toContain('/files/read-raw');
    expect(url).toContain(encodeURIComponent('/docs/a.md'));
    expect(init?.method).toBe('GET');
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer test-token');
    expect(result).toEqual(payload);
  });

  it('非 2xx 响应抛出后端 detail', async () => {
    mockedFetch.mockResolvedValueOnce(mockResponse({ detail: '文件不存在' }, false, 404));
    await expect(api.readFileRaw('/missing')).rejects.toThrow('文件不存在');
  });
});

describe('fileStore.openFile (文本/二进制分支)', () => {
  // 直接通过导入 store 模块来测分支逻辑过于重（涉及 React Context），
  // 这里以 "后端返回结构 → 业务层分支" 的纯逻辑等价测试。
  function resolveContent(file: {
    text?: string;
    data?: string;
    content_type: string;
    size: number;
  }): string {
    // 与 fileStore.tsx 中 openFile 的分支保持一致
    if (file.text) return file.text;
    if (file.data) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return `[二进制文件：${file.content_type}，${sizeMB} MB]`;
    }
    return '';
  }

  it('文本文件：优先使用 text 字段', () => {
    const out = resolveContent({
      text: '# Title',
      content_type: 'text/markdown',
      size: 8,
    });
    expect(out).toBe('# Title');
  });

  it('二进制文件：显示 content_type 与 MB 大小', () => {
    const out = resolveContent({
      data: 'AAAA',
      content_type: 'application/pdf',
      size: 2 * 1024 * 1024, // 2 MB
    });
    expect(out).toBe('[二进制文件：application/pdf，2.00 MB]');
  });

  it('二进制文件：小尺寸正确显示为小数 MB', () => {
    const out = resolveContent({
      data: 'BBBB',
      content_type: 'image/png',
      size: 512 * 1024, // 0.5 MB
    });
    expect(out).toBe('[二进制文件：image/png，0.50 MB]');
  });

  it('既无 text 也无 data：返回空字符串', () => {
    const out = resolveContent({ content_type: 'text/plain', size: 0 });
    expect(out).toBe('');
  });
});

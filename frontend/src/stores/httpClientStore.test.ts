import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useHttpClientStore } from './httpClientStore';
import { updateRequest } from '../services/httpClientApi';
import type { HttpRequest } from '../services/httpClientApi';

// Mock API 层，避免真实网络请求
vi.mock('../services/httpClientApi', () => ({
  updateRequest: vi.fn(),
}));

/** 构造最小 HttpRequest 测试数据 */
const makeRequest = (id: string, url = 'https://example.com/api'): HttpRequest => ({
  id,
  collection_id: 'col-1',
  name: '测试请求',
  method: 'GET',
  url,
  headers: {},
  params: {},
  body_type: 'none',
  auth_type: 'none',
  auth_config: {},
  sort_order: 0,
  created_at: '',
  updated_at: '',
});

describe('httpClientStore.saveRequest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 重置 store 关键状态
    useHttpClientStore.setState({ openTabs: [], activeTabId: null });
  });

  it('保存成功后 isModified 置为 false 且 request 更新为后端返回值', async () => {
    const request = makeRequest('req-1');
    useHttpClientStore.getState().openTab(request);
    useHttpClientStore.getState().updateTabRequest('req-1', { url: 'https://example.com/new' });

    vi.mocked(updateRequest).mockResolvedValue({
      ...request,
      url: 'https://example.com/new',
      updated_at: '2026-08-22T12:00:00Z',
    });

    await useHttpClientStore.getState().saveRequest('req-1');

    const tab = useHttpClientStore.getState().openTabs.find(t => t.requestId === 'req-1');
    expect(tab?.isModified).toBe(false);
    expect(tab?.request.url).toBe('https://example.com/new');
    expect(updateRequest).toHaveBeenCalledWith('req-1', expect.objectContaining({ url: 'https://example.com/new' }));
  });

  it('保存失败时抛出异常且 isModified 保持 true', async () => {
    const request = makeRequest('req-2');
    useHttpClientStore.getState().openTab(request);
    useHttpClientStore.getState().updateTabRequest('req-2', { url: 'https://example.com/changed' });

    vi.mocked(updateRequest).mockRejectedValue(new Error('网络错误'));

    await expect(useHttpClientStore.getState().saveRequest('req-2')).rejects.toThrow('网络错误');

    const tab = useHttpClientStore.getState().openTabs.find(t => t.requestId === 'req-2');
    expect(tab?.isModified).toBe(true);
    expect(tab?.request.url).toBe('https://example.com/changed');
  });

  it('保存进行中继续编辑不会被旧快照覆盖（竞态回归测试）', async () => {
    const request = makeRequest('req-1');
    useHttpClientStore.getState().openTab(request);

    // 手动控制 updateRequest 的完成时机
    let resolveUpdate!: (value: HttpRequest) => void;
    const deferred = new Promise<HttpRequest>(resolve => {
      resolveUpdate = resolve;
    });
    vi.mocked(updateRequest).mockReturnValue(deferred);

    // 不等待保存完成，模拟保存期间用户继续编辑
    const savePromise = useHttpClientStore.getState().saveRequest('req-1');
    useHttpClientStore.getState().updateTabRequest('req-1', { url: 'https://example.com/during' });

    // 服务端返回保存时的快照内容（不包含保存期间的编辑）
    resolveUpdate({
      ...request,
      url: 'https://example.com/api',
      updated_at: '2026-08-22T12:00:00Z',
    });

    await savePromise;

    const tab = useHttpClientStore.getState().openTabs.find(t => t.requestId === 'req-1');
    expect(tab?.isModified).toBe(false);
    expect(tab?.request.url).toBe('https://example.com/during');
  });
});

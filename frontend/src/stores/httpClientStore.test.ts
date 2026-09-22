import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useHttpClientStore } from './httpClientStore';
import { updateRequest } from '../services/httpClientApi';
import type { HttpRequest } from '../services/httpClientApi';

// Mock API 层，避免真实网络请求
vi.mock('../services/httpClientApi', () => ({
  updateRequest: vi.fn(),
  fetchCollections: vi.fn().mockResolvedValue([]),
  fetchRequests: vi.fn().mockResolvedValue([]),
  fetchEnvironments: vi.fn().mockResolvedValue([]),
  fetchActiveEnvironment: vi.fn().mockResolvedValue(null),
  sendHttpRequest: vi.fn(),
  fetchHistory: vi.fn().mockResolvedValue([]),
  clearHistory: vi.fn(),
  deleteHistoryItem: vi.fn(),
  deleteRequest: vi.fn(),
  activateEnvironment: vi.fn(),
  duplicateRequest: vi.fn(),
}));

/** 构造最小 HttpRequest 测试数据 */
const makeRequest = (id: string, url = 'https://example.com/api'): HttpRequest => ({
  id,
  collection_id: 'col-1',
  name: '测试请求',
  method: 'GET',
  url,
  headers: [],
  params: [],
  body_type: 'none',
  form_data: [],
  auth_type: 'none',
  auth_config: {},
  extract_variables: [],
  assertions: [],
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

  it('保存时 form_data 中的 File 对象被序列化为文件名（不丢字段）', async () => {
    const file = new File(['content'], 'upload.png', { type: 'image/png' });
    const request = makeRequest('req-fd');
    request.body_type = 'form-data';
    request.form_data = [
      { key: 'name', value: 'abc', type: 'text', enabled: true, description: '' },
      { key: 'file', value: '', type: 'file', enabled: true, file, description: '' },
    ];
    useHttpClientStore.getState().openTab(request);

    vi.mocked(updateRequest).mockResolvedValue(request);

    await useHttpClientStore.getState().saveRequest('req-fd');

    const payload = vi.mocked(updateRequest).mock.calls[0][1] as HttpRequest;
    expect(payload.form_data?.[0].value).toBe('abc');
    expect(payload.form_data?.[1].value).toBe('upload.png');
    expect((payload.form_data?.[1] as any).file).toBeUndefined();
  });
});

describe('httpClientStore.renameRequest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useHttpClientStore.setState({ openTabs: [], activeTabId: null });
  });

  it('改名成功后 tab 的 request.name 更新且 isModified 保持 false', async () => {
    const request = makeRequest('req-1');
    useHttpClientStore.getState().openTab(request);

    vi.mocked(updateRequest).mockResolvedValue({
      ...request,
      name: '新名字',
      updated_at: '2026-08-22T12:00:00Z',
    });

    await useHttpClientStore.getState().renameRequest('req-1', '新名字');

    const tab = useHttpClientStore.getState().openTabs.find(t => t.requestId === 'req-1');
    expect(tab?.request.name).toBe('新名字');
    expect(tab?.isModified).toBe(false);
    expect(updateRequest).toHaveBeenCalledWith('req-1', { name: '新名字' });
  });

  it('改名失败时抛出异常且 tab 状态不变', async () => {
    const request = makeRequest('req-2');
    useHttpClientStore.getState().openTab(request);

    vi.mocked(updateRequest).mockRejectedValue(new Error('网络错误'));

    await expect(useHttpClientStore.getState().renameRequest('req-2', '新名字')).rejects.toThrow('网络错误');

    const tab = useHttpClientStore.getState().openTabs.find(t => t.requestId === 'req-2');
    expect(tab?.request.name).toBe('测试请求');
    expect(tab?.isModified).toBe(false);
  });
});

describe('httpClientStore.sendRequest（per-tab 响应）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useHttpClientStore.setState({ openTabs: [], activeTabId: null });
  });

  it('响应写入发起请求的标签页，不影响其他标签页', async () => {
    const { sendHttpRequest } = await import('../services/httpClientApi');
    const reqA = makeRequest('req-a', 'https://example.com/a');
    const reqB = makeRequest('req-b', 'https://example.com/b');
    useHttpClientStore.getState().openTab(reqA);
    useHttpClientStore.getState().openTab(reqB);

    const successResponse = {
      status_code: 200,
      status_text: 'OK',
      headers: {},
      body: '{}',
      response_time: 100,
      size: 2,
      content_type: 'application/json',
      request_url: 'https://example.com/a',
      request_headers: {},
      extracted_variables: {},
      assertion_results: [],
      error: null,
    };
    vi.mocked(sendHttpRequest).mockResolvedValue(successResponse);

    await useHttpClientStore.getState().sendRequest('req-a', {
      method: 'GET',
      url: 'https://example.com/a',
      headers: [],
      params: [],
    });

    const state = useHttpClientStore.getState();
    const tabA = state.openTabs.find(t => t.requestId === 'req-a');
    const tabB = state.openTabs.find(t => t.requestId === 'req-b');
    expect(tabA?.response?.status_code).toBe(200);
    expect(tabA?.sending).toBe(false);
    expect(tabB?.response).toBeNull();
  });

  it('网络失败时错误响应仍写入标签页且 sending 复位', async () => {
    const { sendHttpRequest } = await import('../services/httpClientApi');
    const req = makeRequest('req-err');
    useHttpClientStore.getState().openTab(req);

    vi.mocked(sendHttpRequest).mockRejectedValue(new Error('connect refused'));

    await expect(
      useHttpClientStore.getState().sendRequest('req-err', {
        method: 'GET',
        url: 'https://example.com/x',
        headers: [],
        params: [],
      })
    ).rejects.toThrow('connect refused');

    const tab = useHttpClientStore.getState().openTabs.find(t => t.requestId === 'req-err');
    expect(tab?.sending).toBe(false);
    expect(tab?.response?.status_code).toBe(0);
    expect(tab?.response?.error).toContain('connect refused');
  });
});

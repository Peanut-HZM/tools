/**
 * MCP Servers API Client - 单元测试
 * Phase 3-Plan-1A
 *
 * 覆盖：
 *  - 类型字段完整性
 *  - HTTP 方法 / URL 末尾（不依赖 env-driven base URL）
 *  - 错误处理（非 2xx 抛出 Error，并附带后端 detail）
 *  - delete 接口对 204 状态码的兼容性
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type {
  McpServer,
  McpServerCreate,
  McpServerUpdate,
  McpServerTestResponse,
} from '../mcpServersApi';

// 模拟 authedFetch 与 getAuthHeaders
vi.mock('../http', () => ({
  authedFetch: vi.fn(),
}));

vi.mock('../authApi', () => ({
  getAuthHeaders: vi.fn(() => ({ Authorization: 'Bearer test-token' })),
}));

import { authedFetch } from '../http';
import { mcpServersApi } from '../mcpServersApi';

const mockedFetch = authedFetch as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockedFetch.mockReset();
});

/** 构造最小的 McpServer 对象（与后端 McpServerResponse 字段一致） */
function makeServer(overrides: Partial<McpServer> = {}): McpServer {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    name: 'github',
    server_url: 'http://localhost:3000',
    transport: 'sse',
    is_active: true,
    timeout_seconds: 30,
    last_connected_at: null,
    last_error: null,
    tools_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

/** 断言 URL 以给定后缀结尾（兼容本地 base 主机与生产相对路径） */
function expectUrlSuffix(callIndex: number, suffix: string): { init: RequestInit | undefined; url: string } {
  expect(mockedFetch).toHaveBeenCalled();
  const [url, init] = mockedFetch.mock.calls[callIndex];
  expect(typeof url).toBe('string');
  expect((url as string).endsWith(suffix)).toBe(true);
  return { url: url as string, init };
}

describe('McpServer 接口字段', () => {
  it('应包含后端 McpServerResponse 的全部字段', () => {
    const s = makeServer();
    expect(s.id).toBeDefined();
    expect(s.name).toBeDefined();
    expect(s.server_url).toBeDefined();
    expect(s.transport).toBe('sse');
    expect(typeof s.is_active).toBe('boolean');
    expect(typeof s.timeout_seconds).toBe('number');
    expect(s.last_connected_at === null || typeof s.last_connected_at === 'string').toBe(true);
    expect(s.last_error === null || typeof s.last_error === 'string').toBe(true);
    expect(typeof s.tools_count).toBe('number');
    expect(typeof s.created_at).toBe('string');
    expect(typeof s.updated_at).toBe('string');
  });
});

describe('mcpServersApi.list', () => {
  it('GET /api/admin/mcp/servers 并返回数组', async () => {
    const fakeResp = [makeServer()];
    mockedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => fakeResp,
    });

    const result = await mcpServersApi.list();

    const { init } = expectUrlSuffix(0, '/api/admin/mcp/servers');
    expect(init?.method).toBeUndefined();
    expect(Array.isArray(result)).toBe(true);
    expect(result[0].name).toBe('github');
  });

  it('服务端失败时抛出 Error', async () => {
    mockedFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'unauthorized' }),
    });

    await expect(mcpServersApi.list()).rejects.toThrow(/unauthorized|Failed/);
  });
});

describe('mcpServersApi.create', () => {
  it('POST /api/admin/mcp/servers 并发送 JSON body', async () => {
    const created = makeServer({ name: 'newone' });
    mockedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => created,
    });

    const payload: McpServerCreate = {
      name: 'newone',
      server_url: 'http://localhost:4000',
      transport: 'sse',
      timeout_seconds: 60,
    };

    const result = await mcpServersApi.create(payload);

    const { init } = expectUrlSuffix(0, '/api/admin/mcp/servers');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(init?.body as string)).toEqual(payload);
    expect(result.name).toBe('newone');
  });

  it('后端 4xx 错误抛出包含 detail 的 Error', async () => {
    mockedFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "Server name 'github' already exists" }),
    });

    await expect(
      mcpServersApi.create({ name: 'github', server_url: 'http://x' }),
    ).rejects.toThrow(/already exists/);
  });
});

describe('mcpServersApi.update', () => {
  it('PUT /api/admin/mcp/servers/{id}', async () => {
    const id = '00000000-0000-0000-0000-000000000001';
    const updated = makeServer({ name: 'renamed', is_active: false });
    mockedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => updated,
    });

    const payload: McpServerUpdate = { name: 'renamed', is_active: false };
    const result = await mcpServersApi.update(id, payload);

    expectUrlSuffix(0, `/api/admin/mcp/servers/${id}`);
    const init = mockedFetch.mock.calls[0][1] as RequestInit;
    expect(init?.method).toBe('PUT');
    expect(JSON.parse(init?.body as string)).toEqual(payload);
    expect(result.name).toBe('renamed');
    expect(result.is_active).toBe(false);
  });
});

describe('mcpServersApi.delete', () => {
  it('DELETE /api/admin/mcp/servers/{id} 成功不抛错', async () => {
    const id = '00000000-0000-0000-0000-000000000001';
    mockedFetch.mockResolvedValueOnce({ ok: true, status: 204, json: async () => null });

    await expect(mcpServersApi.delete(id)).resolves.toBeUndefined();

    const { init } = expectUrlSuffix(0, `/api/admin/mcp/servers/${id}`);
    expect(init?.method).toBe('DELETE');
  });

  it('DELETE 在 204 状态码下不抛错', async () => {
    mockedFetch.mockResolvedValueOnce({ ok: true, status: 204, json: async () => '' });
    await expect(mcpServersApi.delete('xxx')).resolves.toBeUndefined();
  });

  it('DELETE 在非 2xx 时抛出错误', async () => {
    mockedFetch.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) });
    await expect(mcpServersApi.delete('xxx')).rejects.toThrow();
  });
});

describe('mcpServersApi.test', () => {
  it('POST /api/admin/mcp/servers/{id}/test', async () => {
    const id = 'server-1';
    const fakeResp: McpServerTestResponse = {
      success: true,
      tools: [{ name: 'list_repos', description: 'List repos' }],
    };
    mockedFetch.mockResolvedValueOnce({ ok: true, json: async () => fakeResp });

    const resp = await mcpServersApi.test(id);

    const { init } = expectUrlSuffix(0, '/api/admin/mcp/servers/server-1/test');
    expect(init?.method).toBe('POST');
    expect(resp.success).toBe(true);
    expect(resp.tools[0].name).toBe('list_repos');
  });

  it('服务端 5xx 错误抛出 Error', async () => {
    mockedFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'mcp timeout' }),
    });
    await expect(mcpServersApi.test('x')).rejects.toThrow(/timeout|test/i);
  });
});

describe('mcpServersApi.sync', () => {
  it('POST /api/admin/mcp/servers/{id}/sync 并返回 tools_count', async () => {
    const id = 'server-1';
    mockedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, tools_count: 5 }),
    });

    const resp = await mcpServersApi.sync(id);

    const { init } = expectUrlSuffix(0, '/api/admin/mcp/servers/server-1/sync');
    expect(init?.method).toBe('POST');
    expect(resp.tools_count).toBe(5);
  });
});

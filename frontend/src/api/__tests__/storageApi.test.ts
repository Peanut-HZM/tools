/**
 * storageApi 测试
 *
 * 覆盖：状态查询、单条迁移、批量迁移的 URL 与参数正确性
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getStorageStatus, migrateConfig, migrateAllConfigs } from '../storageApi';

const mockFetch = vi.fn();

vi.mock('../http', () => ({
  authedFetch: (...args: unknown[]) => mockFetch(...args),
}));

vi.mock('../authApi', () => ({
  getAuthHeaders: () => ({ Authorization: 'Bearer test-token' }),
  getAuthToken: () => 'test-token',
}));

describe('storageApi', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('getStorageStatus 请求 /api/storage/status', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        server_available: false,
        server_reason: '未配置远程服务器',
        local_path: 'C:/Users/x/.toolbox/toolbox.db',
      }),
    });

    const status = await getStorageStatus();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/storage/status'),
      expect.anything()
    );
    expect(status.server_available).toBe(false);
    expect(status.local_path).toContain('.toolbox');
  });

  it('migrateConfig 发送正确的 URL 与 body', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        storage_location: 'local',
        message: '迁移成功',
      }),
    });

    const result = await migrateConfig('database', 'cfg-1', 'local');

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/storage/database/configs/cfg-1/migrate');
    expect(JSON.parse(options.body)).toEqual({ target: 'local' });
    expect(result.success).toBe(true);
  });

  it('migrateAllConfigs 请求 migrate-all 端点', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        migrated: 3,
        failed: 0,
        errors: [],
      }),
    });

    const result = await migrateAllConfigs('k8s', 'server');

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/storage/k8s/configs/migrate-all');
    expect(JSON.parse(options.body)).toEqual({ target: 'server' });
    expect(result.migrated).toBe(3);
  });
});

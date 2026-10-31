/**
 * 数据库工具存储位置接入测试
 *
 * 覆盖：连接列表渲染存储徽章、迁移按钮调用 migrateConfig('database', ...)、
 * 创建连接时提交 storage_location（API 层缺省 'local'）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StorageLocationBadge from '../../../Common/StorageLocationBadge';
import { migrateConfig } from '../../../../api/storageApi';
import { createDatabase } from '../../../../api/databaseToolApi';
import type { DatabaseConfig } from '../../../../types/databaseTool';

vi.mock('../../../../api/storageApi', () => ({
  getStorageStatus: vi.fn().mockResolvedValue({
    server_available: true,
    server_reason: '',
    local_path: 'C:/Users/x/.toolbox/toolbox.db',
  }),
  migrateConfig: vi.fn().mockResolvedValue({ success: true, message: '迁移成功' }),
  migrateAllConfigs: vi.fn(),
}));

vi.mock('../../../../api/databaseToolApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../../api/databaseToolApi')>();
  return {
    ...actual,
    getDisplayPreferences: vi.fn().mockRejectedValue(new Error('skip')),
  };
});

// ConnectionList 依赖 DatabaseToolContext / workspaceStore，单测中以固定值替换
vi.mock('../../../../contexts/DatabaseToolContext', () => ({
  useDatabaseTool: () => ({
    configs: [makeConfig()],
    currentConfig: null,
    selectConfigById: vi.fn(),
    setCurrentDatabase: vi.fn(),
    refreshConfigs: vi.fn().mockResolvedValue(undefined),
    isLoading: false,
  }),
}));

vi.mock('../../../../stores/workspaceStore', () => ({
  useWorkspaceStore: () => ({
    isToolSidebarVisible: true,
    toggleToolSidebar: vi.fn(),
  }),
}));

// BackupDialog 等子组件依赖 Toast 上下文
vi.mock('../../../../contexts/ToastContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../../contexts/ToastContext')>().catch(() => ({} as any));
  return {
    ...actual,
    useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
  };
});

function makeConfig(): DatabaseConfig {
  return {
    id: 'c1',
    user_id: 'u1',
    alias: '本地连接',
    db_type: 'mysql' as DatabaseConfig['db_type'],
    host: 'localhost',
    port: 3306,
    username: 'root',
    is_active: true,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    storage_location: 'local',
  };
}

describe('数据库工具存储位置', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  it('StorageLocationBadge 渲染本机徽章', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });

  it('StorageLocationBadge 渲染服务器徽章', () => {
    render(<StorageLocationBadge location="server" />);
    expect(screen.getByText(/服务器/)).toBeTruthy();
  });

  it('createDatabase 未传 storage_location 时缺省 local', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 'x' }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    vi.stubGlobal('fetch', fetchMock);
    try {
      await createDatabase({
        alias: 'a',
        db_type: 'mysql' as never,
        host: 'h',
        port: 3306,
        username: 'root',
        password: 'p',
      });
      expect(fetchMock).toHaveBeenCalled();
      const body = JSON.parse(fetchMock.mock.calls[0][1].body);
      expect(body.storage_location).toBe('local');
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('连接列表渲染本机徽章，点击迁移按钮调用 migrateConfig(database)', async () => {
    const { default: ConnectionList } = await import('../components/ConnectionList');
    render(
      <ConnectionList
        onAddConfig={() => {}}
        onEditConfig={() => {}}
        onSelectTable={() => {}}
      />,
    );

    // 连接项旁渲染本机徽章
    await waitFor(() => {
      expect(screen.getAllByText(/本机/).length).toBeGreaterThan(0);
    });

    // 目标是 server（当前 local），服务器可用 → 按钮可见
    const migrateBtn = await screen.findByTitle('移到服务器');
    fireEvent.click(migrateBtn);

    await waitFor(() => {
      expect(migrateConfig).toHaveBeenCalledWith('database', 'c1', 'server');
    });
  });
});

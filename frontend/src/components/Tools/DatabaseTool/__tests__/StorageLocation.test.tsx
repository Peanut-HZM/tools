/**
 * 数据库工具存储位置接入测试
 *
 * 覆盖：连接列表渲染存储徽章、迁移按钮调用 migrateConfig('database', ...)、
 * 创建连接时提交 storage_location（API 层缺省 'local'）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
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
    updateDatabase: vi.fn().mockResolvedValue({ id: 'c1' }),
    deleteDatabase: vi.fn().mockResolvedValue(undefined),
  };
});

// ConnectionList 依赖 DatabaseToolContext / workspaceStore，单测中以固定值替换
vi.mock('../../../../contexts/DatabaseToolContext', () => ({
  useDatabaseTool: vi.fn(() => ({
    configs: [],
    currentConfig: null,
    selectConfigById: vi.fn(),
    setCurrentDatabase: vi.fn(),
    refreshConfigs: vi.fn().mockResolvedValue(undefined),
    isLoading: false,
  })),
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

// DatabaseConfigPanel 依赖 auth store / i18n / toast
vi.mock('../../../../stores', () => ({
  useAuth: () => ({ user: { id: 'u1' } }),
}));
vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}));
vi.mock('../../../../i18n', () => {
  // 两级代理：t.xxx.yyy 均返回空字符串，避免对象作为 React 子节点报错
  const leaf = new Proxy({}, { get: () => '' });
  return { useI18n: () => ({ t: new Proxy({}, { get: () => leaf }) }) };
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
    // 多个用例都会 render，显式清理避免 DOM 累积（本文件未启用全局 cleanup）
    cleanup();
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
    const { useDatabaseTool } = await import('../../../../contexts/DatabaseToolContext');
    (useDatabaseTool as ReturnType<typeof vi.fn>).mockImplementation(() => ({
      configs: [makeConfig()],
      currentConfig: null,
      selectConfigById: vi.fn(),
      setCurrentDatabase: vi.fn(),
      refreshConfigs: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
    }));

    render(
      <ConnectionList
        onAddConfig={() => {}}
        onEditConfig={() => {}}
        onSelectTable={() => {}}
      />,
    );

    // 连接项旁渲染本机徽章（compact 模式只显示图标，用 aria-label 定位）
    await waitFor(() => {
      expect(screen.getAllByLabelText(/存储位置：本机/).length).toBeGreaterThan(0);
    });

    // 目标是 server（当前 local），服务器可用 → 按钮可见
    const migrateBtn = await screen.findByTitle('移到服务器');
    fireEvent.click(migrateBtn);

    await waitFor(() => {
      expect(migrateConfig).toHaveBeenCalledWith('database', 'c1', 'server');
    });
  });

  it('编辑模式不改存储位置直接保存，请求体不含 storage_location（C1 回归）', async () => {
    const { default: DatabaseConfigPanel } = await import('../DatabaseConfigPanel');
    const { useDatabaseTool } = await import('../../../../contexts/DatabaseToolContext');
    const apiModule = await import('../../../../api/databaseToolApi');
    // 返回稳定对象：DatabaseConfigPanel 的 useEffect 依赖 configs，每次新对象会触发无限重渲染（OOM）
    const ctx = {
      configs: [{ ...makeConfig(), storage_location: 'server' as const }],
      currentConfig: null,
      selectConfigById: vi.fn(),
      setCurrentDatabase: vi.fn(),
      refreshConfigs: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
    };
    (useDatabaseTool as ReturnType<typeof vi.fn>).mockReturnValue(ctx);

    const { container } = render(<DatabaseConfigPanel editConfigId="c1" onClose={() => {}} />);

    // 等回填完成
    await waitFor(() => {
      expect(screen.getByDisplayValue('本地连接')).toBeTruthy();
    });

    // 不碰选择器，直接点保存（type=submit 按钮）
    const saveBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiModule.updateDatabase).toHaveBeenCalled();
    });
    const payload = (apiModule.updateDatabase as ReturnType<typeof vi.fn>).mock.calls[0][1];
    expect(payload.storage_location).toBeUndefined();
  });

  it('编辑模式显式改动存储位置时，请求体带上新值', async () => {
    const { default: DatabaseConfigPanel } = await import('../DatabaseConfigPanel');
    const apiModule = await import('../../../../api/databaseToolApi');
    const { useDatabaseTool } = await import('../../../../contexts/DatabaseToolContext');
    // 稳定对象，理由同上
    const ctx = {
      configs: [makeConfig()],
      currentConfig: null,
      selectConfigById: vi.fn(),
      setCurrentDatabase: vi.fn(),
      refreshConfigs: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
    };
    (useDatabaseTool as ReturnType<typeof vi.fn>).mockReturnValue(ctx);

    const { container } = render(<DatabaseConfigPanel editConfigId="c1" onClose={() => {}} />);

    // 等回填完成（alias 输入框被回填，取 name 精确定位避免多元素歧义）
    await waitFor(() => {
      expect((container.querySelector('input[name="alias"]') as HTMLInputElement).value).toBe('本地连接');
    });

    // 从 local 显式切到 server（getStorageStatus mock server_available=true，选项可见）
    const serverRadio = await screen.findByRole('radio', { name: /上传到服务器/ });
    fireEvent.click(serverRadio);

    const saveBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
    fireEvent.click(saveBtn);

    await waitFor(() => {
      const payload = (apiModule.updateDatabase as ReturnType<typeof vi.fn>).mock.calls.at(-1)?.[1];
      expect(payload?.storage_location).toBe('server');
    });
  });
});

// ConnectionPanel 单元测试
// 覆盖：列表加载、新建表单提交、编辑（password 留空不传）、行内测试按钮
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';

// mock API 模块（不触真实后端）
vi.mock('../../../../api/neo4jToolApi', () => ({
  listConnections: vi.fn(),
  createConnection: vi.fn(),
  updateConnection: vi.fn(),
  deleteConnection: vi.fn(),
  testConnection: vi.fn(),
}));

// mock toast hook
const addToastMock = vi.fn();
vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({ addToast: addToastMock }),
}));

import * as api from '../../../../api/neo4jToolApi';
import { ConnectionPanel } from '../ConnectionPanel';
import type { Neo4jConnection } from '../../../../api/neo4jToolApi';

const mockedListConnections = api.listConnections as unknown as ReturnType<typeof vi.fn>;
const mockedCreateConnection = api.createConnection as unknown as ReturnType<typeof vi.fn>;
const mockedUpdateConnection = api.updateConnection as unknown as ReturnType<typeof vi.fn>;
const mockedTestConnection = api.testConnection as unknown as ReturnType<typeof vi.fn>;

const sampleConn: Neo4jConnection = {
  id: 'conn-1',
  name: '测试连接',
  uri: 'bolt://localhost:7687',
  username: 'neo4j',
  database: 'neo4j',
  readonly: true,
};

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  activeConnectionId: null,
  onActiveConnectionChange: vi.fn(),
  onConnectionsChanged: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe('ConnectionPanel', () => {
  it('打开时加载并渲染连接列表', async () => {
    mockedListConnections.mockResolvedValueOnce([sampleConn]);

    render(<ConnectionPanel {...defaultProps} />);

    expect(screen.getByText('管理连接')).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText('测试连接')).toBeTruthy();
    });
    expect(screen.getByText('bolt://localhost:7687 · neo4j')).toBeTruthy();
  });

  it('列表为空时显示空态提示', async () => {
    mockedListConnections.mockResolvedValueOnce([]);

    render(<ConnectionPanel {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText(/暂无连接/)).toBeTruthy();
    });
  });

  it('加载失败时 toast 报错且不抛出', async () => {
    mockedListConnections.mockRejectedValueOnce(new Error('网络错误'));

    render(<ConnectionPanel {...defaultProps} />);

    await waitFor(() => {
      expect(addToastMock).toHaveBeenCalledWith(
        expect.stringContaining('加载连接列表失败'),
        'error',
      );
    });
  });

  it('新建连接：提交表单调用 createConnection 并刷新列表', async () => {
    mockedListConnections
      .mockResolvedValueOnce([]) // 首次打开
      .mockResolvedValueOnce([sampleConn]); // 保存后刷新
    mockedCreateConnection.mockResolvedValueOnce(sampleConn);

    render(<ConnectionPanel {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText(/暂无连接/)).toBeTruthy();
    });

    // 进入新建表单（头部 + 按钮的 title）
    fireEvent.click(screen.getByTitle('新建连接'));

    // 填写表单
    fireEvent.change(screen.getByPlaceholderText('我的 Neo4j'), {
      target: { value: '新连接' },
    });
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;
    fireEvent.change(passwordInput, { target: { value: 'secret-pw' } });

    fireEvent.click(screen.getByText('保存'));

    await waitFor(() => {
      expect(mockedCreateConnection).toHaveBeenCalledWith(
        expect.objectContaining({ name: '新连接', password: 'secret-pw' }),
      );
    });
    expect(defaultProps.onConnectionsChanged).toHaveBeenCalled();
  });

  it('编辑连接：password 留空则不传 password 字段', async () => {
    mockedListConnections.mockResolvedValueOnce([sampleConn]);
    mockedUpdateConnection.mockResolvedValueOnce(sampleConn);

    render(<ConnectionPanel {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('测试连接')).toBeTruthy();
    });

    // 点编辑按钮
    fireEvent.click(screen.getByTitle('编辑'));

    // 编辑表单标题出现
    expect(screen.getByText('编辑连接：测试连接')).toBeTruthy();

    // 修改名称
    const nameInput = screen.getByDisplayValue('测试连接') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: '改名后' } });

    // password 留空（不触碰 password 输入框）
    fireEvent.click(screen.getByText('保存'));

    await waitFor(() => {
      expect(mockedUpdateConnection).toHaveBeenCalledTimes(1);
    });
    const payload = mockedUpdateConnection.mock.calls[0][1] as Record<string, unknown>;
    expect(payload.name).toBe('改名后');
    expect(payload).not.toHaveProperty('password');
  });

  it('行内"测试"按钮：成功后显示版本号', async () => {
    mockedListConnections.mockResolvedValueOnce([sampleConn]);
    mockedTestConnection.mockResolvedValueOnce({
      ok: true,
      server_version: '5.20.0',
      error: null,
    });

    render(<ConnectionPanel {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('测试连接')).toBeTruthy();
    });

    fireEvent.click(screen.getByTitle('测试连接'));

    await waitFor(() => {
      expect(screen.getByText(/连接成功（版本 5\.20\.0）/)).toBeTruthy();
    });
  });

  it('行内"测试"按钮：失败时显示错误文案', async () => {
    mockedListConnections.mockResolvedValueOnce([sampleConn]);
    mockedTestConnection.mockResolvedValueOnce({
      ok: false,
      server_version: null,
      error: '无法连接到数据库，请检查地址与网络',
    });

    render(<ConnectionPanel {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('测试连接')).toBeTruthy();
    });

    fireEvent.click(screen.getByTitle('测试连接'));

    await waitFor(() => {
      expect(screen.getByText(/连接失败：无法连接到数据库/)).toBeTruthy();
    });
  });
});

import React from 'react';
import { render, fireEvent, screen, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import SSHTool from './SSHTool';

vi.mock('../../../api/sshToolApi', () => ({
  getSSHConfigs: vi.fn().mockResolvedValue([
    { id: 'cfg-1', alias: 'srv-1', host: '127.0.0.1', port: 22, username: 'root', is_active: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
  ]),
  createSSHConfig: vi.fn(),
  updateSSHConfig: vi.fn(),
  deleteSSHConfig: vi.fn(),
  buildSSHWebSocketUrl: () => 'ws://example.com/ssh',
}));
vi.mock('../../../api/authApi', () => ({ getAuthToken: () => 'token' }));
vi.mock('../../../hooks/useToast', () => ({ useToast: () => ({ addToast: vi.fn() }) }));
vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        connections: 'SSH 连接',
        addConnection: '新增',
        editConnection: '编辑',
        alias: '别名',
        host: '主机',
        port: '端口',
        username: '用户名',
        password: '密码',
        privateKey: '私钥',
        passphrase: '口令',
        group: '分组',
        connect: '连接',
        disconnect: '断开',
        connected: '已连接',
        connecting: '连接中',
        disconnected: '未连接',
        selectConnection: '选连接',
        emptyConnections: '无连接',
        confirmDeleteConnection: '删除 {alias}?',
        saveSuccess: '保存成功',
        deleteSuccess: '删除成功',
        connectionFailed: '连接失败',
        authRequired: '请先登录',
        readyForConnection: '等待连接',
        testConnection: '测试',
        testing: '测试中',
        testSuccess: '连接成功',
        testFailed: '测试失败',
        tabLimitReached: '最多保留 20 个 SSH 会话,请先关闭其他会话',
        confirmCloseTab: '断开并关闭?',
        retryConnection: '重试',
        closeTab: '关闭',
        connectionTimeout: '超时',
        sessionDisconnected: '会话已断开',
        connectionError: '连接失败: {reason}',
        tabCount: '{count} / {max}',
      },
      common: { error: '错误', cancel: '取消', confirm: '确认', save: '保存', delete: '删除', leaveBlankToKeep: '留空保持' },
    },
  }),
  interpolate: (s: string, vars: Record<string, string>) => {
    if (typeof s !== 'string') return '';
    return s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
  },
}));

vi.mock('xterm', () => ({
  Terminal: class {
    cols = 80; rows = 24;
    open = vi.fn(); loadAddon = vi.fn();
    onData = () => ({ dispose: vi.fn() });
    write = vi.fn(); writeln = vi.fn(); clear = vi.fn();
    dispose = vi.fn(); focus = vi.fn();
  },
}));
vi.mock('xterm-addon-fit', () => ({ FitAddon: class { fit = vi.fn(); } }));
vi.mock('xterm-addon-web-links', () => ({ WebLinksAddon: class {} }));

describe('SSHTool - Tab 管理', () => {
  afterEach(() => { cleanup(); });
  beforeEach(() => {
    const ws = vi.fn().mockImplementation(() => ({
      readyState: 1, send: vi.fn(), close: vi.fn(),
      onopen: null, onmessage: null, onclose: null, onerror: null,
    }));
    vi.stubGlobal('WebSocket', ws);
  });

  it('点击侧边栏连接新增一个 tab,再点一次新增第二个 tab', async () => {
    render(<SSHTool />);
    await waitFor(() => expect(screen.getAllByText('srv-1').length).toBeGreaterThanOrEqual(1));
    // 第一次点击左侧列表项(第一个匹配项)
    fireEvent.click(screen.getAllByText('srv-1')[0]);
    expect(await screen.findByText('1 / 20')).toBeTruthy();
    // 第二次点击左侧列表项(第一个匹配项)
    fireEvent.click(screen.getAllByText('srv-1')[0]);
    expect(await screen.findByText('2 / 20')).toBeTruthy();
  });
});

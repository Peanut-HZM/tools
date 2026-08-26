import React from 'react';
import { render, fireEvent, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { TabBar } from './TabBar';
import { SSHSessionTab } from './types';

vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        confirmCloseTab: '确认断开?',
        tabCount: '{count} / {max}',
        closeTab: '关闭',
        connected: '已连接',
        connecting: '连接中',
        disconnected: '未连接',
        connectionFailed: '连接失败',
        connectionError: '连接失败: {reason}',
      },
      common: { cancel: '取消', confirm: '确认' },
    },
  }),
  interpolate: (s: string, vars: Record<string, string>) => {
    if (typeof s !== 'string') return '';
    return s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
  },
}));

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const makeTab = (tabId: string, status: 'disconnected' | 'connecting' | 'connected' | 'error' = 'connected'): { tab: SSHSessionTab; status: 'disconnected' | 'connecting' | 'connected' | 'error' } => ({
  tab: {
    tabId,
    configId: `cfg-${tabId}`,
    configSnapshot: { alias: `srv-${tabId}`, host: '127.0.0.1', port: 22, username: 'root' },
    createdAt: Date.now(),
  },
  status,
});

describe('TabBar', () => {
  it('渲染 tab 数量与标题', () => {
    const tabs = [makeTab('a'), makeTab('b')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={Object.fromEntries(tabs.map(t => [t.tab.tabId, t.status]))}
        activeTabId="a"
        onActivate={() => {}}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/srv-a/)).toBeTruthy();
    expect(screen.getByText(/srv-b/)).toBeTruthy();
    expect(screen.getByText('2 / 20')).toBeTruthy();
  });

  it('点击 tab 触发 onActivate', () => {
    const onActivate = vi.fn();
    const tabs = [makeTab('a'), makeTab('b')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={Object.fromEntries(tabs.map(t => [t.tab.tabId, t.status]))}
        activeTabId="a"
        onActivate={onActivate}
        onClose={() => {}}
      />
    );
    fireEvent.click(screen.getByText(/srv-b/));
    expect(onActivate).toHaveBeenCalledWith('b');
  });

  it('connected 状态点击 × 触发 confirm,取消则不调用 onClose', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const onClose = vi.fn();
    const tabs = [makeTab('a')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{ a: 'connected' }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /关闭/ }));
    expect(confirmSpy).toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('connected 状态点击 × 触发 confirm,确认后调用 onClose', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onClose = vi.fn();
    const tabs = [makeTab('a')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{ a: 'connected' }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /关闭/ }));
    expect(onClose).toHaveBeenCalledWith('a');
    confirmSpy.mockRestore();
  });

  it('disconnected 状态点击 × 不弹 confirm,直接调用 onClose', () => {
    const confirmSpy = vi.spyOn(window, 'confirm');
    const onClose = vi.fn();
    const tabs = [makeTab('a')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{ a: 'disconnected' }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /关闭/ }));
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledWith('a');
    confirmSpy.mockRestore();
  });

  it('状态点颜色按 status 渲染', () => {
    const tabs = [makeTab('a'), makeTab('b'), makeTab('c'), makeTab('d')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{
          a: 'connected',
          b: 'connecting',
          c: 'error',
          d: 'disconnected',
        }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={() => {}}
      />
    );
    const dot = (tabId: string) => screen.getByTestId(`tab-dot-${tabId}`);
    expect(dot('a').className).toContain('bg-success');
    expect(dot('b').className).toContain('bg-warning');
    expect(dot('c').className).toContain('bg-danger');
    expect(dot('d').className).toContain('bg-surface-3');
  });
});

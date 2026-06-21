import React from 'react';
import { render, act, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TerminalPanel } from './TerminalPanel';

vi.mock('../../../api/authApi', () => ({ getAuthToken: () => 'token' }));
vi.mock('../../../api/sshToolApi', () => ({
  buildSSHWebSocketUrl: () => 'ws://example.com/ssh',
}));
vi.mock('../../../hooks/useToast', () => ({ useToast: () => ({ addToast: vi.fn() }) }));
vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        authRequired: 'authRequired',
        connectionFailed: 'connectionFailed',
        connected: 'connected',
        connecting: 'connecting',
        disconnected: 'disconnected',
        connect: 'connect',
        disconnect: 'disconnect',
        selectConnection: 'selectConnection',
      },
    },
  }),
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

let lastWsInstance: any;
let wsCtor: any;

const setupWs = () => {
  wsCtor = vi.fn().mockImplementation(() => {
    const inst = {
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null as any, onmessage: null as any, onclose: null as any, onerror: null as any,
    };
    lastWsInstance = inst;
    return inst;
  });
  vi.stubGlobal('WebSocket', wsCtor);
};

const DEFAULT_PROPS = {
  tabId: 'tab-1',
  configId: 'cfg-1',
  createdAt: 1000,
  isActive: true,
  onStatusChange: vi.fn(),
  onRetry: vi.fn(),
};

describe('TerminalPanel', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  // ============ 真实计时器用例 ============

  it('挂载后建立 WebSocket 连接', async () => {
    setupWs();
    render(<TerminalPanel {...DEFAULT_PROPS} />);
    expect(wsCtor).toHaveBeenCalled();
  });

  it('收到后端 {"type": "error"} 后 status 变 error', async () => {
    setupWs();
    const onStatusChange = vi.fn();
    render(<TerminalPanel {...DEFAULT_PROPS} onStatusChange={onStatusChange} />);
    expect(lastWsInstance).toBeTruthy();
    act(() => { lastWsInstance.onopen?.({}); });
    act(() => {
      lastWsInstance.onmessage?.({ data: JSON.stringify({ type: 'error', message: 'auth failed' }) });
    });
    const errorCalls = onStatusChange.mock.calls.filter(c => c[1] === 'error');
    expect(errorCalls.length).toBeGreaterThan(0);
  });

  it('收到后端 {"type": "exit"} 后 status 变 disconnected', async () => {
    setupWs();
    const onStatusChange = vi.fn();
    render(<TerminalPanel {...DEFAULT_PROPS} onStatusChange={onStatusChange} />);
    expect(lastWsInstance).toBeTruthy();
    act(() => { lastWsInstance.onopen?.({}); });
    act(() => { lastWsInstance.onmessage?.({ data: JSON.stringify({ type: 'exit' }) }); });
    const dcCalls = onStatusChange.mock.calls.filter(c => c[1] === 'disconnected');
    expect(dcCalls.length).toBeGreaterThan(0);
  });

  // 注:isActive 切换时发送 resize 消息的测试,因 rAF/setTimeout 在 jsdom 里时序不稳定,
  // 留到端到端手动验证。

  // ============ fake timers 用例(心跳判活)============

  it('90s 无任何数据 → 判死 → 主动 close + status error', () => {
    vi.useFakeTimers();
    setupWs();
    const onStatusChange = vi.fn();
    render(<TerminalPanel {...DEFAULT_PROPS} onStatusChange={onStatusChange} />);
    expect(wsCtor).toHaveBeenCalled();
    act(() => { lastWsInstance.onopen?.({}); });
    // 心跳定时器 5s 检查一次,推进 90s
    act(() => { vi.advanceTimersByTime(95_000); });
    expect(lastWsInstance.close).toHaveBeenCalled();
    const errorCalls = onStatusChange.mock.calls.filter(c => c[1] === 'error');
    expect(errorCalls.length).toBeGreaterThan(0);
  });

  it('收到 pong 重置判活计时器,不会触发 close', () => {
    vi.useFakeTimers();
    setupWs();
    render(<TerminalPanel {...DEFAULT_PROPS} />);
    expect(wsCtor).toHaveBeenCalled();
    act(() => { lastWsInstance.onopen?.({}); });
    for (let i = 0; i < 3; i++) {
      act(() => { vi.advanceTimersByTime(30_000); });
      act(() => { lastWsInstance.onmessage?.({ data: JSON.stringify({ type: 'pong' }) }); });
    }
    expect(lastWsInstance.close).not.toHaveBeenCalled();
  });
});

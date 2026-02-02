import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TerminalPanel } from './TerminalPanel';

vi.mock('../../../api/authApi', () => ({
  getAuthToken: () => 'token'
}));

vi.mock('../../../api/sshToolApi', () => ({
  buildSSHWebSocketUrl: () => 'ws://example.com/ssh'
}));

vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ addToast: vi.fn() })
}));

vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        authRequired: 'authRequired',
        connectionFailed: 'connectionFailed',
        readyForConnection: 'readyForConnection',
        connected: 'connected',
        connecting: 'connecting',
        disconnected: 'disconnected',
        connect: 'connect',
        disconnect: 'disconnect',
        selectConnection: 'selectConnection'
      }
    }
  })
}));

const focusSpy = vi.hoisted(() => vi.fn());
const writelnSpy = vi.hoisted(() => vi.fn());

vi.mock('xterm', () => ({
  Terminal: class {
    cols = 80;
    rows = 24;
    open = vi.fn();
    loadAddon = vi.fn();
    onData = () => ({ dispose: vi.fn() });
    write = vi.fn();
    writeln = writelnSpy;
    clear = vi.fn();
    dispose = vi.fn();
    focus = focusSpy;
  }
}));

vi.mock('xterm-addon-fit', () => ({
  FitAddon: class {
    fit = vi.fn();
  }
}));

vi.mock('xterm-addon-web-links', () => ({
  WebLinksAddon: class {}
}));

const config = {
  id: 'config-1',
  alias: 'server',
  host: '127.0.0.1',
  port: 22,
  username: 'root',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

describe('TerminalPanel', () => {
  beforeEach(() => {
    writelnSpy.mockClear();
    const ws = vi.fn().mockImplementation(() => ({
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null
    }));
    vi.stubGlobal('WebSocket', ws);
  });

  it('auto connects when config is selected', async () => {
    render(<TerminalPanel config={config} />);
    await waitFor(() => {
      expect(WebSocket).toHaveBeenCalled();
    });
  });

  it('connects after config is selected later', async () => {
    const { rerender } = render(<TerminalPanel config={null} />);
    rerender(<TerminalPanel config={config} />);
    await waitFor(() => {
      expect(WebSocket).toHaveBeenCalled();
    });
  });

  it('focuses terminal on click', () => {
    const { getAllByTestId } = render(<TerminalPanel config={config} />);
    const terminal = getAllByTestId('ssh-terminal')[0];
    fireEvent.click(terminal);
    expect(focusSpy).toHaveBeenCalled();
  });

  it('shows close reason on disconnect', async () => {
    const ws = vi.fn().mockImplementation(() => ({
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null
    }));
    vi.stubGlobal('WebSocket', ws);
    render(<TerminalPanel config={config} />);
    await waitFor(() => {
      expect(WebSocket).toHaveBeenCalled();
    });
    const instance = ws.mock.results[0]?.value;
    instance.onclose?.({ code: 4000, reason: 'Auth failed' });
    const calls = writelnSpy.mock.calls.flat().join(' ');
    expect(calls).toContain('Auth failed');
  });
});

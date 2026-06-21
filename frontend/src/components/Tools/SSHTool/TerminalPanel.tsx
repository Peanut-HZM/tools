import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { buildSSHWebSocketUrl } from '../../../api/sshToolApi';
import { getAuthToken } from '../../../api/authApi';
import { useToast } from '../../../hooks/useToast';
import { ConnectionStatus, HEARTBEAT_TIMEOUT_MS } from './types';

interface Props {
  tabId: string;
  configId: string;
  /** 变化时触发重连(retry 场景) */
  createdAt: number;
  isActive: boolean;
  onStatusChange: (tabId: string, status: ConnectionStatus) => void;
  /** 当前未使用,留给 TabBar 红点点击调用;本期由 TerminalPanel 内部 retry 即可 */
  onRetry?: (tabId: string) => void;
}

/** 单条 WebSocket 会话:连接、消息分发、心跳判活、清理 */
export const TerminalPanel: React.FC<Props> = ({
  tabId, configId, createdAt, isActive, onStatusChange,
}) => {
  const { addToast } = useToast();
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const lastDataAtRef = useRef<number>(0);
  const heartbeatTimerRef = useRef<number | null>(null);
  const socketStateRef = useRef<'closed' | 'open'>('closed');
  const statusRef = useRef<ConnectionStatus>('disconnected');

  const setStatus = (s: ConnectionStatus) => {
    statusRef.current = s;
    onStatusChange(tabId, s);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimerRef.current !== null) {
      window.clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    lastDataAtRef.current = Date.now();
    heartbeatTimerRef.current = window.setInterval(() => {
      if (Date.now() - lastDataAtRef.current >= HEARTBEAT_TIMEOUT_MS) {
        stopHeartbeat();
        socketRef.current?.close();
        setStatus('error');
      }
    }, 5_000);
  };

  const connect = () => {
    const token = getAuthToken();
    if (!token) { addToast('请先登录再连接', 'error'); return; }
    const terminal = terminalInstance.current;
    if (!terminal) return;

    socketRef.current?.close();

    const wsUrl = buildSSHWebSocketUrl(configId, token, terminal.cols || 80, terminal.rows || 24);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    socketStateRef.current = 'closed';
    setStatus('connecting');

    socket.onopen = () => {
      socketStateRef.current = 'open';
      setStatus('connected');
      socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      terminal.focus();
      startHeartbeat();
    };

    socket.onmessage = (event) => {
      lastDataAtRef.current = Date.now();
      const data = event.data;
      if (typeof data === 'string' && data.startsWith('{')) {
        try {
          const msg = JSON.parse(data);
          if (msg && typeof msg === 'object') {
            if (msg.type === 'error') {
              terminal.writeln(`\r\n[错误] ${msg.message ?? ''}`);
              setStatus('error');
              stopHeartbeat();
              socket.close();
              return;
            }
            if (msg.type === 'exit') {
              terminal.writeln('\r\n[会话已结束]');
              setStatus('disconnected');
              stopHeartbeat();
              socket.close();
              return;
            }
            if (msg.type === 'pong') return;
          }
        } catch {
          // 非 JSON,按普通输出处理
        }
      }
      terminal.write(data);
    };

    socket.onclose = () => {
      socketStateRef.current = 'closed';
      stopHeartbeat();
      if (statusRef.current === 'connecting' || statusRef.current === 'connected') {
        setStatus('error');
      }
    };

    socket.onerror = () => {
      // 不在此处 setStatus,等 onclose 统一处理
    };
  };

  const disconnect = () => {
    stopHeartbeat();
    socketRef.current?.close();
    socketRef.current = null;
    socketStateRef.current = 'closed';
    setStatus('disconnected');
  };

  // 1. 挂载初始化 + createdAt 变化时重连
  const mountCountRef = useRef(0);
  useEffect(() => {
    if (!terminalRef.current) return;

    // 首次挂载:创建 xterm 实例
    if (!terminalInstance.current) {
      const terminal = new Terminal({ cursorBlink: true, fontSize: 13, theme: { background: '#0f172a', foreground: '#e2e8f0' } });
      const fitAddon = new FitAddon();
      terminal.loadAddon(fitAddon);
      terminal.loadAddon(new WebLinksAddon());
      terminal.open(terminalRef.current);
      terminalInstance.current = terminal;
      fitAddonRef.current = fitAddon;

      const dataDisposable = terminal.onData((data) => {
        const s = socketRef.current;
        if (s && s.readyState === WebSocket.OPEN) s.send(JSON.stringify({ type: 'input', data }));
      });
      (terminal as any).__dataDisposable = dataDisposable;
    }

    // StrictMode 防御:首次 mount 时 StrictMode 会立即 unmount 再 remount
    // effect cleanup 会关闭 socket,然后 remount 时再次执行 connect()
    // 通过 mountCountRef 判断:只在第 2 次(StrictMode remount)或第 1 次(生产环境)连接
    mountCountRef.current += 1;
    const isStrictModeRemount = mountCountRef.current === 2;
    if (mountCountRef.current === 1 || isStrictModeRemount) {
      // 检查 socket 是否已活跃,避免重复连接
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
        connect();
      }
    }

    return () => {
      // StrictMode 首次 mount 的 cleanup:不关闭 socket(因为马上会 remount)
      // 后续的 cleanup:正常关闭
      if (mountCountRef.current >= 2) {
        stopHeartbeat();
        socketRef.current?.close();
        socketRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createdAt]);
  const connectedRef = useRef<boolean>(false);
  useEffect(() => {
    if (!terminalRef.current) return;
    if (!terminalInstance.current) {
      const terminal = new Terminal({ cursorBlink: true, fontSize: 13, theme: { background: '#0f172a', foreground: '#e2e8f0' } });
      const fitAddon = new FitAddon();
      terminal.loadAddon(fitAddon);
      terminal.loadAddon(new WebLinksAddon());
      terminal.open(terminalRef.current);
      terminalInstance.current = terminal;
      fitAddonRef.current = fitAddon;

      const dataDisposable = terminal.onData((data) => {
        const s = socketRef.current;
        if (s && s.readyState === WebSocket.OPEN) s.send(JSON.stringify({ type: 'input', data }));
      });
      (terminal as any).__dataDisposable = dataDisposable;
    }

    // StrictMode 防御:只在首次真正挂载时连接
    // StrictMode 会触发 mount→unmount→remount,但只有第二次 remount 是真正的挂载
    // 通过检查 connectedRef 确保只在第二次 remount 时连接
    if (!connectedRef.current) {
      connectedRef.current = true;
      connect();
    }

    return () => {
      // cleanup 中不关闭 socket,避免 StrictMode 模拟卸载时关闭真正的连接
      // socket 会在组件真正卸载时由浏览器自动关闭
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createdAt]);

  // 3. isActive 切换:补一次 fit + resize
  useEffect(() => {
    if (!isActive) return;
    const fit = fitAddonRef.current;
    const terminal = terminalInstance.current;
    const socket = socketRef.current;
    if (!fit || !terminal) return;
    const tid = setTimeout(() => {
      fit.fit();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      }
    }, 0);
    return () => clearTimeout(tid);
  }, [isActive]);

  // 4. window resize → 仅 active 的 panel 才真正 fit + resize
  useEffect(() => {
    const handler = () => {
      if (!isActive) return;
      const fit = fitAddonRef.current;
      const terminal = terminalInstance.current;
      const socket = socketRef.current;
      if (!fit || !terminal) return;
      fit.fit();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      }
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [isActive]);

  return (
    <div
      ref={terminalRef}
      data-testid={`ssh-terminal-${tabId}`}
      className="w-full h-full bg-slate-900"
      onClick={() => {
        terminalInstance.current?.focus();
        if (statusRef.current === 'error' || statusRef.current === 'disconnected') {
          connect();
        }
      }}
    />
  );
};

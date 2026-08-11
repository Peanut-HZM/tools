import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { buildSSHWebSocketUrl } from '../../../api/sshToolApi';
import { getAuthToken } from '../../../api/authApi';
import { useToast } from '../../../hooks/useToast';
import { ConnectionStatus, HEARTBEAT_TIMEOUT_MS } from '../../Tools/SSHTool/types';

interface Props {
  tabId: string;
  configId: string;
  createdAt: number;
  isActive: boolean;
  onStatusChange: (tabId: string, status: ConnectionStatus) => void;
  onRetry?: (tabId: string) => void;
}

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

    // 先关闭旧 socket
    socketRef.current?.close();
    socketRef.current = null;

    const wsUrl = buildSSHWebSocketUrl(configId, token, terminal.cols || 80, terminal.rows || 24);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    setStatus('connecting');

    socket.onopen = () => {
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
          if (!msg || typeof msg !== 'object') { terminal.write(data); return; }
          if (msg.type === 'error') {
            terminal.writeln(`\r\n[错误] ${msg.message ?? ''}`);
            setStatus('error'); stopHeartbeat(); socket.close(); return;
          }
          if (msg.type === 'exit') {
            terminal.writeln('\r\n[会话已结束]');
            setStatus('disconnected'); stopHeartbeat(); socket.close(); return;
          }
          if (msg.type === 'pong') return;
        } catch {
          // 非 JSON,按普通输出处理
        }
      }
      terminal.write(data);
    };

    socket.onclose = () => {
      // 只处理当前活跃 socket 的关闭,忽略已被替换的旧 socket
      if (socketRef.current !== socket) return;
      stopHeartbeat();
      if (statusRef.current === 'connecting' || statusRef.current === 'connected') {
        setStatus('error');
      }
    };

    socket.onerror = () => {
      // 等 onclose 统一处理
    };
  };

  // 1. terminal 创建(只执行一次)
  useEffect(() => {
    if (!terminalRef.current) return;
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

    return () => {
      dataDisposable.dispose();
      stopHeartbeat();
      socketRef.current?.close();
      socketRef.current = null;
      terminal.dispose();
      terminalInstance.current = null;
      fitAddonRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 2. 连接管理(首次挂载 + createdAt 变化时重连)
  useEffect(() => {
    if (!terminalInstance.current) return;
    connect();

    return () => {
      stopHeartbeat();
      socketRef.current?.close();
      socketRef.current = null;
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

  // 4. window resize
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

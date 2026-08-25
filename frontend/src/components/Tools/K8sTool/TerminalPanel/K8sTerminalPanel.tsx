/**
 * K8s Pod Exec 终端面板
 *
 * 基于 xterm.js 实现 K8s Pod 交互式终端
 * 复用 SSH TerminalPanel 的架构，但使用 buildExecWebSocketUrl 构造连接 URL
 * 支持容器选择 + Shell 命令切换（/bin/sh / /bin/bash）
 */
import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { useI18n } from '../../../../i18n';
import { useToast } from '../../../../hooks/useToast';
import { getAuthToken } from '../../../../api/authApi';
import { buildExecWebSocketUrl } from '../../../../api/k8sToolApi';
import type { K8sContainerInfo } from '../types';
import { Button } from '@/components/ui/Button';

interface Props {
  configId: string;
  podName: string;
  namespace: string;
  containers: K8sContainerInfo[];
  isActive: boolean;
}

type ShellCommand = '/bin/sh' | '/bin/bash';

export const K8sTerminalPanel: React.FC<Props> = ({
  configId, podName, namespace, containers, isActive,
}) => {
  const { t } = useI18n();
  const tt = t.tools['k8s-tool'].terminal;
  const { addToast } = useToast();

  const [selectedContainer, setSelectedContainer] = useState<string>(
    containers[0]?.name || ''
  );
  const [command, setCommand] = useState<ShellCommand>('/bin/sh');
  // createdAt 变化时触发重连
  const [createdAt, setCreatedAt] = useState<number>(Date.now());

  const terminalRef = useRef<HTMLDivElement | null>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  /** 建立 WebSocket 连接 */
  const connect = () => {
    const token = getAuthToken();
    if (!token) {
      addToast(t.tools['k8s-tool'].terminal.connectFailed, 'error');
      return;
    }

    const terminal = terminalInstance.current;
    if (!terminal) return;

    // 关闭旧连接
    socketRef.current?.close();
    socketRef.current = null;

    const wsUrl = buildExecWebSocketUrl(
      configId,
      podName,
      namespace,
      selectedContainer || undefined,
      command,
    );

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    terminal.writeln(`\r\n\x1b[90m[连接到 ${podName}${selectedContainer ? `/${selectedContainer}` : ''}...]\x1b[0m`);

    socket.onopen = () => {
      terminal.writeln('\x1b[92m[已连接]\x1b[0m\r\n');
      // 发送初始 resize
      socket.send(
        JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows })
      );
      terminal.focus();
    };

    socket.onmessage = (event) => {
      const data = event.data;

      // JSON 消息处理（错误、退出、pong 等控制消息）
      if (typeof data === 'string' && data.startsWith('{')) {
        try {
          const msg = JSON.parse(data);
          if (!msg || typeof msg !== 'object') {
            terminal.write(data);
            return;
          }
          if (msg.type === 'error') {
            terminal.writeln(`\r\n\x1b[91m[错误] ${msg.message ?? ''}\x1b[0m`);
            socket.close();
            return;
          }
          if (msg.type === 'exit') {
            terminal.writeln('\r\n\x1b[90m[会话已结束]\x1b[0m');
            socket.close();
            return;
          }
          if (msg.type === 'pong') return;
          // output 类型，写入终端
          if (msg.type === 'output' && msg.data) {
            terminal.write(msg.data);
            return;
          }
        } catch {
          // 非 JSON，按普通输出处理
        }
      }

      // 普通文本，直接写入终端
      terminal.write(data);
    };

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
        terminal.writeln('\r\n\x1b[90m[连接已断开]\x1b[0m');
      }
    };

    socket.onerror = () => {
      // 等 onclose 统一处理
    };
  };

  // 初始化 xterm（只执行一次）
  useEffect(() => {
    if (!terminalRef.current) return;

    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: '"JetBrains Mono", "Fira Code", Consolas, monospace',
      theme: {
        background: '#0f172a',
        foreground: '#e2e8f0',
        cursor: '#94a3b8',
        selectionBackground: '#334155',
      },
    });

    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(new WebLinksAddon());
    terminal.open(terminalRef.current);
    terminalInstance.current = terminal;
    fitAddonRef.current = fitAddon;

    // 用户输入 → 发送到 WebSocket
    const dataDisposable = terminal.onData((data) => {
      const s = socketRef.current;
      if (s && s.readyState === WebSocket.OPEN) {
        s.send(JSON.stringify({ type: 'input', data }));
      }
    });

    return () => {
      dataDisposable.dispose();
      socketRef.current?.close();
      socketRef.current = null;
      terminal.dispose();
      terminalInstance.current = null;
      fitAddonRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 连接管理：首次挂载 + createdAt 变化时重连
  useEffect(() => {
    if (!terminalInstance.current) return;
    connect();

    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createdAt]);

  // isActive 切换时执行 fit + resize + focus
  useEffect(() => {
    if (!isActive) return;
    const fit = fitAddonRef.current;
    const terminal = terminalInstance.current;
    const socket = socketRef.current;
    if (!fit || !terminal) return;

    const tid = setTimeout(() => {
      fit.fit();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows })
        );
      }
      // 自动聚焦终端，确保键盘输入可用
      terminal.focus();
    }, 0);
    return () => clearTimeout(tid);
  }, [isActive]);

  // 窗口 resize
  useEffect(() => {
    const handler = () => {
      if (!isActive) return;
      const fit = fitAddonRef.current;
      const terminal = terminalInstance.current;
      const socket = socketRef.current;
      if (!fit || !terminal) return;
      fit.fit();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows })
        );
      }
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [isActive]);

  /** 点击重连按钮 */
  const handleReconnect = () => {
    setCreatedAt(Date.now());
  };

  return (
    <div className="h-full flex flex-col bg-canvas">
      {/* 工具栏：容器选择 + Shell 切换 + 重连 */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-surface-1/50 shrink-0">
        {/* 容器选择 */}
        {containers.length > 1 && (
          <select
            value={selectedContainer}
            onChange={(e) => setSelectedContainer(e.target.value)}
            className="px-2 py-1 text-xs bg-surface-1 border border-border text-ink-muted rounded focus:outline-none focus:border-blue-500"
          >
            {containers.map((c) => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>
        )}

        {/* Shell 切换 */}
        <select
          value={command}
          onChange={(e) => setCommand(e.target.value as ShellCommand)}
          className="px-2 py-1 text-xs bg-surface-1 border border-border text-ink-muted rounded focus:outline-none focus:border-blue-500"
        >
          <option value="/bin/sh">/bin/sh</option>
          <option value="/bin/bash">/bin/bash</option>
        </select>

        {/* 重连按钮 */}
        <Button
          variant="secondary"
          size="sm"
          onClick={handleReconnect}
          className="h-7 px-2"
        >
          <i className="fas fa-redo text-xs"></i>
          {tt.reconnect}
        </Button>
      </div>

      {/* 终端区域 */}
      <div
        ref={terminalRef}
        className="flex-1 bg-canvas cursor-text"
        onClick={() => terminalInstance.current?.focus()}
      />
    </div>
  );
};
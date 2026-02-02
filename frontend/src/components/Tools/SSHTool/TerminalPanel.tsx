import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { SSHConfig, buildSSHWebSocketUrl } from '../../../api/sshToolApi';
import { getAuthToken } from '../../../api/authApi';
import { useI18n } from '../../../i18n';
import { useToast } from '../../../hooks/useToast';

interface Props {
  config?: SSHConfig | null;
}

export const TerminalPanel: React.FC<Props> = ({ config }) => {
  const { t } = useI18n();
  const { addToast } = useToast();
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [terminalReady, setTerminalReady] = useState(false);

  const connect = (force = false) => {
    if (!config) return;
    if (!force && (status === 'connected' || status === 'connecting')) return;
    const token = getAuthToken();
    if (!token) {
      addToast(t.ssh.authRequired, 'error');
      return;
    }
    const terminal = terminalInstance.current;
    if (!terminal) return;
    const cols = terminal.cols || 80;
    const rows = terminal.rows || 24;
    const wsUrl = buildSSHWebSocketUrl(config.id, token, cols, rows);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    setStatus('connecting');

    socket.onopen = () => {
      setStatus('connected');
      socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      terminal.focus();
      terminal.writeln(`${config.username}@${config.host}:${config.port} connected`);
    };
    socket.onmessage = (event) => {
      terminal.write(event.data);
    };
    socket.onclose = (event) => {
      setStatus('disconnected');
      const reason = event.reason || 'Connection closed';
      terminal.writeln(`Disconnected (${event.code}): ${reason}`);
    };
    socket.onerror = () => {
      setStatus('disconnected');
      addToast(t.ssh.connectionFailed, 'error');
      terminal.writeln(t.ssh.connectionFailed);
    };
  };

  const disconnect = () => {
    socketRef.current?.close();
    socketRef.current = null;
    setStatus('disconnected');
  };

  useEffect(() => {
    if (!terminalRef.current || terminalInstance.current) return;
    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      theme: {
        background: '#0f172a',
        foreground: '#e2e8f0'
      }
    });
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);
    terminal.open(terminalRef.current);
    fitAddon.fit();
    terminalInstance.current = terminal;
    fitAddonRef.current = fitAddon;
    setTerminalReady(true);
    terminal.focus();

    const resizeHandler = () => {
      fitAddon.fit();
      const socket = socketRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      }
    };
    window.addEventListener('resize', resizeHandler);

    const dataDisposable = terminal.onData((data) => {
      const socket = socketRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }));
      }
    });

    return () => {
      dataDisposable.dispose();
      window.removeEventListener('resize', resizeHandler);
      terminal.dispose();
      terminalInstance.current = null;
      fitAddonRef.current = null;
    };
  }, []);

  useEffect(() => {
    disconnect();
    const terminal = terminalInstance.current;
    if (terminal) {
      terminal.clear();
      if (config) {
        terminal.writeln(`${t.ssh.readyForConnection} ${config.username}@${config.host}:${config.port}`);
      }
    }
  }, [config?.id]);

  useEffect(() => {
    if (terminalReady && config) {
      connect(true);
    }
  }, [terminalReady, config?.id]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900">
        <div className="text-sm text-slate-300">
          {config ? `${config.alias} · ${config.username}@${config.host}:${config.port}` : t.ssh.selectConnection}
        </div>
        <div className="flex items-center space-x-2">
          <span className={`text-xs px-2 py-1 rounded-full ${
            status === 'connected' ? 'bg-green-500/20 text-green-300' : status === 'connecting' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-slate-700 text-slate-300'
          }`}>
            {status === 'connected' ? t.ssh.connected : status === 'connecting' ? t.ssh.connecting : t.ssh.disconnected}
          </span>
          {config && status !== 'connected' ? (
            <button
              onClick={() => connect()}
              className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              {t.ssh.connect}
            </button>
          ) : config ? (
            <button
              onClick={disconnect}
              className="px-3 py-1.5 text-xs rounded bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors"
            >
              {t.ssh.disconnect}
            </button>
          ) : null}
        </div>
      </div>
      <div className="flex-1 bg-slate-900 relative">
        <div
          ref={terminalRef}
          data-testid="ssh-terminal"
          className="w-full h-full"
          onClick={() => {
            const terminal = terminalInstance.current;
            if (terminal) {
              terminal.focus();
            }
            if (config && status === 'disconnected') {
              connect(true);
            }
          }}
        />
        {!config && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 pointer-events-none">
            <i className="fas fa-terminal text-6xl mb-4 opacity-20"></i>
            <p className="text-lg">{t.ssh.selectConnection}</p>
          </div>
        )}
      </div>
    </div>
  );
};

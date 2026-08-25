/**
 * K8s 日志查看器 - WebSocket 实时日志流
 *
 * 使用 api.buildLogsWebSocketUrl() 构造 WebSocket URL
 * 功能：容器选择、follow 实时跟随、搜索高亮（正则）、下载日志、清空显示
 * 使用可滚动 div 实现日志显示，自动限制最大行数防止内存溢出
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useI18n } from '../../../../i18n';
import { useToast } from '../../../../hooks/useToast';
import { buildLogsWebSocketUrl, downloadPodLogs } from '../../../../api/k8sToolApi';
import type { K8sContainerInfo } from '../types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface Props {
  configId: string;
  podName: string;
  namespace: string;
  containers: K8sContainerInfo[];
}

// 最多保留日志行数防止内存溢出
const MAX_LINES = 10000;

// 重连延迟（毫秒）
const RECONNECT_DELAY = 2000;

/** 检测是否为日志流错误帧 */
function isLogStreamError(text: string): boolean {
  if (!text.startsWith('{"type":"error"')) return false;
  try {
    const parsed = JSON.parse(text);
    return parsed.code === 'LOG_STREAM_ERROR';
  } catch {
    return false;
  }
}

export const LogsViewer: React.FC<Props> = ({
  configId, podName, namespace, containers,
}) => {
  const { t } = useI18n();
  const lt = t.tools['k8s-tool'].logs;
  const { addToast } = useToast();

  // 日志状态
  const [lines, setLines] = useState<string[]>([]);
  const [selectedContainer, setSelectedContainer] = useState<string>(
    containers[0]?.name || ''
  );
  const [follow, setFollow] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [tailLines, setTailLines] = useState(1000);  // 默认显示 1000 行
  const [downloading, setDownloading] = useState(false);

  // Refs
  const socketRef = useRef<WebSocket | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const bufferRef = useRef<string[]>([]);
  const rafIdRef = useRef<number | null>(null);
  const followRef = useRef(follow);
  useEffect(() => { followRef.current = follow; }, [follow]);

  // 使用 requestAnimationFrame 批量追加日志，避免高频 setState
  const flushBuffer = useCallback(() => {
    rafIdRef.current = null;
    if (bufferRef.current.length === 0) return;
    const newLines = bufferRef.current;
    bufferRef.current = [];
    setLines((prev) => {
      const merged = [...prev, ...newLines];
      return merged.length > MAX_LINES
        ? merged.slice(merged.length - MAX_LINES)
        : merged;
    });
  }, []);

  // 连接 WebSocket
  const connect = useCallback(() => {
    socketRef.current?.close();

    const wsUrl = buildLogsWebSocketUrl(
      configId,
      podName,
      namespace,
      selectedContainer || undefined,
      tailLines,
      true, // follow
    );

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const text = typeof event.data === 'string' ? event.data : '';
      // 过滤 LOG_STREAM_ERROR 错误帧，不显示为日志
      if (isLogStreamError(text)) {
        console.warn('Log stream error:', text);
        return;
      }
      const newLines = text.split('\n');
      bufferRef.current.push(...newLines);
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(flushBuffer);
      }
    };

    socket.onerror = () => {};

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
        // follow 模式下自动重连
        if (followRef.current) {
          setTimeout(() => {
            if (followRef.current && socketRef.current === null) {
              connect();
            }
          }, RECONNECT_DELAY);
        }
      }
    };
  }, [configId, podName, namespace, selectedContainer, tailLines, flushBuffer]);

  useEffect(() => {
    setLines([]);
    connect();
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
    };
  }, [connect]);

  // follow 模式：自动滚动到底部
  useEffect(() => {
    if (!follow) return;
    const el = listRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [lines, follow]);

  /** 搜索正则（非法时忽略） */
  const searchRegex = (() => {
    if (!searchText) return null;
    try {
      return new RegExp(searchText, 'gi');
    } catch {
      return null;
    }
  })();

  /** 高亮匹配文本 */
  const highlightLine = useCallback(
    (text: string, lineIdx: number): React.ReactNode => {
      if (!searchRegex || !text) {
        return <span className="text-ink-muted">{text || ' '}</span>;
      }

      const regex = new RegExp(searchRegex.source, 'gi');
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match: RegExpExecArray | null;

      while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) {
          parts.push(
            <span key={`n-${lineIdx}-${lastIndex}`}>
              {text.slice(lastIndex, match.index)}
            </span>
          );
        }
        parts.push(
          <span
            key={`h-${lineIdx}-${match.index}`}
            className="bg-yellow-500/40 text-yellow-200 rounded-sm"
          >
            {match[0]}
          </span>
        );
        lastIndex = regex.lastIndex;
        if (match[0].length === 0) regex.lastIndex++;
      }

      if (lastIndex < text.length) {
        parts.push(
          <span key={`e-${lineIdx}-${lastIndex}`}>
            {text.slice(lastIndex)}
          </span>
        );
      }

      return parts.length > 0 ? <>{parts}</> : <span className="text-ink-muted">{text || ' '}</span>;
    },
    [searchRegex],
  );

  /** 下载日志 */
  const handleDownload = async () => {
    setDownloading(true);
    try {
      const text = await downloadPodLogs(
        configId, podName, namespace, selectedContainer || undefined
      );
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${podName}-${selectedContainer || 'all'}-logs.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      addToast(lt.downloadError || '下载失败', 'error');
    } finally {
      setDownloading(false);
    }
  };

  /** 清空显示 */
  const handleClear = () => {
    setLines([]);
  };

  return (
    <div className="h-full flex flex-col bg-canvas">
      {/* 工具栏 */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-canvas shrink-0 flex-wrap">
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

        {/* Follow 开关 */}
        <button
          onClick={() => setFollow((f) => !f)}
          className={`flex items-center gap-1 px-2 py-1 text-xs rounded border transition-colors ${
            follow
              ? 'bg-green-500/20 border-green-500/30 text-green-400'
              : 'bg-surface-1 border-border text-ink-muted'
          }`}
        >
          <i className={`fas ${follow ? 'fa-pause' : 'fa-play'} text-xs`}></i>
          {lt.follow}
        </button>

        {/* 日志行数选择 */}
        <select
          value={tailLines}
          onChange={(e) => setTailLines(Number(e.target.value))}
          className="px-2 py-1 text-xs bg-surface-1 border border-border text-ink-muted rounded focus:outline-none focus:border-blue-500"
          title="日志行数"
        >
          <option value={100}>100 行</option>
          <option value={500}>500 行</option>
          <option value={1000}>1000 行</option>
          <option value={5000}>5000 行</option>
          <option value={10000}>10000 行</option>
        </select>

        {/* 搜索框 */}
        <div className="flex items-center gap-1 flex-1 min-w-[140px]">
          <i className="fas fa-search text-xs text-ink-faint"></i>
          <Input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder={lt.search}
            className="flex-1 h-7 px-2 text-xs"
          />
        </div>

        {/* 下载按钮 */}
        <Button
          variant="secondary"
          size="sm"
          onClick={handleDownload}
          disabled={downloading}
          className="h-7 px-2"
          title={lt.download}
        >
          <i className={`fas ${downloading ? 'fa-spinner fa-spin' : 'fa-download'} text-xs`}></i>
        </Button>

        {/* 清空按钮 */}
        <Button
          variant="secondary"
          size="sm"
          onClick={handleClear}
          disabled={lines.length === 0}
          className="h-7 px-2"
          title={lt.clear}
        >
          <i className="fas fa-trash text-xs"></i>
        </Button>
      </div>

      {/* 日志内容 */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto overflow-x-hidden font-mono"
      >
        {lines.length === 0 ? (
          <div className="flex items-center justify-center h-full text-ink-faint text-sm">
            <i className="fas fa-stream mr-2"></i>
            {lt.noLogs}
          </div>
        ) : (
          <div>
            {lines.map((line, idx) => (
              <div
                key={idx}
                className="flex hover:bg-surface-1/30"
                style={{ minHeight: 20 }}
              >
                {/* 行号 */}
                <span className="shrink-0 w-12 text-right pr-2 pl-2 select-none text-ink-faint border-r border-border/50 text-xs leading-5">
                  {idx + 1}
                </span>
                {/* 日志内容 */}
                <span className="px-2 text-xs text-ink-muted whitespace-pre-wrap break-all leading-5">
                  {highlightLine(line, idx)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 底部状态栏 */}
      <div className="flex items-center justify-between px-3 py-1 border-t border-border bg-canvas text-xs text-ink-faint shrink-0">
        <span>
          {lines.length > 0 && (
            <>
              <span className="text-ink-muted">{lines.length.toLocaleString()}</span>
              {' '}lines
              {selectedContainer && (
                <span className="ml-2">
                  container: <span className="text-accent-info">{selectedContainer}</span>
                </span>
              )}
            </>
          )}
        </span>
        <span className={follow ? 'text-green-400' : 'text-ink-faint'}>
          {follow ? '● LIVE' : '○ PAUSED'}
        </span>
      </div>
    </div>
  );
};
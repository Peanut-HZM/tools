import React, { useState } from 'react';
import type {
  McpServer,
  McpServerCreate,
  McpServerUpdate,
  McpTransport,
} from '../../../api/mcpServersApi';

interface Props {
  server?: McpServer;
  onClose: () => void;
  onCreate: (data: McpServerCreate) => Promise<void> | void;
  /**
   * 编辑模式下不传 transport（后端对 transport 不做 PATCH）；
   * 同时允许调用方在更新时强制附带额外字段
   */
  onUpdate?: (data: McpServerUpdate) => Promise<void> | void;
}

/** transport 选项（中文标签） */
const TRANSPORT_OPTIONS: Array<{ value: McpTransport; label: string }> = [
  { value: 'sse', label: 'SSE（服务端事件流）' },
  { value: 'http', label: 'Streamable HTTP' },
  { value: 'stdio', label: 'stdio（本地进程）' },
];

/** 从 server.command_json 解析出格式化文本（编辑模式预填用） */
function parseCommandJsonText(raw?: string | null): string {
  if (!raw) return '';
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

const CreateDialog: React.FC<Props> = ({ server, onClose, onCreate, onUpdate }) => {
  const isEdit = Boolean(server);
  const [name, setName] = useState(server?.name || '');
  const [transport, setTransport] = useState<McpTransport>(server?.transport ?? 'sse');
  const [serverUrl, setServerUrl] = useState(server?.server_url || '');
  const [commandText, setCommandText] = useState(() => parseCommandJsonText(server?.command_json));
  const [timeout, setTimeout] = useState<number>(server?.timeout_seconds ?? 30);
  const [headersText, setHeadersText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const isStdio = transport === 'stdio';

  /**
   * 解析 stdio command JSON（创建/编辑共用）
   * 返回 null 表示格式不合法
   */
  const parseCommand = (): Record<string, unknown> | null => {
    const trimmed = commandText.trim();
    if (!trimmed) return null;
    try {
      const parsed = JSON.parse(trimmed);
      const cmdName = parsed?.command;
      if (
        parsed === null ||
        typeof parsed !== 'object' ||
        Array.isArray(parsed) ||
        typeof cmdName !== 'string' ||
        !cmdName.trim()
      ) {
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch {
      return null;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('Name 为必填');
      return;
    }

    if (timeout < 1 || timeout > 300) {
      setError('Timeout 必须在 1-300 秒之间');
      return;
    }

    // stdio：command JSON 校验（必填）
    let parsedCommand: Record<string, unknown> | undefined;
    if (isStdio) {
      const cmd = parseCommand();
      if (!cmd) {
        setError('command 必须是含非空 "command" 键的 JSON object');
        return;
      }
      parsedCommand = cmd;
    } else if (!serverUrl.trim()) {
      // sse / http：URL 必填
      setError('Server URL 为必填');
      return;
    }

    // 解析 headers JSON（可选，仅 url 型 transport）
    let parsedHeaders: Record<string, string> | undefined;
    const trimmedHeaders = headersText.trim();
    if (trimmedHeaders && !isStdio) {
      try {
        const parsed = JSON.parse(trimmedHeaders);
        if (
          parsed === null ||
          typeof parsed !== 'object' ||
          Array.isArray(parsed) ||
          Object.values(parsed).some((v) => typeof v !== 'string')
        ) {
          setError('Headers 必须是 JSON object<string, string>');
          return;
        }
        parsedHeaders = parsed as Record<string, string>;
      } catch {
        setError('Headers JSON 格式不合法');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (isEdit) {
        const payload: McpServerUpdate = {
          name,
          server_url: serverUrl,
          timeout_seconds: timeout,
        };
        // 仅 stdio server 可替换 command 配置
        if (server?.transport === 'stdio' && parsedCommand) payload.command = parsedCommand;
        if (parsedHeaders) payload.headers = parsedHeaders;
        if (onUpdate) {
          await onUpdate(payload);
        } else {
          await onCreate(payload as unknown as McpServerCreate);
        }
      } else {
        const payload: McpServerCreate = {
          name,
          // stdio 的 server_url 仅作展示摘要，留空时用 command 首段兜底
          server_url: isStdio
            ? serverUrl.trim() || String((parsedCommand?.command as string) ?? '')
            : serverUrl.trim(),
          transport,
          timeout_seconds: timeout,
        };
        if (isStdio && parsedCommand) payload.command = parsedCommand;
        if (parsedHeaders) payload.headers = parsedHeaders;
        await onCreate(payload);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-1 rounded-lg p-6 w-full max-w-md border border-border/50 shadow-xl">
        <h2 className="text-xl font-bold mb-4 text-ink">
          {server ? '编辑 MCP Server' : '添加 MCP Server'}
        </h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 text-ink">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="e.g. github"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 text-ink">Transport</label>
            <select
              value={transport}
              onChange={(e) => setTransport(e.target.value as McpTransport)}
              disabled={isEdit}
              className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
            >
              {TRANSPORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {isEdit && (
              <p className="text-xs text-ink-muted mt-1">
                transport 创建后不可修改；如需切换请删除后重建
              </p>
            )}
          </div>

          {!isStdio ? (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-ink">Server URL</label>
              <input
                type="text"
                value={serverUrl}
                onChange={(e) => setServerUrl(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="https://mcp.example.com/mcp"
              />
            </div>
          ) : (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-ink">
                Command (JSON, 必填)
              </label>
              <textarea
                value={commandText}
                onChange={(e) => setCommandText(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder={'{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"]}'}
              />
              <p className="text-xs text-ink-muted mt-1">
                可选字段：args（参数数组）、env（附加环境变量，叠加在最小默认环境之上）
              </p>
            </div>
          )}

          {!isStdio && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-ink">
                Headers (可选, JSON)
              </label>
              <textarea
                value={headersText}
                onChange={(e) => setHeadersText(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder='{"Authorization": "Bearer xxx"}'
              />
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 text-ink">Timeout (seconds)</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(Number(e.target.value))}
              min={1}
              max={300}
              className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          {error && <div className="text-danger text-sm mb-4">{error}</div>}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-ink-muted hover:text-ink"
              disabled={submitting}
            >
              取消
            </button>
            <button
              type="submit"
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-60"
              disabled={submitting}
            >
              {submitting ? '保存中...' : server ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateDialog;

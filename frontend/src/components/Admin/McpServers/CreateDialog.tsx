import React, { useState } from 'react';
import type { McpServer, McpServerCreate, McpServerUpdate } from '../../../api/mcpServersApi';

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

const CreateDialog: React.FC<Props> = ({ server, onClose, onCreate, onUpdate }) => {
  const isEdit = Boolean(server);
  const [name, setName] = useState(server?.name || '');
  const [serverUrl, setServerUrl] = useState(server?.server_url || '');
  const [timeout, setTimeout] = useState<number>(server?.timeout_seconds ?? 30);
  const [headersText, setHeadersText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim() || !serverUrl.trim()) {
      setError('Name 和 URL 均为必填');
      return;
    }

    if (timeout < 1 || timeout > 300) {
      setError('Timeout 必须在 1-300 秒之间');
      return;
    }

    // 解析 headers JSON（可选）
    let parsedHeaders: Record<string, string> | undefined;
    const trimmedHeaders = headersText.trim();
    if (trimmedHeaders) {
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
        if (parsedHeaders) payload.headers = parsedHeaders;
        if (onUpdate) {
          await onUpdate(payload);
        } else {
          await onCreate(payload as unknown as McpServerCreate);
        }
      } else {
        const payload: McpServerCreate = {
          name,
          server_url: serverUrl,
          transport: 'sse',
          timeout_seconds: timeout,
        };
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
            <label className="block text-sm font-medium mb-1 text-ink">Server URL</label>
            <input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="http://localhost:3000"
            />
          </div>

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

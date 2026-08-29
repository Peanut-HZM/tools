import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import {
  mcpServersApi,
  type McpServer,
  type McpServerCreate,
  type McpServerUpdate,
  type McpServerTestResponse,
} from '../../../api/mcpServersApi';
import CreateDialog from './CreateDialog';
import TestResultDialog from './TestResultDialog';

const McpServers: React.FC = () => {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingServer, setEditingServer] = useState<McpServer | null>(null);
  const [testResult, setTestResult] = useState<McpServerTestResponse | null>(null);
  const [error, setError] = useState('');

  const fetchServers = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await mcpServersApi.list();
      setServers(data);
    } catch (err: any) {
      console.error('Failed to fetch MCP servers:', err);
      setError(err?.message || '加载 MCP servers 失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleCreate = async (data: McpServerCreate) => {
    await mcpServersApi.create(data);
    setShowCreate(false);
    await fetchServers();
  };

  const handleUpdate = async (id: string, data: McpServerUpdate) => {
    await mcpServersApi.update(id, data);
    setEditingServer(null);
    await fetchServers();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定删除此 MCP server？')) return;
    try {
      await mcpServersApi.delete(id);
      await fetchServers();
    } catch (err: any) {
      console.error('Delete failed:', err);
      setError(err?.message || '删除失败');
    }
  };

  const handleTest = async (id: string) => {
    try {
      const data = await mcpServersApi.test(id);
      setTestResult(data);
      await fetchServers();
    } catch (err: any) {
      console.error('Test failed:', err);
      // 即使失败也展示结果对话框，让用户看到错误
      setTestResult({
        success: false,
        tools: [],
        error: err?.message || '测试失败',
      });
    }
  };

  const handleToggleActive = async (server: McpServer) => {
    try {
      await mcpServersApi.update(server.id, { is_active: !server.is_active });
      await fetchServers();
    } catch (err: any) {
      console.error('Toggle active failed:', err);
      setError(err?.message || '更新启用状态失败');
    }
  };

  const handleSync = async (id: string) => {
    try {
      await mcpServersApi.sync(id);
      await fetchServers();
    } catch (err: any) {
      console.error('Sync failed:', err);
      setError(err?.message || '同步失败');
    }
  };

  if (loading && servers.length === 0) {
    return <div className="p-4 text-ink-muted">加载中...</div>;
  }

  return (
    <div className="p-6 text-ink">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">MCP Servers</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> 添加 Server
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 rounded border border-danger text-danger bg-danger/10">
          {error}
        </div>
      )}

      <div className="bg-surface-1 rounded shadow border border-border/50 overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-2">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">Name</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">URL</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">Transport</th>
              <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">Tools</th>
              <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">Status</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-ink-muted">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {servers.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-ink-faint text-sm"
                >
                  暂无 MCP server，点击右上角"添加 Server"创建
                </td>
              </tr>
            ) : (
              servers.map((server) => (
                <tr key={server.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 font-medium">{server.name}</td>
                  <td className="px-4 py-3 text-sm text-ink-muted break-all">{server.server_url}</td>
                  <td className="px-4 py-3 text-sm">{server.transport}</td>
                  <td className="px-4 py-3 text-center">{server.tools_count}</td>
                  <td className="px-4 py-3 text-center">
                    {server.is_active ? (
                      <span className="text-green-600 flex items-center justify-center gap-1">
                        <Wifi className="w-4 h-4" /> Active
                      </span>
                    ) : (
                      <span className="text-gray-400 flex items-center justify-center gap-1">
                        <WifiOff className="w-4 h-4" /> Inactive
                      </span>
                    )}
                    {server.last_error && (
                      <div className="text-xs text-danger mt-1" title={server.last_error}>
                        上次错误
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                    <button
                      onClick={() => handleTest(server.id)}
                      className="text-blue-500 hover:text-blue-700"
                      title="测试连接"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleSync(server.id)}
                      className="text-cyan-500 hover:text-cyan-700"
                      title="同步工具"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setEditingServer(server)}
                      className="text-gray-500 hover:text-gray-700"
                      title="编辑"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleToggleActive(server)}
                      className="text-yellow-500 hover:text-yellow-700"
                      title={server.is_active ? '禁用' : '启用'}
                    >
                      {server.is_active ? <WifiOff className="w-4 h-4" /> : <Wifi className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(server.id)}
                      className="text-red-500 hover:text-red-700"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateDialog
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}

      {editingServer && (
        <CreateDialog
          server={editingServer}
          onClose={() => setEditingServer(null)}
          onCreate={(data) => handleUpdate(editingServer.id, data)}
        />
      )}

      {testResult && (
        <TestResultDialog
          result={testResult}
          onClose={() => setTestResult(null)}
        />
      )}
    </div>
  );
};

export default McpServers;

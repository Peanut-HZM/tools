// Neo4j 连接管理面板（抽屉）
// 列表 + 新建/编辑表单 + 每行"测试"按钮内联显示结果
import React, { useEffect, useState } from 'react';
import { X, Plus, Pencil, Trash2, Plug } from 'lucide-react';
import {
  Neo4jConnection,
  CreateNeo4jConnectionRequest,
  UpdateNeo4jConnectionRequest,
  Neo4jTestResult,
  listConnections,
  createConnection,
  updateConnection,
  deleteConnection,
  testConnection,
} from '../../../api/neo4jToolApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface Props {
  /** 抽屉是否打开 */
  isOpen: boolean;
  onClose: () => void;
  /** 当前选中的连接 ID（删除选中项时回调清空） */
  activeConnectionId: string | null;
  onActiveConnectionChange: (id: string | null) => void;
  /** 连接变更（增删改）后通知父组件刷新 Schema 等 */
  onConnectionsChanged?: () => void;
}

/** 单行连接的测试结果本地状态 */
interface RowTestState {
  loading: boolean;
  result: Neo4jTestResult | null;
}

export const ConnectionPanel: React.FC<Props> = ({
  isOpen,
  onClose,
  activeConnectionId,
  onActiveConnectionChange,
  onConnectionsChanged,
}) => {
  const { addToast } = useToast();
  const [connections, setConnections] = useState<Neo4jConnection[]>([]);
  const [listLoading, setListLoading] = useState(false);
  /** 正在编辑的连接（null = 新建模式；undefined = 不显示表单） */
  const [editingConn, setEditingConn] = useState<Neo4jConnection | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  /** 每行测试状态：connId → 状态 */
  const [testStates, setTestStates] = useState<Record<string, RowTestState>>({});

  // 表单字段
  const [formName, setFormName] = useState('');
  const [formUri, setFormUri] = useState('bolt://localhost:7687');
  const [formUsername, setFormUsername] = useState('neo4j');
  const [formPassword, setFormPassword] = useState('');
  const [formDatabase, setFormDatabase] = useState('neo4j');

  /** 加载连接列表；失败时 toast 并保留已有数据（不炸页） */
  const loadConnections = async () => {
    setListLoading(true);
    try {
      const data = await listConnections();
      // 防御：异常数据源返回 undefined 时按空列表处理，避免渲染崩溃
      setConnections(Array.isArray(data) ? data : []);
    } catch (error) {
      addToast(`加载连接列表失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConnections();
      // 关闭表单态，回到列表态
      setEditingConn(undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  /** 进入新建模式 */
  const handleAdd = () => {
    setEditingConn(null);
    setFormName('');
    setFormUri('bolt://localhost:7687');
    setFormUsername('neo4j');
    setFormPassword('');
    setFormDatabase('neo4j');
  };

  /** 进入编辑模式（password 不回填，留空表示不修改） */
  const handleEdit = (conn: Neo4jConnection) => {
    setEditingConn(conn);
    setFormName(conn.name);
    setFormUri(conn.uri);
    setFormUsername(conn.username);
    setFormPassword('');
    setFormDatabase(conn.database);
  };

  /** 提交表单：新建 或 更新 */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingConn) {
        // 编辑：password 留空则不修改
        const payload: UpdateNeo4jConnectionRequest = {
          name: formName,
          uri: formUri,
          username: formUsername,
          database: formDatabase,
        };
        if (formPassword) {
          payload.password = formPassword;
        }
        await updateConnection(editingConn.id, payload);
        addToast('连接已更新', 'success');
      } else {
        const payload: CreateNeo4jConnectionRequest = {
          name: formName,
          uri: formUri,
          username: formUsername,
          password: formPassword,
          database: formDatabase,
        };
        await createConnection(payload);
        addToast('连接已创建', 'success');
      }
      // 先回到列表态，再加载数据，避免在表单态/列表态之间出现竞态
      setEditingConn(undefined);
      await loadConnections();
      onConnectionsChanged?.();
    } catch (error) {
      addToast(`保存失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  /** 删除连接（需确认） */
  const handleDelete = async (conn: Neo4jConnection) => {
    if (!window.confirm(`确定删除连接「${conn.name}」吗？`)) return;
    try {
      await deleteConnection(conn.id);
      addToast('连接已删除', 'success');
      if (activeConnectionId === conn.id) {
        onActiveConnectionChange(null);
      }
      await loadConnections();
      onConnectionsChanged?.();
    } catch (error) {
      addToast(`删除失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
    }
  };

  /** 行内测试连通性，结果只显示在行内（不弹 toast 打扰） */
  const handleTest = async (conn: Neo4jConnection) => {
    setTestStates((prev) => ({ ...prev, [conn.id]: { loading: true, result: null } }));
    try {
      const result = await testConnection(conn.id);
      setTestStates((prev) => ({ ...prev, [conn.id]: { loading: false, result } }));
    } catch (error) {
      setTestStates((prev) => ({
        ...prev,
        [conn.id]: {
          loading: false,
          result: { ok: false, server_version: null, error: error instanceof Error ? error.message : '测试失败' },
        },
      }));
    }
  };

  if (!isOpen) return null;

  const isEditing = editingConn !== undefined;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" data-testid="connection-panel">
      {/* 点击遮罩关闭 */}
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full max-w-md h-full bg-surface-1 border-l border-border flex flex-col shadow-xl">
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h2 className="text-lg font-semibold text-ink">管理连接</h2>
          <div className="flex items-center gap-2">
            {!isEditing && (
              <Button variant="ghost" size="icon" onClick={handleAdd} title="新建连接">
                <Plus className="w-4 h-4" />
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={onClose} title="关闭">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-y-auto p-4">
          {isEditing ? (
            /* ---------------- 新建 / 编辑表单 ---------------- */
            <form onSubmit={handleSubmit} className="space-y-4">
              <h3 className="text-sm font-medium text-ink-muted">
                {editingConn ? `编辑连接：${editingConn.name}` : '新建连接'}
              </h3>
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-1">名称</label>
                <Input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="我的 Neo4j"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-1">连接地址</label>
                <Input
                  type="text"
                  required
                  value={formUri}
                  onChange={(e) => setFormUri(e.target.value)}
                  placeholder="bolt://localhost:7687"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-1">用户名</label>
                <Input
                  type="text"
                  required
                  value={formUsername}
                  onChange={(e) => setFormUsername(e.target.value)}
                  placeholder="neo4j"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-1">密码</label>
                <Input
                  type="password"
                  required={!editingConn}
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  placeholder={editingConn ? '留空则不修改' : ''}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-1">数据库</label>
                <Input
                  type="text"
                  value={formDatabase}
                  onChange={(e) => setFormDatabase(e.target.value)}
                  placeholder="neo4j"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" onClick={() => setEditingConn(undefined)}>
                  返回列表
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? '保存中...' : '保存'}
                </Button>
              </div>
            </form>
          ) : (
            /* ---------------- 连接列表 ---------------- */
            <div className="space-y-2">
              {listLoading && connections.length === 0 && (
                <p className="text-sm text-ink-faint text-center py-8">加载中...</p>
              )}
              {!listLoading && connections.length === 0 && (
                <p className="text-sm text-ink-faint text-center py-8">
                  暂无连接，点击右上角 + 新建
                </p>
              )}
              {connections.map((conn) => {
                const testState = testStates[conn.id];
                return (
                  <div
                    key={conn.id}
                    className={`rounded-lg border p-3 ${
                      activeConnectionId === conn.id
                        ? 'border-accent bg-surface-2'
                        : 'border-border bg-surface-1'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <button
                        type="button"
                        className="flex-1 text-left min-w-0"
                        onClick={() => onActiveConnectionChange(conn.id)}
                      >
                        <div className="font-medium text-ink truncate">{conn.name}</div>
                        <div className="text-xs text-ink-faint truncate">
                          {conn.uri} · {conn.database}
                        </div>
                      </button>
                      <div className="flex items-center gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleTest(conn)}
                          disabled={testState?.loading}
                          title="测试连接"
                        >
                          <Plug className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleEdit(conn)}
                          title="编辑"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-accent-danger"
                          onClick={() => handleDelete(conn)}
                          title="删除"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                    {/* 行内测试结果 */}
                    {testState?.loading && (
                      <p className="text-xs text-ink-faint mt-2">测试连接中...</p>
                    )}
                    {testState?.result && !testState.loading && (
                      <p
                        className={`text-xs mt-2 ${
                          testState.result.ok ? 'text-accent-success' : 'text-accent-danger'
                        }`}
                      >
                        {testState.result.ok
                          ? `连接成功${testState.result.server_version ? `（版本 ${testState.result.server_version}）` : ''}`
                          : `连接失败：${testState.result.error || '未知错误'}`}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

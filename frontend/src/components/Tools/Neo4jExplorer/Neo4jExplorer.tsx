// Neo4j 图谱浏览器 —— 页面入口
// 顶部连接选择器 + 管理连接抽屉 + Tab（概览 / 探索 / 查询）
// 本任务实现概览 Tab，探索/查询为占位（Task 7/8 填充）
import React, { useEffect, useState } from 'react';
import { Database, Settings, LayoutGrid, Compass, Terminal } from 'lucide-react';
import {
  Neo4jConnection,
  Neo4jSchema,
  listConnections,
  getSchema,
} from '../../../api/neo4jToolApi';
import { useToast } from '../../../hooks/useToast';
import { useAuth } from '../../../stores/authStore';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { ConnectionPanel } from './ConnectionPanel';
import { SchemaOverview } from './SchemaOverview';

type TabValue = 'overview' | 'explore' | 'query';

const Neo4jExplorer: React.FC = () => {
  const { addToast } = useToast();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [connections, setConnections] = useState<Neo4jConnection[]>([]);
  /** 当前选中的连接 ID（Task 7/8 复用） */
  const [activeConnectionId, setActiveConnectionId] = useState<string | null>(null);
  const [showConnectionPanel, setShowConnectionPanel] = useState(false);
  const [activeTab, setActiveTab] = useState<TabValue>('overview');
  // Schema 状态：失败时保留旧数据（不炸页）
  const [schema, setSchema] = useState<Neo4jSchema | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);

  /** 加载连接列表；失败 toast + 保留已有数据 */
  const loadConnections = async () => {
    try {
      const data = await listConnections();
      setConnections(data);
      // 若当前选中项已不存在，自动清空
      if (activeConnectionId && !data.find((c) => c.id === activeConnectionId)) {
        setActiveConnectionId(null);
      }
    } catch (error) {
      if (isAuthenticated) {
        addToast(`加载连接列表失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
      }
    }
  };

  /** 加载 Schema 概览；失败 toast + 保留已有 schema */
  const loadSchema = async (connId: string) => {
    setSchemaLoading(true);
    try {
      const data = await getSchema(connId);
      setSchema(data);
    } catch (error) {
      addToast(`加载 Schema 失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
      // 失败不炸页：保留旧 schema
    } finally {
      setSchemaLoading(false);
    }
  };

  // 未登录不发起受保护请求
  useEffect(() => {
    if (!isAuthenticated) {
      setConnections([]);
      setActiveConnectionId(null);
      return;
    }
    loadConnections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  // 选中连接变化时自动刷新 Schema（仅概览 Tab 需要，这里统一加载）
  useEffect(() => {
    if (activeConnectionId) {
      loadSchema(activeConnectionId);
    } else {
      setSchema(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConnectionId]);

  /** 点击 Label 卡片：切换到探索 Tab 并预选（Task 7 实现完整联动，这里先占位提示） */
  const handleSelectLabel = (_label: string) => {
    addToast('探索功能即将上线（Task 7）', 'info');
  };

  if (authLoading) {
    return (
      <div className="flex h-full min-h-[300px] items-center justify-center">
        <div className="text-sm text-ink-muted">加载中...</div>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <RequireAuthNotice />;
  }

  const activeConnection = connections.find((c) => c.id === activeConnectionId) || null;

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden bg-canvas">
      {/* ---------- 顶部工具栏：连接选择器 + 管理连接 ---------- */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-surface-1 shrink-0 flex-wrap">
        <Database className="w-4 h-4 text-ink-muted shrink-0" />
        <span className="text-sm font-medium text-ink-muted shrink-0">Neo4j 连接：</span>
        <select
          className="flex-1 min-w-[160px] max-w-xs h-9 rounded-lg border border-border bg-surface-1 px-3 text-sm text-ink focus-visible:border-accent focus-visible:outline-none"
          value={activeConnectionId || ''}
          onChange={(e) => setActiveConnectionId(e.target.value || null)}
          aria-label="选择 Neo4j 连接"
        >
          <option value="">请选择连接</option>
          {connections.map((conn) => (
            <option key={conn.id} value={conn.id}>
              {conn.name}（{conn.database}）
            </option>
          ))}
        </select>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowConnectionPanel(true)}
        >
          <Settings className="w-3.5 h-3.5 mr-1" />
          管理连接
        </Button>
      </div>

      {/* ---------- 主体 Tab ---------- */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {activeConnection ? (
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as TabValue)}
            className="flex-1 flex flex-col overflow-hidden"
          >
            <TabsList className="mx-4 mt-2 bg-surface-2 shrink-0 self-start">
              <TabsTrigger value="overview">
                <LayoutGrid className="w-3.5 h-3.5 mr-1" />
                概览
              </TabsTrigger>
              <TabsTrigger value="explore">
                <Compass className="w-3.5 h-3.5 mr-1" />
                探索
              </TabsTrigger>
              <TabsTrigger value="query">
                <Terminal className="w-3.5 h-3.5 mr-1" />
                查询
              </TabsTrigger>
            </TabsList>

            {/* 概览 Tab：本任务实现 */}
            <TabsContent value="overview" className="flex-1 overflow-hidden mt-0">
              <SchemaOverview
                schema={schema}
                loading={schemaLoading}
                onSelectLabel={handleSelectLabel}
              />
            </TabsContent>

            {/* 探索 Tab：Task 7 实现 */}
            <TabsContent value="explore" className="flex-1 overflow-hidden">
              <div className="flex flex-col items-center justify-center h-full text-ink-faint">
                <Compass className="w-16 h-16 mb-4 opacity-20" />
                <p className="text-sm">图探索功能即将上线</p>
              </div>
            </TabsContent>

            {/* 查询 Tab：Task 8 实现 */}
            <TabsContent value="query" className="flex-1 overflow-hidden">
              <div className="flex flex-col items-center justify-center h-full text-ink-faint">
                <Terminal className="w-16 h-16 mb-4 opacity-20" />
                <p className="text-sm">Cypher 查询工作台即将上线</p>
              </div>
            </TabsContent>
          </Tabs>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-ink-faint">
            <Database className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg">请选择或新建 Neo4j 连接</p>
          </div>
        )}
      </div>

      {/* ---------- 连接管理抽屉 ---------- */}
      <ConnectionPanel
        isOpen={showConnectionPanel}
        onClose={() => setShowConnectionPanel(false)}
        activeConnectionId={activeConnectionId}
        onActiveConnectionChange={(id) => {
          setActiveConnectionId(id);
          if (id) setShowConnectionPanel(false);
        }}
        onConnectionsChanged={loadConnections}
      />
    </div>
  );
};

export default Neo4jExplorer;

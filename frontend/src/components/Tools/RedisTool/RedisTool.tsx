import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Key, LineChart as LineChartIcon, Wrench, Server } from 'lucide-react';
import { ConnectionList } from './ConnectionList';
import { KeyExplorer } from './KeyExplorer';
import { MonitorPanel } from './MonitorPanel';
import { OperationsPanel } from './OperationsPanel';
import { ConnectionModal } from './ConnectionModal';
import { RedisConfig, getRedisConfigs, createRedisConfig, updateRedisConfig, deleteRedisConfig, CreateRedisRequest } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';
import { useAuth } from '../../../stores/authStore';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH } from '../../Common/useConnectionListWidth';

const RedisTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [configs, setConfigs] = useState<RedisConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<RedisConfig | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<'keys' | 'monitor' | 'ops'>('keys');
  // 侧栏宽度：用户可拖拽调整，且不小于「名称完整显示所需宽度」
  const [sidebarWidth, setSidebarWidth] = useState(256);
  const [requiredSidebarWidth, setRequiredSidebarWidth] = useState(0);
  const effectiveSidebarWidth = Math.max(sidebarWidth, requiredSidebarWidth);

  const loadConfigs = async () => {
    try {
      const data = await getRedisConfigs();
      setConfigs(data);
    } catch (error) {
      // 未登录/登录过期不弹通用错误：401 已由全局处理弹出登录框
      if (isAuthenticated) addToast(t.common.error, 'error');
    }
  };

  // 未登录不发起受保护请求，避免 401 触发无意义错误提示
  useEffect(() => {
    if (!isAuthenticated) {
      setConfigs([]);
      return;
    }
    loadConfigs();
  }, [isAuthenticated]);

  const handleAddConfig = () => {
    setEditingConfig(undefined);    setShowConnectionModal(true);
  };

  /** 拖拽调整左侧连接列表宽度 */
  const handleSidebarDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX;
      setSidebarWidth(
        Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, startWidth + delta)),
      );
    };
    const onUp = () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [sidebarWidth]);

  const handleEditConfig = (config: RedisConfig) => {
    setEditingConfig(config);
    setShowConnectionModal(true);
  };

  const handleSaveConfig = async (data: CreateRedisRequest) => {
    try {
      if (editingConfig) {
        await updateRedisConfig(editingConfig.id, data);
        addToast(t.redis.saveSuccess, 'success');
      } else {
        await createRedisConfig(data);
        addToast(t.redis.saveSuccess, 'success');
      }
      loadConfigs();
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  const handleDeleteConfig = async (id: string) => {
    try {
      await deleteRedisConfig(id);
      addToast(t.redis.deleteSuccess, 'success');
      if (selectedConfigId === id) setSelectedConfigId(null);
      loadConfigs();
    } catch (error) {
      // 未登录/登录过期不弹通用错误：401 已由全局处理弹出登录框
      if (isAuthenticated) addToast(t.common.error, 'error');
    }
  };

  // 未登录：不发受保护请求，显示登录提示（避免 401 弹出通用错误）
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

  return (
    <div className="flex flex-col md:flex-row h-full min-h-0 overflow-hidden bg-canvas">
     {/* 移动端纵向堆叠(侧栏在上、内容在下),md 以上恢复左右分栏 */}
      <div
        style={{ '--redis-sidebar-width': `${effectiveSidebarWidth}px` } as React.CSSProperties}
        className="w-full shrink-0 md:w-[var(--redis-sidebar-width)]"
      >
        <ConnectionList
          configs={configs}
          selectedId={selectedConfigId}
          onSelect={setSelectedConfigId}
          onAdd={handleAddConfig}
          onEdit={handleEditConfig}
          onDelete={handleDeleteConfig}
          onMigrated={loadConfigs}
          onRequiredWidthChange={setRequiredSidebarWidth}
        />
      </div>

      {/* 可拖动的分隔条：调整左侧连接列表宽度 */}
      <div
        onMouseDown={handleSidebarDragStart}
        role="separator"
        tabIndex={0}
        aria-orientation="vertical"
        aria-valuemin={MIN_SIDEBAR_WIDTH}
        aria-valuemax={MAX_SIDEBAR_WIDTH}
        aria-valuenow={effectiveSidebarWidth}
        aria-label="调整连接列表宽度"
        onKeyDown={(event) => {
          if (event.key === 'ArrowLeft') {
            event.preventDefault();
            setSidebarWidth((w) => Math.max(MIN_SIDEBAR_WIDTH, w - 20));
          }
          if (event.key === 'ArrowRight') {
            event.preventDefault();
            setSidebarWidth((w) => Math.min(MAX_SIDEBAR_WIDTH, w + 20));
          }
        }}
        className="hidden w-1 shrink-0 cursor-col-resize bg-surface-2 transition-colors hover:bg-accent-hover md:block"
      />
      <div className="flex-1 overflow-hidden bg-canvas flex flex-col">
        {selectedConfigId ? (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'keys' | 'monitor' | 'ops')} className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="mx-2 mt-2 bg-surface-2 shrink-0">
              <TabsTrigger value="keys"><Key className="w-3.5 h-3.5 mr-1" /> 键值浏览</TabsTrigger>
              <TabsTrigger value="monitor"><LineChartIcon className="w-3.5 h-3.5 mr-1" /> 监控</TabsTrigger>
              <TabsTrigger value="ops"><Wrench className="w-3.5 h-3.5 mr-1" /> 运维</TabsTrigger>
            </TabsList>
            <TabsContent value="keys" className="flex-1 overflow-hidden">
              <KeyExplorer configId={selectedConfigId} />
            </TabsContent>
            <TabsContent value="monitor" className="flex-1 overflow-hidden">
              <MonitorPanel configId={selectedConfigId} />
            </TabsContent>
            <TabsContent value="ops" className="flex-1 overflow-hidden">
              <OperationsPanel configId={selectedConfigId} />
            </TabsContent>
          </Tabs>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-ink-faint">
            <Server className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg">{t.redis.selectConnection}</p>
          </div>
        )}
      </div>
      <ConnectionModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        onSave={handleSaveConfig}
        initialData={editingConfig}
      />
    </div>
  );
};

export default RedisTool;

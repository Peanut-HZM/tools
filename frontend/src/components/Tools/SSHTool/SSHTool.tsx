import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ConnectionList } from './ConnectionList';
import { ConnectionModal } from './ConnectionModal';
import { EmptyState } from './EmptyState';
import { TabBar } from './TabBar';
import { TerminalPanel } from './TerminalPanel';
import {
  CreateSSHRequest, SSHConfig, UpdateSSHRequest,
  createSSHConfig, deleteSSHConfig, getSSHConfigs, updateSSHConfig,
} from '../../../api/sshToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { useAuth } from '../../../stores/authStore';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import { ConnectionStatus, MAX_TABS, SSHSessionTab, generateTabId } from './types';
import { MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH } from '../../Common/useConnectionListWidth';

const SSHTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [configs, setConfigs] = useState<SSHConfig[]>([]);
  const [tabs, setTabs] = useState<SSHSessionTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [tabStatuses, setTabStatuses] = useState<Record<string, ConnectionStatus>>({});
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SSHConfig | undefined>(undefined);
  // 侧栏宽度：用户可拖拽调整，且不小于「名称完整显示所需宽度」
  const [sidebarWidth, setSidebarWidth] = useState(256);
  const [requiredSidebarWidth, setRequiredSidebarWidth] = useState(0);
  const effectiveSidebarWidth = Math.max(sidebarWidth, requiredSidebarWidth);

  const loadConfigs = async () => {
    try {
      const data = await getSSHConfigs();
      setConfigs(data);
    } catch {
      // 未登录/登录过期时不弹通用错误：全局 401 处理已弹登录框
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

  const handleAddConfig = () => { setEditingConfig(undefined); setShowConnectionModal(true); };
  const handleEditConfig = (config: SSHConfig) => { setEditingConfig(config); setShowConnectionModal(true); };

  const handleSaveConfig = async (data: CreateSSHRequest | UpdateSSHRequest) => {
    try {
      if ('id' in data) await updateSSHConfig(data);
      else await createSSHConfig(data);
      addToast(t.ssh.saveSuccess, 'success');
      loadConfigs();
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  const handleDeleteConfig = async (id: string) => {
    try {
      await deleteSSHConfig(id);
      addToast(t.ssh.deleteSuccess, 'success');
      loadConfigs();
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  /** 侧边栏点击 → 新增 tab;达到上限 toast 提示 */
  const handleSelectConnection = useCallback((configId: string) => {
    if (tabs.length >= MAX_TABS) {
      addToast(t.ssh.tabLimitReached, 'error');
      return;
    }
    const config = configs.find(c => c.id === configId);
    if (!config) return;
    const tabId = generateTabId();
    const newTab: SSHSessionTab = {
      tabId,
      configId: config.id,
      configSnapshot: {
        alias: config.alias,
        host: config.host,
        port: config.port,
        username: config.username,
      },
      createdAt: Date.now(),
    };
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
  }, [tabs.length, configs, addToast, t.ssh.tabLimitReached]);

  /** 关闭指定 tab;若为 active,自动激活相邻 */
  const handleCloseTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const idx = prev.findIndex(item => item.tabId === tabId);
      const next = prev.filter(item => item.tabId !== tabId);
      setActiveTabId(current => {
        if (current !== tabId) return current;
        if (next.length === 0) return null;
        // 优先右侧相邻;否则左侧
        const right = prev[idx + 1];
        return right?.tabId ?? next[next.length - 1].tabId;
      });
      return next;
    });
    setTabStatuses(prev => {
      const { [tabId]: _removed, ...rest } = prev;
      return rest;
    });
  }, []);

  const handleActivateTab = useCallback((tabId: string) => setActiveTabId(tabId), []);

  const handleStatusChange = useCallback((tabId: string, status: ConnectionStatus) => {
    setTabStatuses(prev => ({ ...prev, [tabId]: status }));
  }, []);

  const handleRetryTab = useCallback((tabId: string) => {
    // 通过强制重渲染 TerminalPanel 触发重连:更新 createdAt
    setTabs(prev => prev.map(item => item.tabId === tabId ? { ...item, createdAt: Date.now() } : item));
  }, []);

  const activeTab = useMemo(() => tabs.find(item => item.tabId === activeTabId) ?? null, [tabs, activeTabId]);

  /** 拖拽调整左侧连接列表宽度 */
  const handleSidebarDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX;
      const next = Math.min(
        MAX_SIDEBAR_WIDTH,
        Math.max(MIN_SIDEBAR_WIDTH, startWidth + delta),
      );
      setSidebarWidth(next);
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

  // 未登录/登录过期：不渲染工具主体，避免挂载后立即请求受保护接口返回 401
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
     {/* 移动端纵向堆叠(侧栏在上、终端在下),md 以上恢复左右分栏 */}
      <div
        style={{ '--ssh-sidebar-width': `${effectiveSidebarWidth}px` } as React.CSSProperties}
        className="w-full shrink-0 md:w-[var(--ssh-sidebar-width)]"
      >
        <ConnectionList
          configs={configs}
          selectedId={null}
          onSelect={handleSelectConnection}
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
      <div className="flex-1 flex flex-col overflow-hidden bg-canvas">
        {tabs.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <TabBar
              tabs={tabs}
              statuses={tabStatuses}
              activeTabId={activeTabId}
              onActivate={handleActivateTab}
              onClose={handleCloseTab}
            />
            <div className="flex-1 relative overflow-hidden">
              {tabs.map(tab => (
                <div
                  key={tab.tabId}
                  className="absolute inset-0"
                  style={{
                    visibility: tab.tabId === activeTabId ? 'visible' : 'hidden',
                    zIndex: tab.tabId === activeTabId ? 1 : 0,
                  }}
                >
                  <TerminalPanel
                    tabId={tab.tabId}
                    configId={tab.configId}
                    createdAt={tab.createdAt}
                    isActive={tab.tabId === activeTabId}
                    onStatusChange={handleStatusChange}
                    onRetry={handleRetryTab}
                  />
                </div>
              ))}
            </div>
          </>
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

export default SSHTool;

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
import { ConnectionStatus, MAX_TABS, SSHSessionTab, generateTabId } from './types';

const SSHTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();

  const [configs, setConfigs] = useState<SSHConfig[]>([]);
  const [tabs, setTabs] = useState<SSHSessionTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [tabStatuses, setTabStatuses] = useState<Record<string, ConnectionStatus>>({});
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SSHConfig | undefined>(undefined);

  const loadConfigs = async () => {
    try {
      const data = await getSSHConfigs();
      setConfigs(data);
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  useEffect(() => { loadConfigs(); }, []);

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

  return (
    <div className="flex h-[calc(100vh-64px)] bg-canvas overflow-hidden">
      <ConnectionList
        configs={configs}
        selectedId={null}
        onSelect={handleSelectConnection}
        onAdd={handleAddConfig}
        onEdit={handleEditConfig}
        onDelete={handleDeleteConfig}
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

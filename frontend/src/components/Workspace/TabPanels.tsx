import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { toolComponentMap } from './toolComponents';
import { useI18n } from '../../i18n';

/**
 * 标签面板容器
 * 所有标签保持挂载，通过 display: none/block 切换
 * 这是状态保持的核心实现
 */
export const TabPanels: React.FC = () => {
  const { tabs, activeTabId } = useWorkspaceStore();
  const { t } = useI18n();

  if (tabs.length === 0) return null;

  return (
    <div className="flex-1 min-h-0 overflow-hidden">
      {tabs.map((tab) => {
        const ToolComponent = toolComponentMap[tab.toolId];
        if (!ToolComponent) {
          // 未知的工具 ID，显示占位
          return (
            <div
              key={tab.id}
              style={{ display: tab.id === activeTabId ? 'flex' : 'none' }}
              className="h-full items-center justify-center text-slate-500"
            >
              <div className="text-center">
                <i className="fas fa-exclamation-triangle text-4xl mb-4"></i>
                <p>{t.workspace.unknownTool}: {tab.toolId}</p>
              </div>
            </div>
          );
        }

        return (
          <div
            key={tab.id}
            style={{ display: tab.id === activeTabId ? 'flex' : 'none' }}
            className="h-full flex-col p-4"
          >
            <ToolComponent />
          </div>
        );
      })}
    </div>
  );
};

import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';

export const TabBar: React.FC = () => {
  const { t } = useI18n();
  const { tabs, activeTabId, setActiveTab, removeTab, isToolSidebarVisible, toggleToolSidebar } = useWorkspaceStore();

  return (
    <div className="flex items-end bg-surface-1 border-b border-border h-10 px-2 gap-0.5 overflow-x-auto">
      {/* 工具列表展开/折叠按钮 */}
      <button
        onClick={toggleToolSidebar}
        className="self-center p-1.5 mr-1 text-ink-muted hover:text-ink hover:bg-surface-2 rounded transition-colors flex-shrink-0"
        title={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
        aria-label={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
      >
        <i className={`fas ${isToolSidebarVisible ? 'fa-chevron-left' : 'fa-chevron-right'} text-xs`}></i>
      </button>
      {/* 标签页分隔线 */}
      <div className="self-stretch w-px bg-surface-2 mr-1"></div>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            data-tab-id={tab.id}
            data-active={isActive}
            className={[
              'flex items-center gap-2 px-3 py-1.5 rounded-t-md text-sm cursor-pointer transition-colors min-w-0 max-w-[180px] group',
              isActive
                ? 'bg-canvas text-ink border-t border-l border-r border-border'
                : 'bg-surface-1 text-ink-muted hover:text-ink hover:bg-surface-2',
            ].join(' ')}
            onClick={() => setActiveTab(tab.id)}
          >
            <i className={['fas', tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>
            <span className="truncate">{tab.toolName}</span>
            <button
              className="ml-1 text-ink-faint hover:text-ink hover:bg-surface-3 rounded px-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => {
                e.stopPropagation();
                removeTab(tab.id);
              }}
              title={t.workspace.closeTab}
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
};

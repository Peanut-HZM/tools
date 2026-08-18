import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';

export const TabBar: React.FC = () => {
  const { t } = useI18n();
  const { tabs, activeTabId, setActiveTab, removeTab, isToolSidebarVisible, toggleToolSidebar } = useWorkspaceStore();

  return (
    <div className="flex items-end bg-slate-800 border-b border-slate-700 h-10 px-2 gap-0.5 overflow-x-auto">
      {/* 工具列表展开/折叠按钮 */}
      <button
        onClick={toggleToolSidebar}
        className="self-center p-1.5 mr-1 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors flex-shrink-0"
        title={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
        aria-label={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
      >
        <i className={`fas ${isToolSidebarVisible ? 'fa-chevron-left' : 'fa-chevron-right'} text-xs`}></i>
      </button>
      {/* 标签页分隔线 */}
      <div className="self-stretch w-px bg-slate-700 mr-1"></div>
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
                ? 'bg-slate-900 text-slate-100 border-t border-l border-r border-slate-700'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700',
            ].join(' ')}
            onClick={() => setActiveTab(tab.id)}
          >
            <i className={['fas', tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>
            <span className="truncate">{tab.toolName}</span>
            <button
              className="ml-1 text-slate-500 hover:text-slate-200 hover:bg-slate-600 rounded px-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
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

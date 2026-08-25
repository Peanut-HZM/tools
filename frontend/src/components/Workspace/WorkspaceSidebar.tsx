import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import type { Tool } from '../../types';

interface Props {
  tools: Tool[];
}

export const WorkspaceSidebar: React.FC<Props> = ({ tools }) => {
  const navigate = useNavigate();
  const { t } = useI18n();
  const { tabs, addTab, isToolSidebarVisible, toggleToolSidebar } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');

  const openedToolIds = new Set(tabs.map((t) => t.toolId));

  const filteredTools = tools.filter((tool) =>
    tool.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleToolClick = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  const handleGoHome = () => {
    navigate('/');
  };

  if (!isToolSidebarVisible) {
    return null;
  }

  return (
    <div className="w-52 bg-surface-1 border-r border-border flex flex-col h-full">
      {/* 首页按钮 */}
      <div className="p-3 border-b border-border">
        <button
          onClick={handleGoHome}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent hover:bg-accent-hover text-white rounded-md text-sm font-medium transition-colors"
        >
          <i className="fas fa-home"></i>
          <span>{t.workspace.home}</span>
        </button>
      </div>

      {/* 搜索框 */}
      <div className="px-3 py-2 border-b border-border">
        <div className="relative">
          <i className="fas fa-search absolute left-2 top-1/2 -translate-y-1/2 text-ink-faint text-xs"></i>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.workspace.searchPlaceholder}
            className="w-full bg-canvas border border-border rounded-md pl-7 pr-2 py-1.5 text-xs text-ink-muted placeholder-slate-500 focus:outline-none focus:border-border"
          />
        </div>
      </div>

      {/* 工具列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="text-[10px] text-ink-faint uppercase font-semibold tracking-wider px-2 mb-2">
          {t.workspace.toolList}
        </div>
        <div className="space-y-0.5">
          {filteredTools.map((tool) => {
            const isOpened = openedToolIds.has(tool.id);
            return (
              <div
                key={tool.id}
                data-tool-id={tool.id}
                data-active={isOpened}
                className={[
                  'flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer transition-colors',
                  isOpened
                    ? 'bg-accent/20 text-blue-300'
                    : 'text-ink-muted hover:bg-surface-2 hover:text-ink-inverse',
                ].join(' ')}
                onClick={() => handleToolClick(tool)}
              >
                <i className={['fas', tool.icon, 'text-xs w-4 text-center flex-shrink-0'].join(' ')}></i>
                <span className="truncate">{tool.title}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import type { Tool } from '../../types';

interface Props {
  tools: Tool[];
}

const SIDEBAR_COLLAPSED_KEY = 'workspace-sidebar-collapsed';

export const WorkspaceSidebar: React.FC<Props> = ({ tools }) => {
  const navigate = useNavigate();
  const { tabs, addTab } = useWorkspaceStore();
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
  });

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));
  }, [collapsed]);

  const openedToolIds = new Set(tabs.map((t) => t.toolId));

  const handleToolClick = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  const handleGoHome = () => {
    navigate('/');
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-2">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
          title="展开侧边栏"
        >
          <i className="fas fa-chevron-right text-xs"></i>
        </button>
      </div>
    );
  }

  return (
    <div className="w-52 bg-slate-800 border-r border-slate-700 flex flex-col h-full">
      {/* 首页按钮 */}
      <div className="p-3 border-b border-slate-700">
        <button
          onClick={handleGoHome}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm font-medium transition-colors"
        >
          <i className="fas fa-home"></i>
          <span>返回首页</span>
        </button>
      </div>

      {/* 折叠按钮 */}
      <div className="flex justify-end px-2 pt-2">
        <button
          onClick={() => setCollapsed(true)}
          className="p-1 text-slate-500 hover:text-slate-300 hover:bg-slate-700 rounded transition-colors"
          title="折叠侧边栏"
        >
          <i className="fas fa-chevron-left text-xs"></i>
        </button>
      </div>

      {/* 工具列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider px-2 mb-2">
          工具列表
        </div>
        <div className="space-y-0.5">
          {tools.map((tool) => {
            const isOpened = openedToolIds.has(tool.id);
            return (
              <div
                key={tool.id}
                data-tool-id={tool.id}
                data-active={isOpened}
                className={[
                  'flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer transition-colors',
                  isOpened
                    ? 'bg-blue-600/20 text-blue-300'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white',
                ].join(' ')}
                onClick={() => handleToolClick(tool)}
              >
                <i className={[tool.icon, 'text-xs w-4 text-center flex-shrink-0'].join(' ')}></i>
                <span className="truncate">{tool.title}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { TabBar } from './TabBar';
import { TabPanels } from './TabPanels';
import { EmptyWorkspace } from './EmptyWorkspace';
import type { Tool } from '../../types';
import { fetchTools } from '../../services/api';

export const WorkspacePage: React.FC = () => {
  const location = useLocation();
  const { tabs, addTab } = useWorkspaceStore();
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTools('pc')
      .then((data) => setTools(data))
      .catch((err) => {
        const message =
          err instanceof Error ? err.message : '加载工具列表失败，请稍后重试';
        setError(message);
      })
      .finally(() => setLoading(false));
  }, []);

  // 处理从首页跳转过来时传递的工具 ID
  useEffect(() => {
    const state = location.state as { openToolId?: string } | null;
    if (state?.openToolId && tools.length > 0) {
      const tool = tools.find((t) => t.id === state.openToolId);
      if (tool) {
        addTab({ id: tool.id, title: tool.title, icon: tool.icon });
      }
      // 清除 state，避免刷新后重复触发
      window.history.replaceState({}, '');
    }
  }, [location.state, tools, addTab]);

  if (loading) {
    return (
      <div className="h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center text-slate-400">
          <i className="fas fa-exclamation-triangle text-4xl mb-4 text-amber-500"></i>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const hasTabs = tabs.length > 0;

  return (
    <div className="h-screen bg-slate-900 flex flex-col overflow-hidden">
      <div className="flex flex-1 min-h-0">
        {/* 左侧边栏 */}
        <WorkspaceSidebar tools={tools} />

        {/* 右侧内容区 */}
        <div className="flex-1 flex flex-col min-w-0">
          {hasTabs ? (
            <>
              {/* 标签栏 */}
              <TabBar />
              {/* 标签面板 */}
              <TabPanels />
            </>
          ) : (
            /* 空工作区欢迎页 */
            <EmptyWorkspace tools={tools} />
          )}
        </div>
      </div>
    </div>
  );
};

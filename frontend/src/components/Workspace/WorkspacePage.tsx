import { AlertTriangle } from 'lucide-react';
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
      <div className="h-screen bg-canvas flex items-center justify-center">
        <div className="text-ink-muted">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-canvas flex items-center justify-center">
        <div className="text-center text-ink-muted">
          <AlertTriangle className="w-10 h-10 mb-4 text-amber-500" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const hasTabs = tabs.length > 0;

  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">
      <div className="flex flex-1 min-h-0">
        {/* 左侧边栏 */}
        <WorkspaceSidebar tools={tools} />

        {/* 右侧内容区 */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* 标签栏始终渲染，空状态保留工具列表切换入口 */}
          <TabBar />
          {hasTabs ? <TabPanels /> : <EmptyWorkspace tools={tools} />}
        </div>
      </div>
    </div>
  );
};

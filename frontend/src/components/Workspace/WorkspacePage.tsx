import React, { useEffect, useState } from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { TabBar } from './TabBar';
import { TabPanels } from './TabPanels';
import { EmptyWorkspace } from './EmptyWorkspace';
import type { Tool } from '../../types';
import { fetchTools } from '../../services/api';

export const WorkspacePage: React.FC = () => {
  const { tabs } = useWorkspaceStore();
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTools('pc')
      .then((data) => setTools(data))
      .catch((err) => console.error('Failed to fetch tools:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">加载中...</div>
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

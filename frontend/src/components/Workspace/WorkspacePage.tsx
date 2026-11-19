import { AlertTriangle } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { TabBar } from './TabBar';
import { TabPanels } from './TabPanels';
import { EmptyWorkspace } from './EmptyWorkspace';
import type { Tool } from '../../types';
import { fetchTools } from '../../services/api';

export const WorkspacePage: React.FC = () => {
  const location = useLocation();
  // 地址栏中的工具编码（/workspace/<toolId>）：刷新后据此恢复打开的工具
  const { toolId: routeToolId } = useParams<{ toolId: string }>();
  const navigate = useNavigate();
  const { tabs, activeTabId, addTab } = useWorkspaceStore();
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 记录地址栏中的工具编码是否已被「打开工具」effect 消费。
  // 首次渲染时持久化的活跃页签可能仍指向旧工具，此时回写地址栏会把
  // 用户直接输入/刷新的 /workspace/<toolId> 覆盖掉。
  const consumedRouteToolIdRef = useRef<string | null>(null);
  // 等待 store 把活跃页签切到地址栏指定的工具（addTab 为异步 setState）
  const pendingRouteToolIdRef = useRef<string | null>(null);

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

  // 打开工具：优先用地址栏的 /workspace/<toolId>（刷新后仍能恢复），
  // 其次用从首页跳转时携带的 state.openToolId。
  useEffect(() => {
    if (tools.length === 0) return;

    const state = location.state as { openToolId?: string } | null;
    const targetToolId = routeToolId || state?.openToolId;
    if (!targetToolId) return;

    const tool = tools.find((t) => t.id === targetToolId);
    if (tool) {
      addTab({ id: tool.id, title: tool.title, icon: tool.icon });
    }
    // 标记该地址参数已消费：此后地址栏交由活跃页签驱动。
    // addTab 是异步 setState，本帧的 activeTabId 仍是旧值；用 pending 标记
    // 让下面的地址回写 effect 等到 store 真正切到该工具再动手，避免地址栏
    // 先闪回旧工具再跳回来。
    consumedRouteToolIdRef.current = targetToolId;
    pendingRouteToolIdRef.current = tool ? targetToolId : null;

    // 清除 history state，避免浏览器前进/后退时重复触发
    if (state?.openToolId) {
      window.history.replaceState({}, '');
    }
  }, [location.state, routeToolId, tools, addTab]);

  // 地址栏同步：只保留 /workspace/<工具编码>，工具内部参数一律不进 URL。
  // 用 replace 而不是 push，避免切换页签污染浏览器历史（后退键应回到
  // 工作区之外，而不是在页签之间来回跳）。
  useEffect(() => {
    if (loading) return;
    if (!activeTabId) return;

    const activeTab = tabs.find((tab) => tab.id === activeTabId);
    if (!activeTab) return;

    // 地址栏指定了工具但「打开工具」effect 尚未消费（首次渲染/刷新时）：
    // 此时持久化的活跃页签可能仍指向旧工具，回写会覆盖用户输入的地址。
    if (routeToolId && consumedRouteToolIdRef.current !== routeToolId) return;

    // 已请求打开地址栏工具，但 store 还没切过去（同一帧）：等下一帧再同步，
    // 避免地址栏先闪回旧工具。
    const pending = pendingRouteToolIdRef.current;
    if (pending) {
      if (activeTab.toolId === pending) {
        pendingRouteToolIdRef.current = null;
      } else {
        return;
      }
    }

    const target = `/workspace/${activeTab.toolId}`;
    if (location.pathname !== target) {
      navigate(target, { replace: true });
    }
  }, [activeTabId, loading, location.pathname, navigate, routeToolId, tabs]);

  if (loading) {
    return (
      <div className="h-full min-h-0 bg-canvas flex items-center justify-center">
        <div className="text-ink-muted">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full min-h-0 bg-canvas flex items-center justify-center">
        <div className="text-center text-ink-muted">
          <AlertTriangle className="w-10 h-10 mb-4 text-warning" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const hasTabs = tabs.length > 0;

  return (
    <div className="h-full min-h-0 bg-canvas flex flex-col overflow-hidden">
      <div className="relative flex min-h-0 flex-1">
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

/**
 * K8s 控制台工具 - 主容器
 *
 * 布局：左侧 ConnectionList（集群连接列表） + 右侧主区域
 * 右侧主区域：TopBar（ClusterSwitcher + NamespaceFilter） + ResourceTabs
 * 右侧抽屉 RightDrawer 展示资源详情（点击 Pod 行触发）
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useK8sStore } from '../../../stores/k8sStore';
import { useK8sConnections } from '../../../hooks/useK8sClient';
import { ConnectionList } from './ConnectionList';
import { ConnectionModal } from './ConnectionModal';
import { EmptyState } from './EmptyState';
import { TopBar } from './TopBar';
import { ResourceTabs } from './ResourceTabs';
import { RightDrawer } from './RightDrawer';
import { ClusterOverview } from './ClusterOverview';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';
import { useAuth } from '../../../stores/authStore';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import type { K8sConnection } from './types';
import * as api from '../../../api/k8sToolApi';
import { useK8sWorkspaceRoute } from './useK8sWorkspaceRoute';

const K8sTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const { isAuthenticated } = useAuth();
  const { connections, activeConnectionId, setActiveConnection, setConnections } = useK8sStore();

  const [showModal, setShowModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<K8sConnection | undefined>(undefined);

  // 左侧面板宽度（默认 256px，最小 200px，最大 500px）
  const [sidebarWidth, setSidebarWidth] = useState(256);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartXRef = useRef(0);
  const dragStartWidthRef = useRef(0);

  // 加载连接列表（React Query 自动轮询刷新）
  const connectionsQuery = useK8sConnections();

  const handleInvalidRouteContext = useCallback((message: string) => {
    addToast(message, 'error');
  }, [addToast]);
  const isWorkspaceRouteReady = useK8sWorkspaceRoute(
    handleInvalidRouteContext,
    connectionsQuery.isSuccess || connectionsQuery.isError,
  );

  /** 侧边栏点击 → 设置活跃连接 */
  const handleSelectConnection = (id: string) => setActiveConnection(id);

  /** 新建连接 */
  const handleAddConfig = () => {
    setEditingConfig(undefined);
    setShowModal(true);
  };

  /** 编辑连接 */
  const handleEditConfig = (config: K8sConnection) => {
    setEditingConfig(config);
    setShowModal(true);
  };

  /** 删除连接 */
  const handleDeleteConfig = async (id: string) => {
    const name = connections.find(c => c.id === id)?.name || '';
    if (!window.confirm(interpolate(t.tools['k8s-tool'].connection.deleteConfirm, { name }))) return;

    try {
      await api.deleteK8sConfig(id);
      addToast(t.tools['k8s-tool'].deleteSuccess, 'success');
      // 更新本地列表
      const remaining = connections.filter(c => c.id !== id);
      setConnections(remaining);
      // 若删除的是当前活跃连接，清除选择
      if (activeConnectionId === id) {
        setActiveConnection(null);
      }
    } catch (err) {
      addToast(err instanceof Error ? err.message : t.common.error, 'error');
    }
  };

  /** 拖动排序结束后更新后端排序 */
  const handleSortEnd = async (configIds: string[]) => {
    try {
      await api.updateK8sConfigSort(configIds);
    } catch (err) {
      addToast(err instanceof Error ? err.message : '排序更新失败', 'error');
    }
  };

  /** 模态框关闭后重新加载列表 */
  const handleModalClose = () => {
    setShowModal(false);
    setEditingConfig(undefined);
  };

  /** 开始拖动分隔条 */
  const handleDragStart = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartXRef.current = e.clientX;
    dragStartWidthRef.current = sidebarWidth;
    e.preventDefault();
  };

  /** 拖动中 */
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - dragStartXRef.current;
      const newWidth = Math.min(500, Math.max(200, dragStartWidthRef.current + deltaX));
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  // 未登录：不发请求，显示登录提示
  if (!isAuthenticated) {
    return <RequireAuthNotice />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-canvas overflow-hidden md:flex-row">
      {/* 左侧：连接列表 */}
      <div
        style={{ '--cluster-sidebar-width': `${sidebarWidth}px` } as React.CSSProperties}
        className="h-64 w-full shrink-0 md:h-full md:w-[var(--cluster-sidebar-width)]"
      >
        <ConnectionList
          configs={connections}
          selectedId={activeConnectionId}
          onSelect={handleSelectConnection}
          onAdd={handleAddConfig}
          onEdit={handleEditConfig}
          onDelete={handleDeleteConfig}
          onSortEnd={handleSortEnd}
        />
      </div>

      {/* 可拖动的分隔条 */}
      <div
        onMouseDown={handleDragStart}
        role="separator"
        tabIndex={0}
        aria-orientation="vertical"
        aria-valuemin={200}
        aria-valuemax={500}
        aria-valuenow={sidebarWidth}
        aria-label="调整集群列表宽度"
        onKeyDown={(event) => {
          if (event.key === 'ArrowLeft') {
            event.preventDefault();
            setSidebarWidth((width) => Math.max(200, width - 20));
          }
          if (event.key === 'ArrowRight') {
            event.preventDefault();
            setSidebarWidth((width) => Math.min(500, width + 20));
          }
        }}
        className={`hidden w-1 shrink-0 cursor-col-resize bg-surface-2 transition-colors hover:bg-accent-hover md:block ${
          isDragging ? 'bg-accent' : ''
        }`}
        style={{ cursor: 'col-resize' }}
      />

      {/* 右侧：主区域 */}
      <div className="flex-1 flex flex-col overflow-hidden bg-canvas min-h-0">
        {activeConnectionId ? (
          <>
            {/* 顶部操作栏：集群切换 + 命名空间过滤 */}
            <TopBar />
            {/* 仅展示后端实际可用的集群信息，不伪造容量或利用率指标 */}
            <ClusterOverview />
            {isWorkspaceRouteReady ? (
              <ResourceTabs />
            ) : (
              <div className="flex flex-1 items-center justify-center text-sm text-ink-faint">
                正在恢复工作区上下文…
              </div>
            )}
          </>
        ) : (
          <EmptyState />
        )}
      </div>

      {/* 右侧抽屉：资源详情（点击 Pod 行触发） */}
      <RightDrawer />

      {/* 连接配置模态框 */}
      <ConnectionModal
        isOpen={showModal}
        onClose={handleModalClose}
        initialData={editingConfig}
      />
    </div>
  );
};

export default K8sTool;

/**
 * K8s 控制台工具 - 主容器
 *
 * 布局：左侧 ConnectionList（集群连接列表） + 右侧主区域
 * 右侧主区域：TopBar（ClusterSwitcher + NamespaceFilter） + ResourceTabs
 * 底部面板 BottomPanel 展示多标签资源详情（由 k8sStore 多标签状态驱动）
 */
import React, { useState, useRef, useEffect } from 'react';
import { useK8sStore } from '../../../stores/k8sStore';
import { useK8sConnections } from '../../../hooks/useK8sClient';
import { ConnectionList } from './ConnectionList';
import { ConnectionModal } from './ConnectionModal';
import { EmptyState } from './EmptyState';
import { TopBar } from './TopBar';
import { ResourceTabs } from './ResourceTabs';
import { BottomPanel } from './BottomPanel/BottomPanel';
import { useToast } from '../../../hooks/useToast';
import { useI18n, interpolate } from '../../../i18n';
import { useAuth } from '../../../stores/authStore';
import RequireAuthNotice from '../../Common/RequireAuthNotice';
import type { K8sConnection } from './types';
import * as api from '../../../api/k8sToolApi';

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
  useK8sConnections();

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
    <div className="flex h-[calc(100vh-64px)] bg-slate-900 overflow-hidden">
      {/* 左侧：连接列表 */}
      <div style={{ width: `${sidebarWidth}px` }} className="shrink-0">
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
        className={`w-1 bg-slate-700 hover:bg-blue-500 cursor-col-resize transition-colors shrink-0 ${
          isDragging ? 'bg-blue-500' : ''
        }`}
        style={{ cursor: 'col-resize' }}
      />

      {/* 右侧：主区域 */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
        {activeConnectionId ? (
          <>
            {/* 顶部操作栏：集群切换 + 命名空间过滤 */}
            <TopBar />
            {/* 资源标签页：Pods / Workloads / Nodes / Events */}
            <ResourceTabs />
          </>
        ) : (
          <EmptyState />
        )}
      </div>

      {/* 底部面板：多标签资源详情（无标签时自动隐藏） */}
      <BottomPanel />

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

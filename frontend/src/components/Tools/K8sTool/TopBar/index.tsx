/**
 * K8s 控制台 - 顶部操作栏
 *
 * 包含 ClusterSwitcher（集群切换）和 NamespaceFilter（命名空间过滤）
 */
import React from 'react';
import { RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { ClusterSwitcher } from './ClusterSwitcher';
import { NamespaceFilter } from './NamespaceFilter';
import { useK8sStore } from '../../../../stores/k8sStore';
import { Button } from '@/components/ui/Button';

export const TopBar: React.FC = () => {
  const queryClient = useQueryClient();
  const { activeConnectionId, connections } = useK8sStore();
  const activeConnection = connections.find((connection) => connection.id === activeConnectionId);

  const refreshWorkspace = () => {
    if (!activeConnectionId) return;
    void queryClient.invalidateQueries({ queryKey: ['k8s', activeConnectionId] });
  };

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2 border-b border-border bg-surface-1/50">
      <div className="hidden 2xl:flex items-center gap-1.5 text-xs text-ink-faint mr-1">
        <span>工具箱</span>
        <span>/</span>
        <span>K8s 控制台</span>
        {activeConnection && (
          <>
            <span>/</span>
            <span className="max-w-32 truncate text-ink-muted">{activeConnection.name}</span>
          </>
        )}
      </div>
      {/* 集群切换 */}
      <ClusterSwitcher />

      {/* 分隔线 */}
      <div className="w-px h-6 bg-surface-2"></div>

      {/* 命名空间过滤 */}
      <NamespaceFilter />

      <div className="ml-auto">
        <Button
          variant="ghost"
          size="sm"
          onClick={refreshWorkspace}
          className="gap-1.5"
          title="刷新当前集群资源"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </Button>
      </div>
    </div>
  );
};

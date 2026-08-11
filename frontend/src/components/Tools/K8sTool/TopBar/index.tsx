/**
 * K8s 控制台 - 顶部操作栏
 *
 * 包含 ClusterSwitcher（集群切换）和 NamespaceFilter（命名空间过滤）
 */
import React from 'react';
import { ClusterSwitcher } from './ClusterSwitcher';
import { NamespaceFilter } from './NamespaceFilter';

export const TopBar: React.FC = () => {
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-700 bg-slate-800/50">
      {/* 集群切换 */}
      <ClusterSwitcher />

      {/* 分隔线 */}
      <div className="w-px h-6 bg-slate-700"></div>

      {/* 命名空间过滤 */}
      <NamespaceFilter />
    </div>
  );
};

/**
 * K8s 控制台 - 节点列表
 *
 * 展示集群所有 Node，字段：状态、名称、角色、版本、运行时、创建时间
 * 点击行触发 setSelectedResource
 */
import React from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sNodes } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';
import { formatAge, getNodeStatusColor } from './utils';
import type { K8sNodeSummary } from '../types';

export const NodeList: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, setSelectedResource } = useK8sStore();

  const { data: nodes = [], isLoading, error } = useK8sNodes(activeConnectionId);
  const isError = !!error;
  const errorMessage = error instanceof Error ? error.message : k8sT.errors.CONNECTION_FAILED;

  /** 点击行，选中该节点 */
  const handleRowClick = (node: K8sNodeSummary) => {
    setSelectedResource({
      type: 'node',
      namespace: '',
      name: node.name,
    });
  };

  /** 节点就绪状态（从 conditions 提取） */
  const getNodeStatus = (node: K8sNodeSummary): string => {
    const readyCondition = node.conditions.find((c) => c.type === 'Ready');
    if (!readyCondition) return node.status || 'Unknown';
    return readyCondition.status === 'True' ? 'Ready' : 'NotReady';
  };

  /** 角色显示 */
  const getRolesDisplay = (roles: string[]): string => {
    if (roles.length === 0) return '<none>';
    return roles.join(', ');
  };

  return (
    <div className="flex-1 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-slate-800 text-slate-400 border-b border-slate-700">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{k8sT.nodeList.status}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.nodeList.name}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.nodeList.roles}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.nodeList.version}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.nodeList.runtime}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.nodeList.age}</th>
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                <i className="fas fa-spinner fa-spin mr-2"></i>
                Loading...
              </td>
            </tr>
          )}

          {isError && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-red-400">
                <i className="fas fa-exclamation-triangle mr-2"></i>
                {errorMessage}
              </td>
            </tr>
          )}

          {!isLoading && !isError && nodes.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                {k8sT.nodeList.noNodes}
              </td>
            </tr>
          )}

          {nodes.map((node) => {
            const status = getNodeStatus(node);
            const statusColor = getNodeStatusColor(status);
            return (
              <tr
                key={node.name}
                onClick={() => handleRowClick(node)}
                className="border-b border-slate-800 hover:bg-slate-800/50 cursor-pointer transition-colors"
              >
                {/* 状态 */}
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <i className={`fas ${status === 'Ready' ? 'fa-check-circle' : 'fa-exclamation-circle'} ${statusColor}`}></i>
                    <span className={`text-xs ${statusColor}`}>{status}</span>
                  </div>
                </td>

                {/* 名称 */}
                <td className="px-3 py-2">
                  <div className="text-slate-200 font-medium truncate max-w-[240px]">{node.name}</div>
                </td>

                {/* 角色 */}
                <td className="px-3 py-2 text-slate-400 text-xs">
                  {getRolesDisplay(node.roles)}
                </td>

                {/* 版本 */}
                <td className="px-3 py-2 text-slate-400 text-xs font-mono">
                  {node.version || '-'}
                </td>

                {/* 运行时 */}
                <td className="px-3 py-2 text-slate-400 text-xs truncate max-w-[160px]">
                  {node.container_runtime || '-'}
                </td>

                {/* 创建时间 */}
                <td className="px-3 py-2 text-slate-400 text-xs">
                  {formatAge(node.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

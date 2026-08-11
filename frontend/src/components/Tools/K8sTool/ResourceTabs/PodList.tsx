/**
 * K8s 控制台 - Pod 列表
 *
 * 表格展示：状态图标、名称、重启次数、运行时间、节点、IP
 * 点击行触发 openResourceTab 打开对应标签页
 */
import React, { useState } from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sPods } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';
import { formatAge, getStatusColor, getStatusIcon } from './utils';

export const PodList: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, selectedNamespaces, openResourceTab } = useK8sStore();
  const [searchText, setSearchText] = useState('');

  // 查询命名空间列表（空数组表示"所有"，此时使用 store 中的全部 namespaces）
  const { namespaces } = useK8sStore();
  const effectiveNamespaces = selectedNamespaces.length === 0 ? namespaces : selectedNamespaces;
  const { data: pods = [], isLoading, error } = useK8sPods(activeConnectionId, effectiveNamespaces);
  const isError = !!error;
  const errorMessage = error instanceof Error ? error.message : k8sT.errors.CONNECTION_FAILED;

  // 按名称过滤 Pod
  const filteredPods = searchText
    ? pods.filter((pod) => pod.name.toLowerCase().includes(searchText.toLowerCase()))
    : pods;

  /** 点击行，打开该 Pod 的资源标签页 */
  const handleRowClick = (pod: typeof pods[0]) => {
    openResourceTab({
      id: `pod-${pod.namespace}-${pod.name}`,
      type: 'pod',
      namespace: pod.namespace,
      name: pod.name,
    });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 搜索框 */}
      <div className="px-3 py-2 border-b border-slate-700 bg-slate-800/50 shrink-0">
        <div className="flex items-center gap-2">
          <i className="fas fa-search text-xs text-slate-500"></i>
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="搜索 Pod 名称..."
            className="flex-1 px-2 py-1 text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded focus:outline-none focus:border-blue-500 placeholder-slate-600"
          />
          {searchText && (
            <button
              onClick={() => setSearchText('')}
              className="text-slate-500 hover:text-slate-300 px-1"
            >
              <i className="fas fa-times text-xs"></i>
            </button>
          )}
        </div>
      </div>

      {/* 表格 */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
        <thead className="sticky top-0 bg-slate-800 text-slate-400 border-b border-slate-700">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.status}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.name}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.restarts}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.age}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.node}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.ip}</th>
          </tr>
        </thead>
        <tbody>
          {/* 加载中 */}
          {isLoading && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                <i className="fas fa-spinner fa-spin mr-2"></i>
                Loading...
              </td>
            </tr>
          )}

          {/* 请求出错 */}
          {isError && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-red-400">
                <i className="fas fa-exclamation-triangle mr-2"></i>
                {errorMessage}
              </td>
            </tr>
          )}

          {/* 空数据 */}
          {!isLoading && !isError && filteredPods.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                {searchText ? `未找到匹配的 Pod: "${searchText}"` : k8sT.podList.noPods}
              </td>
            </tr>
          )}

          {/* Pod 行 */}
          {filteredPods.map((pod) => (
            <tr
              key={`${pod.namespace}/${pod.name}`}
              onClick={() => handleRowClick(pod)}
              className="border-b border-slate-800 hover:bg-slate-800/50 cursor-pointer transition-colors"
            >
              {/* 状态图标 */}
              <td className="px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <i className={`${getStatusIcon(pod.phase, pod.status)} ${getStatusColor(pod.phase, pod.status)}`}></i>
                  <span className={`${getStatusColor(pod.phase, pod.status)} text-xs`}>
                    {pod.phase}
                  </span>
                </div>
              </td>

              {/* 名称 + 命名空间 */}
              <td className="px-3 py-2">
                <div className="text-slate-200 font-medium truncate max-w-[240px]">{pod.name}</div>
                <div className="text-xs text-slate-500 truncate">{pod.namespace}</div>
              </td>

              {/* 重启次数 */}
              <td className="px-3 py-2 text-slate-300">
                {pod.restarts > 0 ? (
                  <span className={pod.restarts > 5 ? 'text-red-400' : 'text-yellow-400'}>
                    {pod.restarts}
                  </span>
                ) : (
                  <span className="text-slate-500">0</span>
                )}
              </td>

              {/* 运行时间 */}
              <td className="px-3 py-2 text-slate-400 text-xs">
                {formatAge(pod.created_at)}
              </td>

              {/* 节点 */}
              <td className="px-3 py-2 text-slate-400 truncate max-w-[140px]">
                {pod.node || '-'}
              </td>

              {/* IP */}
              <td className="px-3 py-2 text-slate-400 font-mono text-xs">
                {pod.pod_ip || '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
};

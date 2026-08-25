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
import { useToast } from '../../../../hooks/useToast';
import { downloadPodLogs } from '../../../../api/k8sToolApi';
import { formatAge, getStatusColor, getStatusIcon } from './utils';
import { Input } from '@/components/ui/Input';

export const PodList: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, selectedNamespaces, namespaces, openResourceTab } = useK8sStore();
  const { addToast } = useToast();
  const [searchText, setSearchText] = useState('');

  // 有效命名空间：空数组表示"所有"，此时使用 store 中的全部 namespaces
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

  /** 下载 Pod 完整日志 */
  const handleDownloadLogs = async (podName: string, namespace: string) => {
    try {
      const text = await downloadPodLogs(activeConnectionId, podName, namespace);
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${podName}-logs.txt`;
      a.click();
      URL.revokeObjectURL(url);
      addToast('日志下载成功', 'success');
    } catch (error) {
      console.error('Download logs failed:', error);
      addToast('下载日志失败', 'error');
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 搜索框 */}
      <div className="px-3 py-2 border-b border-border bg-surface-1/50 shrink-0">
        <div className="flex items-center gap-2">
          <i className="fas fa-search text-xs text-ink-faint"></i>
          <Input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder={k8sT.podList.searchPlaceholder}
            className="flex-1 h-7 px-2 text-xs"
          />
          {searchText && (
            <button
              onClick={() => setSearchText('')}
              className="text-ink-faint hover:text-ink-muted px-1"
            >
              <i className="fas fa-times text-xs"></i>
            </button>
          )}
        </div>
      </div>

      {/* 表格 */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
        <thead className="sticky top-0 bg-surface-1 text-ink-muted border-b border-border">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.status}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.name}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.restarts}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.age}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.node}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.ip}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.podList.actions || '操作'}</th>
          </tr>
        </thead>
        <tbody>
          {/* 加载中 */}
          {isLoading && (
            <tr>
              <td colSpan={7} className="px-3 py-8 text-center text-ink-faint">
                <i className="fas fa-spinner fa-spin mr-2"></i>
                {t.common.loading}
              </td>
            </tr>
          )}

          {/* 请求出错 */}
          {isError && (
            <tr>
              <td colSpan={7} className="px-3 py-8 text-center text-danger">
                <i className="fas fa-exclamation-triangle mr-2"></i>
                {errorMessage}
              </td>
            </tr>
          )}

          {/* 空数据 */}
          {!isLoading && !isError && filteredPods.length === 0 && (
            <tr>
              <td colSpan={7} className="px-3 py-8 text-center text-ink-faint">
                {searchText ? k8sT.podList.noMatch.replace('{text}', searchText) : k8sT.podList.noPods}
              </td>
            </tr>
          )}

          {/* Pod 行 */}
          {filteredPods.map((pod) => (
            <tr
              key={`${pod.namespace}/${pod.name}`}
              onClick={() => handleRowClick(pod)}
              className="border-b border-border hover:bg-surface-1/50 cursor-pointer transition-colors"
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
                <div className="text-ink font-medium truncate max-w-[240px]">{pod.name}</div>
                <div className="text-xs text-ink-faint truncate">{pod.namespace}</div>
              </td>

              {/* 重启次数 */}
              <td className="px-3 py-2 text-ink-muted">
                {pod.restarts > 0 ? (
                  <span className={pod.restarts > 5 ? 'text-danger' : 'text-accent-warning'}>
                    {pod.restarts}
                  </span>
                ) : (
                  <span className="text-ink-faint">0</span>
                )}
              </td>

              {/* 运行时间 */}
              <td className="px-3 py-2 text-ink-muted text-xs">
                {formatAge(pod.created_at)}
              </td>

              {/* 节点 */}
              <td className="px-3 py-2 text-ink-muted truncate max-w-[140px]">
                {pod.node || '-'}
              </td>

              {/* IP */}
              <td className="px-3 py-2 text-ink-muted font-mono text-xs">
                {pod.pod_ip || '-'}
              </td>

              {/* 操作：下载日志 */}
              <td className="px-3 py-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownloadLogs(pod.name, pod.namespace);
                  }}
                  className="text-ink-muted hover:text-accent-info transition-colors"
                  title="下载日志"
                >
                  <i className="fas fa-download text-xs"></i>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
};
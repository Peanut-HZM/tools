/**
 * K8s 控制台 - 工作负载列表
 *
 * 展示 Deployment / StatefulSet / DaemonSet 等工作负载
 * 字段：类型、名称、就绪、可用、镜像、创建时间
 */
import React from 'react';
import { Loader2, AlertTriangle, Rocket, Database, Settings, Copy, ListChecks, CalendarClock, Box } from 'lucide-react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sDeployments } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';
import { formatAge } from './utils';

export const WorkloadList: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, selectedNamespaces, namespaces, setSelectedResource } = useK8sStore();

  const effectiveNamespaces = selectedNamespaces.length === 0 ? namespaces : selectedNamespaces;
  const { data: workloads = [], isLoading, error } = useK8sDeployments(activeConnectionId, effectiveNamespaces);
  const isError = !!error;
  const errorMessage = error instanceof Error ? error.message : k8sT.errors.CONNECTION_FAILED;

  /** 点击行，选中该工作负载 */
  const handleRowClick = (wl: typeof workloads[0]) => {
    setSelectedResource({
      type: wl.kind.toLowerCase(),
      namespace: wl.namespace,
      name: wl.name,
    });
  };

  /** 根据 kind 返回图标 */
  const getKindIcon = (kind: string): React.ComponentType<{ className?: string }> => {
    switch (kind.toLowerCase()) {
      case 'deployment': return Rocket;
      case 'statefulset': return Database;
      case 'daemonset': return Settings;
      case 'replicaset': return Copy;
      case 'job': return ListChecks;
      case 'cronjob': return CalendarClock;
      default: return Box;
    }
  };

  /** 就绪状态颜色 */
  const getReadyColor = (ready: string, desired: number): string => {
    const [current] = ready.split('/').map(Number);
    if (current >= desired) return 'text-success';
    if (current > 0) return 'text-accent-warning';
    return 'text-danger';
  };

  return (
    <div className="flex-1 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-surface-1 text-ink-muted border-b border-border">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{k8sT.workloadList.kind}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.workloadList.name}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.workloadList.ready}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.workloadList.available}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.workloadList.images}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.workloadList.age}</th>
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-ink-faint">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Loading...
              </td>
            </tr>
          )}

          {isError && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-danger">
                <AlertTriangle className="w-4 h-4 mr-2" />
                {errorMessage}
              </td>
            </tr>
          )}

          {!isLoading && !isError && workloads.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-ink-faint">
                {k8sT.workloadList.noWorkloads}
              </td>
            </tr>
          )}

          {workloads.map((wl) => (
            <tr
              key={`${wl.namespace}/${wl.kind}/${wl.name}`}
              onClick={() => handleRowClick(wl)}
              className="border-b border-border hover:bg-surface-1/50 cursor-pointer transition-colors"
            >
              {/* 类型 */}
              <td className="px-3 py-2">
                <div className="flex items-center gap-1.5">
                  {(() => {
                    const KindIcon = getKindIcon(wl.kind);
                    return <KindIcon className="w-3 h-3 text-accent-info mr-1" />;
                  })()}
                  <span className="text-ink-muted text-xs">{wl.kind}</span>
                </div>
              </td>

              {/* 名称 + 命名空间 */}
              <td className="px-3 py-2">
                <div className="text-ink font-medium truncate max-w-[240px]">{wl.name}</div>
                <div className="text-xs text-ink-faint truncate">{wl.namespace}</div>
              </td>

              {/* 就绪 */}
              <td className={`px-3 py-2 font-mono text-xs ${getReadyColor(wl.ready, wl.desired)}`}>
                {wl.ready}
              </td>

              {/* 可用 */}
              <td className="px-3 py-2 text-ink-muted font-mono text-xs">
                {wl.available}
              </td>

              {/* 镜像 */}
              <td className="px-3 py-2 text-ink-muted text-xs truncate max-w-[200px]">
                {wl.images.length > 0 ? wl.images.join(', ') : '-'}
              </td>

              {/* 创建时间 */}
              <td className="px-3 py-2 text-ink-muted text-xs">
                {formatAge(wl.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

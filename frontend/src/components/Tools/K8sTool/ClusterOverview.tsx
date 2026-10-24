import { Activity, Boxes, CircleAlert, Server } from 'lucide-react';
import { useK8sNodes } from '../../../hooks/useK8sClient';
import { useK8sStore } from '../../../stores/k8sStore';

export function ClusterOverview() {
  const { connections, activeConnectionId } = useK8sStore();
  const connection = connections.find((item) => item.id === activeConnectionId);
  const nodesQuery = useK8sNodes(activeConnectionId);

  if (!connection) return null;

  const status = connection.last_test_error
    ? { label: '连接异常', className: 'text-danger bg-danger/10 border-danger/20', Icon: CircleAlert }
    : connection.last_test_at
      ? { label: '已验证连接', className: 'text-success bg-success/10 border-success/20', Icon: Activity }
      : { label: '未验证连接', className: 'text-ink-muted bg-surface-2 border-border', Icon: Activity };
  const StatusIcon = status.Icon;

  return (
    <section className="grid grid-cols-1 gap-2 border-b border-border bg-canvas px-3 py-3 xl:grid-cols-[minmax(0,1fr)_140px_140px]">
      <div className="min-w-0 rounded-lg border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 dark:border-blue-400/15 dark:from-blue-400/10 dark:to-indigo-400/10">
        <div className="flex items-center gap-2 min-w-0">
          <Boxes className="h-4 w-4 text-accent-info shrink-0" />
          <h1 className="font-semibold text-ink truncate">{connection.name}</h1>
          <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs shrink-0 ${status.className}`}>
            <StatusIcon className="h-3 w-3" />
            {status.label}
          </span>
        </div>
        <p className="mt-1 truncate font-mono text-xs text-ink-faint" title={connection.server || connection.cluster_name}>
          {connection.server || connection.cluster_name || '未提供连接地址'}
        </p>
      </div>

      <div className="min-w-[140px] rounded-lg border border-border bg-surface-1 px-4 py-3">
        <div className="flex items-center gap-2 text-xs text-ink-faint">
          <Server className="h-3.5 w-3.5" />
          节点
        </div>
        <p className="mt-1 text-lg font-semibold text-ink">
          {nodesQuery.isLoading ? '加载中' : nodesQuery.isError ? '不可用' : nodesQuery.data?.length ?? 0}
        </p>
      </div>

      <div className="min-w-[140px] rounded-lg border border-border bg-surface-1 px-4 py-3">
        <div className="flex items-center gap-2 text-xs text-ink-faint">
          <Activity className="h-3.5 w-3.5" />
          连通性检查
        </div>
        <p className="mt-1 text-sm font-medium text-ink">
          {connection.last_test_at ? '已完成' : '未执行'}
        </p>
      </div>
    </section>
  );
}

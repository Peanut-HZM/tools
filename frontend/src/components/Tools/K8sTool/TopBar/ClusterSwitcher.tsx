/**
 * K8s 控制台 - 集群切换器
 *
 * 顶部下拉菜单，按 last_test_at 排序（最近测试的在前）
 * 健康状态用绿/红/灰圆点指示
 */
import React from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useI18n } from '../../../../i18n';
import type { K8sConnection } from '../types';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
} from '@/components/ui/DropdownMenu';

/**
 * 根据测试结果返回健康状态圆点颜色类名
 */
function getHealthDotClass(conn: K8sConnection): string {
  if (conn.last_test_error) return 'bg-danger';
  if (conn.last_test_at) return 'bg-success';
  return 'bg-surface-3';
}

/**
 * 按 last_test_at 降序排序连接
 * 有时间的排在前面，null 的排最后
 */
function sortByLastTest(connections: K8sConnection[]): K8sConnection[] {
  return [...connections].sort((a, b) => {
    if (!a.last_test_at && !b.last_test_at) return 0;
    if (!a.last_test_at) return 1;
    if (!b.last_test_at) return -1;
    return new Date(b.last_test_at).getTime() - new Date(a.last_test_at).getTime();
  });
}

export const ClusterSwitcher: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { connections, activeConnectionId, setActiveConnection } = useK8sStore();

  // 当前活跃连接
  const activeConn = connections.find((c) => c.id === activeConnectionId);
  // 按 last_test_at 排序的连接列表
  const sortedConns = sortByLastTest(connections);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex items-center gap-2 px-3 py-1.5 bg-surface-1 border border-border rounded-md text-sm text-ink hover:border-border hover:bg-surface-2 transition-colors min-w-[180px] max-w-[260px] outline-none"
        aria-label={k8sT.topBar.selectCluster}
      >
        {activeConn ? (
          <>
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getHealthDotClass(activeConn)}`}></span>
            <span className="truncate">{activeConn.name}</span>
          </>
        ) : (
          <span className="text-ink-faint">{k8sT.topBar.selectCluster}</span>
        )}
        <ChevronDown className="w-3 h-3 ml-auto text-ink-muted" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 max-h-80 overflow-y-auto">
        {sortedConns.length === 0 ? (
          <DropdownMenuLabel className="px-3 py-4 text-sm text-ink-faint text-center">
            {k8sT.emptyConnections}
          </DropdownMenuLabel>
        ) : (
          sortedConns.map((conn) => {
            const isActive = conn.id === activeConnectionId;
            return (
              <DropdownMenuItem
                key={conn.id}
                onSelect={() => setActiveConnection(conn.id)}
                className={`flex items-center gap-2 px-3 py-2 cursor-pointer ${
                  isActive
                    ? 'bg-accent/20 text-accent-info focus:bg-accent/20 focus:text-accent-info'
                    : 'text-ink-muted focus:text-ink'
                }`}
              >
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getHealthDotClass(conn)}`}></span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{conn.name}</div>
                  <div className="text-xs text-ink-faint truncate">{conn.server || conn.cluster_name}</div>
                </div>
                {isActive && (
                  <Check className="w-3 h-3 text-accent-info flex-shrink-0" />
                )}
              </DropdownMenuItem>
            );
          })
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

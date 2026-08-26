/**
 * K8s 资源详情 - 概览面板
 *
 * 展示 Pod 的基本信息、标签、注解、状态条件和 Owner Reference
 * 数据来源：K8sPodDetail 类型（由后端 /pods/{name} 返回）
 */
import React from 'react';
import { Link } from 'lucide-react';
import { useI18n } from '../../../../i18n';
import { formatAge } from '../ResourceTabs/utils';
import type { K8sPodDetail } from '../types';
import { Badge } from '@/components/ui/Badge';

interface Props {
  pod: K8sPodDetail;
}

/** 状态徽章颜色 */
const getPhaseColor = (phase: string): string => {
  switch (phase.toLowerCase()) {
    case 'running': return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'pending': return 'bg-accent-warning/20 text-accent-warning border-yellow-500/30';
    case 'failed': return 'bg-danger/20 text-danger border-red-500/30';
    case 'succeeded': return 'bg-accent-info/20 text-accent-info border-accent-info/30';
    default: return 'bg-surface-3/20 text-ink-muted border-border/30';
  }
};

/** 条件状态颜色 */
const getConditionColor = (status: string): string => {
  switch (status) {
    case 'True': return 'text-green-400';
    case 'False': return 'text-danger';
    default: return 'text-accent-warning';
  }
};

export const OverviewPanel: React.FC<Props> = ({ pod }) => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const ot = k8sT.resourceDetail.overview;

  /** 渲染标签/注解键值对 */
  const renderKeyValueMap = (
    data: Record<string, string>,
    emptyText: string,
  ) => {
    const entries = Object.entries(data);
    if (entries.length === 0) {
      return <div className="text-ink-faint text-xs italic">{emptyText}</div>;
    }
    return (
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([key, value]) => (
          <span
            key={key}
            className="px-2 py-0.5 bg-surface-2/50 border border-border/50 rounded text-xs text-ink-muted font-mono truncate max-w-[300px]"
            title={`${key}=${value}`}
          >
            <span className="text-accent-info">{key}</span>
            <span className="text-ink-faint">=</span>
            <span>{value}</span>
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="p-4 overflow-y-auto h-full space-y-5">
      {/* 基本信息网格 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-3">
          {ot.title}
        </h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2.5">
          {/* 阶段 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.phase}</span>
            <Badge variant={
              pod.phase.toLowerCase() === 'running' ? 'success' :
              pod.phase.toLowerCase() === 'failed' ? 'destructive' :
              pod.phase.toLowerCase() === 'succeeded' ? 'default' :
              'secondary'
            }>
              {pod.phase}
            </Badge>
          </div>

          {/* 状态描述 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.status}</span>
            <span className="text-xs text-ink truncate">{pod.status || '-'}</span>
          </div>

          {/* 节点 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.node}</span>
            <span className="text-xs text-ink truncate font-mono">{pod.node || '-'}</span>
          </div>

          {/* Pod IP */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.podIp}</span>
            <span className="text-xs text-ink font-mono">{pod.pod_ip || '-'}</span>
          </div>

          {/* 主机 IP */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.hostIp}</span>
            <span className="text-xs text-ink font-mono">{pod.host_ip || '-'}</span>
          </div>

          {/* QoS 类别 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.qosClass}</span>
            <span className="text-xs text-ink font-mono">{pod.qos_class || '-'}</span>
          </div>

          {/* 创建时间 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-faint w-20 shrink-0">{ot.createdAt}</span>
            <span className="text-xs text-ink-muted">{formatAge(pod.created_at)}</span>
          </div>
        </div>
      </div>

      {/* 标签 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {ot.labels}
          <span className="ml-1.5 text-ink-faint normal-case font-normal">
            ({Object.keys(pod.labels).length})
          </span>
        </h4>
        {renderKeyValueMap(pod.labels, ot.noAnnotations)}
      </div>

      {/* 注解 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {ot.annotations}
          <span className="ml-1.5 text-ink-faint normal-case font-normal">
            ({Object.keys(pod.annotations).length})
          </span>
        </h4>
        {renderKeyValueMap(pod.annotations, ot.noAnnotations)}
      </div>

      {/* 状态条件 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {ot.conditions}
        </h4>
        {pod.conditions.length === 0 ? (
          <div className="text-xs text-ink-faint italic">{ot.noConditions}</div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-ink-faint border-b border-border">
                <th className="text-left py-1 font-medium">Type</th>
                <th className="text-left py-1 font-medium">Status</th>
                <th className="text-left py-1 font-medium">Reason</th>
                <th className="text-left py-1 font-medium">Message</th>
                <th className="text-left py-1 font-medium">Transition</th>
              </tr>
            </thead>
            <tbody>
              {pod.conditions.map((c) => (
                <tr key={c.type} className="border-b border-border">
                  <td className="py-1.5 text-ink-muted font-mono">{c.type}</td>
                  <td className={`py-1.5 font-mono font-medium ${getConditionColor(c.status)}`}>
                    {c.status}
                  </td>
                  <td className="py-1.5 text-ink-muted">{c.reason || '-'}</td>
                  <td className="py-1.5 text-ink-muted truncate max-w-[200px]" title={c.message}>
                    {c.message || '-'}
                  </td>
                  <td className="py-1.5 text-ink-faint text-xs">
                    {formatAge(c.last_transition_time)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Owner Reference */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {ot.ownerReferences}
        </h4>
        {pod.owner_references.length === 0 ? (
          <div className="text-xs text-ink-faint italic">{ot.noOwner}</div>
        ) : (
          <div className="space-y-1.5">
            {pod.owner_references.map((ref) => (
              <div
                key={ref.uid}
                className="flex items-center gap-2 px-2 py-1.5 bg-surface-1/50 border border-border/50 rounded text-xs"
              >
                <Link className="w-3 h-3 text-accent-info" />
                <span className="text-accent-info font-medium">{ref.kind}</span>
                <span className="text-ink-muted">/</span>
                <span className="text-ink font-mono">{ref.name}</span>
                <span className="text-ink-faint text-xs ml-auto font-mono truncate max-w-[160px]">
                  {ref.uid}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

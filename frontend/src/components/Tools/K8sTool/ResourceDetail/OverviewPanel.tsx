/**
 * K8s 资源详情 - 概览面板
 *
 * 展示 Pod 的基本信息、标签、注解、状态条件和 Owner Reference
 * 数据来源：K8sPodDetail 类型（由后端 /pods/{name} 返回）
 */
import React from 'react';
import { useI18n } from '../../../../i18n';
import { formatAge } from '../ResourceTabs/utils';
import type { K8sPodDetail } from '../types';

interface Props {
  pod: K8sPodDetail;
}

/** 状态徽章颜色 */
const getPhaseColor = (phase: string): string => {
  switch (phase.toLowerCase()) {
    case 'running': return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'pending': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'failed': return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'succeeded': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  }
};

/** 条件状态颜色 */
const getConditionColor = (status: string): string => {
  switch (status) {
    case 'True': return 'text-green-400';
    case 'False': return 'text-red-400';
    default: return 'text-yellow-400';
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
      return <div className="text-slate-500 text-xs italic">{emptyText}</div>;
    }
    return (
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([key, value]) => (
          <span
            key={key}
            className="px-2 py-0.5 bg-slate-700/50 border border-slate-600/50 rounded text-xs text-slate-300 font-mono truncate max-w-[300px]"
            title={`${key}=${value}`}
          >
            <span className="text-blue-400">{key}</span>
            <span className="text-slate-500">=</span>
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
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
          {ot.title}
        </h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2.5">
          {/* 阶段 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.phase}</span>
            <span className={`px-2 py-0.5 rounded border text-xs font-medium ${getPhaseColor(pod.phase)}`}>
              {pod.phase}
            </span>
          </div>

          {/* 状态描述 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.status}</span>
            <span className="text-xs text-slate-200 truncate">{pod.status || '-'}</span>
          </div>

          {/* 节点 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.node}</span>
            <span className="text-xs text-slate-200 truncate font-mono">{pod.node || '-'}</span>
          </div>

          {/* Pod IP */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.podIp}</span>
            <span className="text-xs text-slate-200 font-mono">{pod.pod_ip || '-'}</span>
          </div>

          {/* 主机 IP */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.hostIp}</span>
            <span className="text-xs text-slate-200 font-mono">{pod.host_ip || '-'}</span>
          </div>

          {/* QoS 类别 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.qosClass}</span>
            <span className="text-xs text-slate-200 font-mono">{pod.qos_class || '-'}</span>
          </div>

          {/* 创建时间 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">{ot.createdAt}</span>
            <span className="text-xs text-slate-400">{formatAge(pod.created_at)}</span>
          </div>
        </div>
      </div>

      {/* 标签 */}
      <div>
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
          {ot.labels}
          <span className="ml-1.5 text-slate-500 normal-case font-normal">
            ({Object.keys(pod.labels).length})
          </span>
        </h4>
        {renderKeyValueMap(pod.labels, ot.noAnnotations)}
      </div>

      {/* 注解 */}
      <div>
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
          {ot.annotations}
          <span className="ml-1.5 text-slate-500 normal-case font-normal">
            ({Object.keys(pod.annotations).length})
          </span>
        </h4>
        {renderKeyValueMap(pod.annotations, ot.noAnnotations)}
      </div>

      {/* 状态条件 */}
      <div>
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
          {ot.conditions}
        </h4>
        {pod.conditions.length === 0 ? (
          <div className="text-xs text-slate-500 italic">{ot.noConditions}</div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-700">
                <th className="text-left py-1 font-medium">Type</th>
                <th className="text-left py-1 font-medium">Status</th>
                <th className="text-left py-1 font-medium">Reason</th>
                <th className="text-left py-1 font-medium">Message</th>
                <th className="text-left py-1 font-medium">Transition</th>
              </tr>
            </thead>
            <tbody>
              {pod.conditions.map((c) => (
                <tr key={c.type} className="border-b border-slate-800">
                  <td className="py-1.5 text-slate-300 font-mono">{c.type}</td>
                  <td className={`py-1.5 font-mono font-medium ${getConditionColor(c.status)}`}>
                    {c.status}
                  </td>
                  <td className="py-1.5 text-slate-400">{c.reason || '-'}</td>
                  <td className="py-1.5 text-slate-400 truncate max-w-[200px]" title={c.message}>
                    {c.message || '-'}
                  </td>
                  <td className="py-1.5 text-slate-500 text-xs">
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
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
          {ot.ownerReferences}
        </h4>
        {pod.owner_references.length === 0 ? (
          <div className="text-xs text-slate-500 italic">{ot.noOwner}</div>
        ) : (
          <div className="space-y-1.5">
            {pod.owner_references.map((ref) => (
              <div
                key={ref.uid}
                className="flex items-center gap-2 px-2 py-1.5 bg-slate-800/50 border border-slate-700/50 rounded text-xs"
              >
                <i className="fas fa-link text-blue-400 text-xs"></i>
                <span className="text-blue-400 font-medium">{ref.kind}</span>
                <span className="text-slate-400">/</span>
                <span className="text-slate-200 font-mono">{ref.name}</span>
                <span className="text-slate-600 text-xs ml-auto font-mono truncate max-w-[160px]">
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

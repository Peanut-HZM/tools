/**
 * K8s 资源详情 - 事件面板
 *
 * 展示与当前资源相关的 K8s Events，按 last_seen 降序排列
 * 数据来源：api.listEvents() + fieldSelector 过滤
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/k8sToolApi';
import { formatAge } from '../ResourceTabs/utils';
import type { K8sEventInfo } from '../types';

interface Props {
  configId: string;
  namespace: string;
  /** 资源名称，用于构造 fieldSelector */
  resourceName: string;
  /** 资源类型（'Pod'、'Node' 等），用于构造 fieldSelector */
  resourceKind: string;
}

/** 事件类型颜色 */
const getEventTypeColor = (type: string): string => {
  switch (type) {
    case 'Normal': return 'text-blue-400';
    case 'Warning': return 'text-yellow-400';
    default: return 'text-slate-400';
  }
};

/** 事件类型图标 */
const getEventTypeIcon = (type: string): string => {
  switch (type) {
    case 'Normal': return 'fas fa-info-circle';
    case 'Warning': return 'fas fa-exclamation-triangle';
    default: return 'fas fa-circle';
  }
};

export const EventsPanel: React.FC<Props> = ({
  configId, namespace, resourceName, resourceKind,
}) => {
  const { t } = useI18n();
  const et = t.tools['k8s-tool'].resourceDetail.events;

  // 使用 fieldSelector 过滤当前资源的事件
  const fieldSelector = `involvedObject.name=${resourceName},involvedObject.kind=${resourceKind}`;

  const { data: events = [], isLoading } = useQuery({
    queryKey: ['k8s', configId, 'events', namespace, fieldSelector],
    queryFn: () => api.listEvents(configId, namespace, fieldSelector),
    enabled: !!configId && !!namespace && !!resourceName,
    refetchInterval: 10_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500">
        <i className="fas fa-spinner fa-spin mr-2"></i>
        {t.common.loading}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        <i className="fas fa-bolt mr-2 text-slate-600"></i>
        {et.noEvents}
      </div>
    );
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-slate-800 text-slate-400 border-b border-slate-700">
          <tr>
            <th className="text-left px-3 py-2 font-medium w-20">{et.type}</th>
            <th className="text-left px-3 py-2 font-medium w-28">{et.reason}</th>
            <th className="text-left px-3 py-2 font-medium">{et.message}</th>
            <th className="text-left px-3 py-2 font-medium w-14">{et.count}</th>
            <th className="text-left px-3 py-2 font-medium w-28">{et.lastSeen}</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event: K8sEventInfo, idx: number) => (
            <tr key={`${event.reason}-${idx}`} className="border-b border-slate-800 hover:bg-slate-800/30">
              {/* 类型 */}
              <td className="px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <i className={`${getEventTypeIcon(event.type)} ${getEventTypeColor(event.type)} text-xs`}></i>
                  <span className={`${getEventTypeColor(event.type)} font-medium`}>
                    {event.type}
                  </span>
                </div>
              </td>

              {/* 原因 */}
              <td className="px-3 py-2 text-slate-300 font-mono">
                {event.reason}
              </td>

              {/* 消息 */}
              <td className="px-3 py-2 text-slate-400 truncate max-w-[300px]" title={event.message}>
                {event.message}
              </td>

              {/* 次数 */}
              <td className="px-3 py-2 text-slate-400 text-center">
                {event.count > 1 ? (
                  <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs font-medium">
                    {event.count}
                  </span>
                ) : (
                  event.count
                )}
              </td>

              {/* 最近出现 */}
              <td className="px-3 py-2 text-slate-500">
                {formatAge(event.last_seen)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

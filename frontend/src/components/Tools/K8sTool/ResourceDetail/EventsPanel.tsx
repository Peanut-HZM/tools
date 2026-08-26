/**
 * K8s 资源详情 - 事件面板
 *
 * 展示与当前资源相关的 K8s Events，按 last_seen 降序排列
 * 数据来源：api.listEvents() + fieldSelector 过滤
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Zap, Info, AlertTriangle, Circle } from 'lucide-react';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/k8sToolApi';
import { formatAge } from '../ResourceTabs/utils';
import type { K8sEventInfo } from '../types';
import { Badge } from '@/components/ui/Badge';

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
    case 'Normal': return 'text-accent-info';
    case 'Warning': return 'text-accent-warning';
    default: return 'text-ink-muted';
  }
};

/** 事件类型图标 */
const getEventTypeIcon = (type: string): React.ComponentType<{ className?: string }> => {
  switch (type) {
    case 'Normal': return Info;
    case 'Warning': return AlertTriangle;
    default: return Circle;
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
      <div className="flex items-center justify-center h-full text-ink-faint">
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        {t.common.loading}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-ink-faint text-sm">
        <Zap className="w-4 h-4 mr-2 text-ink-faint" />
        {et.noEvents}
      </div>
    );
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-surface-1 text-ink-muted border-b border-border">
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
            <tr key={`${event.reason}-${idx}`} className="border-b border-border hover:bg-surface-1/30">
              {/* 类型 */}
              <td className="px-3 py-2">
                <div className="flex items-center gap-1.5">
                  {(() => {
                    const EventIcon = getEventTypeIcon(event.type);
                    return <EventIcon className={`${getEventTypeColor(event.type)} w-3 h-3`} />;
                  })()}
                  <span className={`${getEventTypeColor(event.type)} font-medium`}>
                    {event.type}
                  </span>
                </div>
              </td>

              {/* 原因 */}
              <td className="px-3 py-2 text-ink-muted font-mono">
                {event.reason}
              </td>

              {/* 消息 */}
              <td className="px-3 py-2 text-ink-muted truncate max-w-[300px]" title={event.message}>
                {event.message}
              </td>

              {/* 次数 */}
              <td className="px-3 py-2 text-ink-muted text-center">
                {event.count > 1 ? (
                  <Badge variant="warning" className="text-xs">
                    {event.count}
                  </Badge>
                ) : (
                  event.count
                )}
              </td>

              {/* 最近出现 */}
              <td className="px-3 py-2 text-ink-faint">
                {formatAge(event.last_seen)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

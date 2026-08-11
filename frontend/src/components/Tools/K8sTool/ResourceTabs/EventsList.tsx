/**
 * K8s 控制台 - 事件列表
 *
 * 展示 K8s 事件，字段：类型、原因、消息、对象、次数、最近出现
 * Warning 事件用黄色高亮
 */
import React from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sEvents } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';
import { formatAge } from './utils';

export const EventsList: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, selectedNamespaces, namespaces } = useK8sStore();

  const effectiveNamespaces = selectedNamespaces.length === 0 ? namespaces : selectedNamespaces;
  const { data: events = [], isLoading, error } = useK8sEvents(activeConnectionId, effectiveNamespaces);
  const isError = !!error;
  const errorMessage = error instanceof Error ? error.message : k8sT.errors.CONNECTION_FAILED;

  /** 按 last_seen 降序排列（最新事件在前） */
  const sortedEvents = [...events].sort((a, b) => {
    const ta = a.last_seen ? new Date(a.last_seen).getTime() : 0;
    const tb = b.last_seen ? new Date(b.last_seen).getTime() : 0;
    return tb - ta;
  });

  return (
    <div className="flex-1 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-slate-800 text-slate-400 border-b border-slate-700">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{k8sT.eventsList.type}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.eventsList.reason}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.eventsList.message}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.eventsList.object}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.eventsList.count}</th>
            <th className="text-left px-3 py-2 font-medium">{k8sT.eventsList.lastSeen}</th>
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

          {!isLoading && !isError && events.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                {k8sT.eventsList.noEvents}
              </td>
            </tr>
          )}

          {sortedEvents.map((event, idx) => {
            const isWarning = event.type === 'Warning';
            return (
              <tr
                key={`${event.object_namespace}/${event.object_kind}/${event.object_name}/${event.reason}-${idx}`}
                className={`border-b border-slate-800 transition-colors ${
                  isWarning ? 'bg-red-900/10 hover:bg-red-900/20' : 'hover:bg-slate-800/50'
                }`}
              >
                {/* 类型 */}
                <td className="px-3 py-2">
                  <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                    isWarning ? 'text-yellow-400' : 'text-blue-400'
                  }`}>
                    <i className={`fas ${isWarning ? 'fa-exclamation-triangle' : 'fa-info-circle'}`}></i>
                    {event.type}
                  </span>
                </td>

                {/* 原因 */}
                <td className="px-3 py-2">
                  <span className={`text-xs font-mono ${isWarning ? 'text-yellow-300' : 'text-slate-300'}`}>
                    {event.reason}
                  </span>
                </td>

                {/* 消息 */}
                <td className="px-3 py-2 text-slate-400 text-xs truncate max-w-[300px]" title={event.message}>
                  {event.message}
                </td>

                {/* 对象 */}
                <td className="px-3 py-2 text-slate-400 text-xs">
                  <span className="font-mono">
                    {event.object_kind}/{event.object_name}
                  </span>
                  <span className="text-slate-600 ml-1">{event.object_namespace}</span>
                </td>

                {/* 次数 */}
                <td className="px-3 py-2 text-slate-400 text-xs text-center">
                  {event.count > 1 ? (
                    <span className="bg-slate-700 px-1.5 py-0.5 rounded text-xs">{event.count}</span>
                  ) : (
                    event.count
                  )}
                </td>

                {/* 最近出现 */}
                <td className="px-3 py-2 text-slate-400 text-xs">
                  {formatAge(event.last_seen)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

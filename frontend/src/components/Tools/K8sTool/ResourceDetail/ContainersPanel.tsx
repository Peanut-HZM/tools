/**
 * K8s 资源详情 - 容器面板
 *
 * 表格展示 Pod 内所有容器（含 Init 容器）
 * 列：名称、镜像、状态、重启次数、资源请求/限制
 */
import React from 'react';
import { useI18n } from '../../../../i18n';
import type { K8sContainerInfo } from '../types';
import { Badge } from '@/components/ui/Badge';

interface Props {
  containers: K8sContainerInfo[];
  initContainers: K8sContainerInfo[];
}

/** 容器状态颜色 */
const getStateColor = (state: K8sContainerInfo['state']): string => {
  switch (state) {
    case 'running': return 'text-green-400';
    case 'waiting': return 'text-accent-warning';
    case 'terminated': return 'text-danger';
    default: return 'text-ink-muted';
  }
};

/** 容器状态图标 */
const getStateIcon = (state: K8sContainerInfo['state']): string => {
  switch (state) {
    case 'running': return 'fas fa-play-circle';
    case 'waiting': return 'fas fa-hourglass-half';
    case 'terminated': return 'fas fa-stop-circle';
    default: return 'fas fa-question-circle';
  }
};

/** 格式化资源请求/限制 */
const formatResources = (resources: Record<string, string>): string => {
  const entries = Object.entries(resources);
  if (entries.length === 0) return '-';
  return entries.map(([k, v]) => `${k}:${v}`).join(' / ');
};

/** 容器行渲染 */
const ContainerRow: React.FC<{ container: K8sContainerInfo; isInit: boolean; ct: Record<string, string> }> = ({
  container, isInit, ct,
}) => (
  <tr className="border-b border-border hover:bg-surface-1/30">
    {/* 名称 */}
    <td className="px-3 py-2">
      <div className="flex items-center gap-2">
        {isInit && (
          <Badge variant="outline" className="px-1 py-0.5 text-xs">
            init
          </Badge>
        )}
        <span className="text-ink font-medium text-xs">{container.name}</span>
      </div>
    </td>

    {/* 镜像 */}
    <td className="px-3 py-2">
      <span
        className="text-xs text-ink-muted font-mono truncate block max-w-[200px]"
        title={container.image}
      >
        {container.image}
      </span>
    </td>

    {/* 状态 */}
    <td className="px-3 py-2">
      <div className="flex items-center gap-1.5">
        <i className={`${getStateIcon(container.state)} ${getStateColor(container.state)} text-xs`}></i>
        <span className={`text-xs ${getStateColor(container.state)}`}>
          {container.state}
        </span>
        {container.state_detail && container.state !== container.state_detail && (
          <span className="text-xs text-ink-faint truncate max-w-[120px]" title={container.state_detail}>
            ({container.state_detail})
          </span>
        )}
      </div>
    </td>

    {/* 就绪 */}
    <td className="px-3 py-2">
      <span className={`text-xs font-medium ${container.ready ? 'text-green-400' : 'text-danger'}`}>
        {container.ready ? ct.ready : ct.notReady}
      </span>
    </td>

    {/* 重启次数 */}
    <td className="px-3 py-2 text-xs">
      {container.restart_count > 0 ? (
        <span className={container.restart_count > 5 ? 'text-danger font-medium' : 'text-accent-warning'}>
          {container.restart_count}
        </span>
      ) : (
        <span className="text-ink-faint">0</span>
      )}
    </td>

    {/* 资源请求 */}
    <td className="px-3 py-2 text-xs text-ink-muted font-mono">
      {formatResources(container.resources_requests)}
    </td>

    {/* 资源限制 */}
    <td className="px-3 py-2 text-xs text-ink-muted font-mono">
      {formatResources(container.resources_limits)}
    </td>
  </tr>
);

export const ContainersPanel: React.FC<Props> = ({ containers, initContainers }) => {
  const { t } = useI18n();
  const ct = t.tools['k8s-tool'].resourceDetail.containers;

  const allContainers = [
    ...initContainers.map((c) => ({ ...c, _isInit: true })),
    ...containers.map((c) => ({ ...c, _isInit: false })),
  ];

  if (allContainers.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-ink-faint text-sm">
        {ct.noContainers}
      </div>
    );
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-surface-1 text-ink-muted border-b border-border">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{ct.name}</th>
            <th className="text-left px-3 py-2 font-medium">{ct.image}</th>
            <th className="text-left px-3 py-2 font-medium">{ct.state}</th>
            <th className="text-left px-3 py-2 font-medium">Ready</th>
            <th className="text-left px-3 py-2 font-medium">{ct.restarts}</th>
            <th className="text-left px-3 py-2 font-medium">{ct.requests}</th>
            <th className="text-left px-3 py-2 font-medium">{ct.limits}</th>
          </tr>
        </thead>
        <tbody>
          {allContainers.map((c) => (
            <ContainerRow
              key={c.name}
              container={c}
              isInit={c._isInit}
              ct={ct}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};

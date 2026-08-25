/**
 * K8s Pod 资源详情面板
 *
 * 根据 tabId 从 store 的 openedTabs 中读取对应资源信息
 * 支持 8 个子 Tab：Overview / Containers / Logs / Terminal / YAML / Events / Metrics / Related
 *
 * 数据来源：api.getPodDetail()
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useI18n } from '../../../../i18n';
import { useK8sStore } from '../../../../stores/k8sStore';
import * as api from '../../../../api/k8sToolApi';

import { OverviewPanel } from './OverviewPanel';
import { ContainersPanel } from './ContainersPanel';
import { YamlPanel } from './YamlPanel';
import { EventsPanel } from './EventsPanel';
import { MetricsPanel } from './MetricsPanel';
import { RelatedPanel } from './RelatedPanel';
import { LogsViewer } from '../LogsViewer/LogsViewer';
import { K8sTerminalPanel } from '../TerminalPanel/K8sTerminalPanel';

/** PodDetail 组件 Props */
interface PodDetailProps {
  /** 从 BottomPanel 传入的标签 ID，未传时使用 store 中的 activeTabId */
  tabId?: string;
}

/** 子 Tab 定义 */
interface SubTab {
  key: string;
  labelKey: keyof typeof TAB_I18N_KEYS;
  icon: string;
}

/** Tab key → i18n key 映射 */
const TAB_I18N_KEYS = {
  overview: 'overview',
  containers: 'containers',
  logs: 'logs',
  terminal: 'terminal',
  yaml: 'yaml',
  events: 'events',
  metrics: 'metrics',
  related: 'related',
} as const;

const SUB_TABS: SubTab[] = [
  { key: 'overview', labelKey: 'overview', icon: 'fas fa-info-circle' },
  { key: 'containers', labelKey: 'containers', icon: 'fas fa-cube' },
  { key: 'logs', labelKey: 'logs', icon: 'fas fa-stream' },
  { key: 'terminal', labelKey: 'terminal', icon: 'fas fa-terminal' },
  { key: 'yaml', labelKey: 'yaml', icon: 'fas fa-file-code' },
  { key: 'events', labelKey: 'events', icon: 'fas fa-bolt' },
  { key: 'metrics', labelKey: 'metrics', icon: 'fas fa-chart-line' },
  { key: 'related', labelKey: 'related', icon: 'fas fa-project-diagram' },
];

export const PodDetail: React.FC<PodDetailProps> = ({ tabId }) => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const tabT = k8sT.resourceDetail.tabs;

  const {
    activeConnectionId,
    openedTabs,
    activeTabId,
    activeSubTabs,
    setActiveSubTab,
  } = useK8sStore();

  // 如果未传 tabId，使用 store 中的 activeTabId
  const currentTabId = tabId || activeTabId;

  // 从 openedTabs 中查找当前标签
  const currentTab = openedTabs.find((t) => t.id === currentTabId);

  // 子 Tab 状态从 store 读取，按 tabId 维度持久化，跨 Pod 切换不会丢失
  const activeTab = activeSubTabs[currentTabId || ''] || 'overview';

  // 获取 Pod 详情（使用 currentTab 的 namespace 和 name）
  const {
    data: pod,
    isLoading,
    isError,
  } = useQuery({
    queryKey: [
      'k8s',
      activeConnectionId,
      'pod',
      currentTab?.name,
      currentTab?.namespace,
    ],
    queryFn: () =>
      api.getPodDetail(
        activeConnectionId!,
        currentTab!.name,
        currentTab!.namespace,
      ),
    enabled:
      !!activeConnectionId &&
      !!currentTab &&
      currentTab.type === 'pod',
  });

  // 如果没有找到对应标签，不渲染
  if (!currentTab) return null;

  /** 渲染当前激活的子面板 */
  const renderContent = () => {
    // 非 Pod 类型暂无专用详情面板（Deployment/StatefulSet 等）
    if (currentTab.type !== 'pod') {
      return (
        <div className="flex flex-col items-center justify-center h-full text-ink-faint gap-2">
          <i className="fas fa-cube text-3xl text-ink-faint"></i>
          <div className="text-sm">
            资源类型 <span className="text-accent-info font-mono">{currentTab.type}</span> 的详情面板暂未实现
          </div>
          <div className="text-xs text-ink-faint">当前仅支持 Pod 详情视图</div>
        </div>
      );
    }

    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-full text-ink-faint">
          <i className="fas fa-spinner fa-spin mr-2"></i>
          {t.common.loading}
        </div>
      );
    }

    if (isError || !pod) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-danger gap-2">
          <i className="fas fa-exclamation-triangle text-2xl"></i>
          <div className="text-sm">{k8sT.errors.NOT_FOUND}</div>
        </div>
      );
    }

    switch (activeTab) {
      case 'overview':
        return <OverviewPanel pod={pod} />;

      case 'containers':
        return (
          <ContainersPanel
            containers={pod.containers}
            initContainers={pod.init_containers}
          />
        );

      case 'logs':
        return (
          <LogsViewer
            configId={activeConnectionId!}
            podName={pod.name}
            namespace={pod.namespace}
            containers={pod.containers}
          />
        );

      case 'terminal':
        return (
          <K8sTerminalPanel
            configId={activeConnectionId!}
            podName={pod.name}
            namespace={pod.namespace}
            containers={pod.containers}
            isActive={activeTab === 'terminal'}
          />
        );

      case 'yaml':
        return (
          <YamlPanel
            configId={activeConnectionId!}
            resourceType={currentTab.type}
            namespace={pod.namespace}
            name={pod.name}
          />
        );

      case 'events':
        return (
          <EventsPanel
            configId={activeConnectionId!}
            namespace={pod.namespace}
            resourceName={pod.name}
            resourceKind="Pod"
          />
        );

      case 'metrics':
        return (
          <MetricsPanel
            podName={pod.name}
            namespace={pod.namespace}
          />
        );

      case 'related':
        return (
          <RelatedPanel
            configId={activeConnectionId!}
            namespace={pod.namespace}
            podName={pod.name}
          />
        );

      default:
        return <OverviewPanel pod={pod} />;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 头部：Pod 名称 + 命名空间 + 状态 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-1/50 shrink-0">
        <div className="flex items-center gap-2">
          <i className="fas fa-cube text-accent-info"></i>
          <h3 className="text-sm font-semibold text-ink truncate max-w-[300px]">
            {currentTab.name}
          </h3>
          <span className="text-xs text-ink-faint font-mono">
            {currentTab.namespace}
          </span>
          {pod?.phase && (
            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
              pod.phase === 'Running'
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : pod.phase === 'Failed'
                ? 'bg-danger/20 text-danger border border-red-500/30'
                : 'bg-accent-warning/20 text-accent-warning border border-yellow-500/30'
            }`}>
              {pod.phase}
            </span>
          )}
        </div>
        {/* 关闭按钮由 BottomPanel 的 TabBar 处理 */}
      </div>

      {/* 子 Tab 栏 */}
      <div className="flex items-center px-2 border-b border-border bg-surface-1/30 shrink-0 overflow-x-auto">
        {SUB_TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => {
                if (currentTabId) {
                  setActiveSubTab(currentTabId, tab.key);
                }
              }}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                isActive
                  ? 'border-blue-500 text-accent-info'
                  : 'border-transparent text-ink-muted hover:text-ink hover:border-border'
              }`}
            >
              <i className={`${tab.icon} text-xs`}></i>
              {tabT[tab.labelKey]}
            </button>
          );
        })}
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {renderContent()}
      </div>
    </div>
  );
};

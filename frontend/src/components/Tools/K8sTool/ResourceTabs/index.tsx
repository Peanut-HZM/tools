/**
 * K8s 控制台 - 资源标签页
 *
 * 标签切换：Pods / Workloads / Nodes / Events
 * 根据当前 resourceType 渲染对应的列表组件
 */
import React from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useI18n } from '../../../../i18n';
import { PodList } from './PodList';
import { WorkloadList } from './WorkloadList';
import { NodeList } from './NodeList';
import { EventsList } from './EventsList';

/** 标签配置 */
interface TabConfig {
  key: string;
  labelKey: 'pods' | 'workloads' | 'nodes' | 'events';
  icon: string;
}

const TABS: TabConfig[] = [
  { key: 'pods', labelKey: 'pods', icon: 'fas fa-cube' },
  { key: 'workloads', labelKey: 'workloads', icon: 'fas fa-rocket' },
  { key: 'nodes', labelKey: 'nodes', icon: 'fas fa-server' },
  { key: 'events', labelKey: 'events', icon: 'fas fa-bolt' },
];

export const ResourceTabs: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { resourceType, setResourceType } = useK8sStore();

  /** 渲染当前激活的资源列表 */
  const renderContent = () => {
    switch (resourceType) {
      case 'pods': return <PodList />;
      case 'workloads': return <WorkloadList />;
      case 'nodes': return <NodeList />;
      case 'events': return <EventsList />;
      default: return <PodList />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 标签栏 */}
      <div className="flex items-center px-4 border-b border-border bg-surface-1/30">
        {TABS.map((tab) => {
          const isActive = resourceType === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setResourceType(tab.key as 'pods' | 'workloads' | 'nodes' | 'events')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? 'border-blue-500 text-accent-info'
                  : 'border-transparent text-ink-muted hover:text-ink hover:border-border'
              }`}
            >
              <i className={`${tab.icon} text-xs`}></i>
              {k8sT.resourceTabs[tab.labelKey]}
            </button>
          );
        })}
      </div>

      {/* 资源列表内容 */}
      {renderContent()}
    </div>
  );
};

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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';

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
      <Tabs value={resourceType} onValueChange={(v) => setResourceType(v as 'pods' | 'workloads' | 'nodes' | 'events')} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="mx-4 bg-transparent h-auto p-0 justify-start border-b border-border bg-surface-1/30">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.key} value={tab.key} className="rounded-none bg-transparent px-4 py-2.5 text-sm font-medium border-b-2 border-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-blue-500 data-[state=active]:text-accent-info data-[state=inactive]:text-ink-muted">
              <i className={`${tab.icon} text-xs`}></i>
              {k8sT.resourceTabs[tab.labelKey]}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value={resourceType} className="flex-1 overflow-hidden mt-0">
          {renderContent()}
        </TabsContent>
      </Tabs>
    </div>
  );
};

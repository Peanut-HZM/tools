/**
 * K8s 控制台 - 资源标签页
 *
 * 标签切换：Pods / Workloads / Nodes / Events
 * 根据当前 resourceType 渲染对应的列表组件
 */
import React from 'react';
import { Box, Rocket, Server, Zap } from 'lucide-react';
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
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const TABS: TabConfig[] = [
  { key: 'workloads', labelKey: 'workloads', icon: Rocket, color: 'text-violet-600 bg-violet-50 dark:bg-violet-400/10 dark:text-violet-300' },
  { key: 'pods', labelKey: 'pods', icon: Box, color: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-400/10 dark:text-emerald-300' },
  { key: 'nodes', labelKey: 'nodes', icon: Server, color: 'text-blue-600 bg-blue-50 dark:bg-blue-400/10 dark:text-blue-300' },
  { key: 'events', labelKey: 'events', icon: Zap, color: 'text-amber-600 bg-amber-50 dark:bg-amber-400/10 dark:text-amber-300' },
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
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">
      <Tabs value={resourceType} onValueChange={(v) => setResourceType(v as 'pods' | 'workloads' | 'nodes' | 'events')} className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <TabsList className="grid h-auto shrink-0 grid-cols-2 gap-2 rounded-none border-0 bg-transparent p-3 xl:grid-cols-4">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.key} value={tab.key} className="h-auto min-w-0 justify-start gap-3 rounded-lg border border-border bg-surface-1 px-3 py-3 text-left shadow-sm data-[state=active]:border-indigo-200 data-[state=active]:bg-indigo-50 data-[state=active]:text-ink data-[state=active]:shadow-sm dark:data-[state=active]:border-indigo-400/30 dark:data-[state=active]:bg-indigo-400/10">
              {(() => {
                const TabIcon = tab.icon;
                return <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${tab.color}`}><TabIcon className="h-4 w-4" /></span>;
              })()}
              <span className="min-w-0">
                <span className="block truncate text-xs font-semibold text-ink">{k8sT.resourceTabs[tab.labelKey]}</span>
                <span className="mt-0.5 block truncate text-[10px] font-normal text-ink-faint">{k8sT.resourceDescriptions[tab.labelKey]}</span>
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value={resourceType} className="mx-3 mb-3 mt-0 flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-border bg-surface-1 shadow-sm">
          {renderContent()}
        </TabsContent>
      </Tabs>
    </div>
  );
};

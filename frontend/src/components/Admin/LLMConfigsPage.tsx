/**
 * 大模型配置管理页面
 * Task 1.5.4 — 重构为 3 tabs（供应商 + 模型 + 额度管理）
 */
import { useState } from 'react';
import { ProvidersTab, ModelsTab, QuotaManagementTab } from './LLMConfigs';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';

type TabKey = 'providers' | 'models' | 'quota';

export default function LLMConfigsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('providers');

  return (
    <div>
      <h2 className="text-2xl font-bold text-ink mb-6">大模型配置管理</h2>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabKey)}>
        <TabsList className="mb-6">
          <TabsTrigger value="providers">模型供应商</TabsTrigger>
          <TabsTrigger value="models">模型配置</TabsTrigger>
          <TabsTrigger value="quota">额度管理</TabsTrigger>
        </TabsList>

        <TabsContent value="providers"><ProvidersTab /></TabsContent>
        <TabsContent value="models"><ModelsTab /></TabsContent>
        <TabsContent value="quota"><QuotaManagementTab /></TabsContent>
      </Tabs>
    </div>
  );
}

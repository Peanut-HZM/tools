/**
 * 图像生成管理页面 — Task 12.1
 * 5 tabs: 使用统计 / Dify 配置 / 降级配置 / 保留策略 / 用户配额
 */
import { useState } from 'react';
import { useI18n } from '../../../i18n';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import UsageStats from './tabs/UsageStats';
import DifyConfigPanel from './tabs/DifyConfigPanel';
import DegradationConfigPanel from './tabs/DegradationConfigPanel';
import RetentionConfigPanel from './tabs/RetentionConfigPanel';
import UserQuotaTable from './tabs/UserQuotaTable';
import { LineChart, Plug, Shield, Trash2, Users, type ReactNode } from 'lucide-react';

type TabKey = 'stats' | 'dify' | 'degradation' | 'retention' | 'quota';

export default function ImageGenerationAdmin() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const [activeTab, setActiveTab] = useState<TabKey>('stats');

  const tabs: { key: TabKey; label: string; icon: ReactNode }[] = [
    { key: 'stats', label: igT.tabs.stats, icon: <LineChart className="w-4 h-4" /> },
    { key: 'dify', label: igT.tabs.difyConfig, icon: <Plug className="w-4 h-4" /> },
    { key: 'degradation', label: igT.tabs.degradation, icon: <Shield className="w-4 h-4" /> },
    { key: 'retention', label: igT.tabs.retention, icon: <Trash2 className="w-4 h-4" /> },
    { key: 'quota', label: igT.tabs.userQuota, icon: <Users className="w-4 h-4" /> },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold text-ink-inverse mb-6">{igT.admin.title}</h2>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabKey)}>
        <TabsList className="mb-6">
          {tabs.map((tab) => (
            <TabsTrigger key={tab.key} value={tab.key} className="flex items-center gap-2">
              {tab.icon}
              <span>{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="stats"><UsageStats /></TabsContent>
        <TabsContent value="dify"><DifyConfigPanel /></TabsContent>
        <TabsContent value="degradation"><DegradationConfigPanel /></TabsContent>
        <TabsContent value="retention"><RetentionConfigPanel /></TabsContent>
        <TabsContent value="quota"><UserQuotaTable /></TabsContent>
      </Tabs>
    </div>
  );
}
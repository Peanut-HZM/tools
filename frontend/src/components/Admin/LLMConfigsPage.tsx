/**
 * 大模型配置管理页面
 * Task 1.5.4 — 重构为 3 tabs（供应商 + 模型 + 额度管理）
 */
import { useState } from 'react';
import { ProvidersTab, ModelsTab, QuotaManagementTab } from './LLMConfigs';
import { Button } from '@/components/ui/Button';

type TabKey = 'providers' | 'models' | 'quota';

export default function LLMConfigsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('providers');

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'providers', label: '模型供应商' },
    { key: 'models', label: '模型配置' },
    { key: 'quota', label: '额度管理' },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold text-ink-inverse mb-6">大模型配置管理</h2>

      {/* Tab 切换 */}
      <div className="flex gap-1 mb-6 bg-surface-2 rounded-lg p-1 border border-border">
        {tabs.map((tab) => (
          <Button
            key={tab.key}
            variant={activeTab === tab.key ? 'default' : 'secondary'}
            onClick={() => setActiveTab(tab.key)}
            className="flex-1"
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Tab 内容 */}
      {activeTab === 'providers' && <ProvidersTab />}
      {activeTab === 'models' && <ModelsTab />}
      {activeTab === 'quota' && <QuotaManagementTab />}
    </div>
  );
}

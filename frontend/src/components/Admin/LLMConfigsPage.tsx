/**
 * 大模型配置管理页面
 * Task 1.5.4 — 重构为 3 tabs（供应商 + 模型 + 额度管理）
 */
import { useState } from 'react';
import { ProvidersTab, ModelsTab, QuotaManagementTab } from './LLMConfigs';

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
      <h2 className="text-2xl font-bold text-white mb-6">大模型配置管理</h2>

      {/* Tab 切换 */}
      <div className="flex gap-1 mb-6 bg-slate-700 rounded-lg p-1 border border-slate-600">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
              activeTab === tab.key
                ? 'bg-cyan-600 text-white'
                : 'text-slate-300 hover:bg-slate-600 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      {activeTab === 'providers' && <ProvidersTab />}
      {activeTab === 'models' && <ModelsTab />}
      {activeTab === 'quota' && <QuotaManagementTab />}
    </div>
  );
}

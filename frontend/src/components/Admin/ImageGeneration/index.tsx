/**
 * 图像生成管理页面 — Task 12.1
 * 5 tabs: 使用统计 / Dify 配置 / 降级配置 / 保留策略 / 用户配额
 */
import { useState } from 'react';
import UsageStats from './tabs/UsageStats';
import DifyConfigPanel from './tabs/DifyConfigPanel';
import DegradationConfigPanel from './tabs/DegradationConfigPanel';
import RetentionConfigPanel from './tabs/RetentionConfigPanel';
import UserQuotaTable from './tabs/UserQuotaTable';

type TabKey = 'stats' | 'dify' | 'degradation' | 'retention' | 'quota';

export default function ImageGenerationAdmin() {
  const [activeTab, setActiveTab] = useState<TabKey>('stats');

  const tabs: { key: TabKey; label: string; icon: string }[] = [
    { key: 'stats', label: '使用统计', icon: 'fa-chart-line' },
    { key: 'dify', label: 'Dify 配置', icon: 'fa-plug' },
    { key: 'degradation', label: '降级配置', icon: 'fa-shield-alt' },
    { key: 'retention', label: '保留策略', icon: 'fa-trash-alt' },
    { key: 'quota', label: '用户配额', icon: 'fa-users' },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">图像生成管理</h2>

      {/* Tab 切换 */}
      <div className="flex gap-1 mb-6 bg-slate-700 rounded-lg p-1 border border-slate-600 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 px-4 py-2 rounded-lg transition-colors text-sm font-medium whitespace-nowrap flex items-center justify-center gap-2 ${
              activeTab === tab.key
                ? 'bg-cyan-600 text-white'
                : 'text-slate-300 hover:bg-slate-600 hover:text-white'
            }`}
          >
            <i className={`fas ${tab.icon}`}></i>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      {activeTab === 'stats' && <UsageStats />}
      {activeTab === 'dify' && <DifyConfigPanel />}
      {activeTab === 'degradation' && <DegradationConfigPanel />}
      {activeTab === 'retention' && <RetentionConfigPanel />}
      {activeTab === 'quota' && <UserQuotaTable />}
    </div>
  );
}
/**
 * 大模型统计卡片
 * Task 1.5.4 — 统计维度改为按 provider_type / category 聚合
 */
import React, { useState, useEffect } from 'react';
import { llmProviderApi } from '../../services/llmProviderApi';
import { llmModelApi } from '../../services/llmModelApi';

interface LLMStatsProps {
  refreshInterval?: number;
}

const LLMStats: React.FC<LLMStatsProps> = ({ refreshInterval = 30000 }) => {
  const [providerCount, setProviderCount] = useState(0);
  const [modelCount, setModelCount] = useState(0);
  const [activeModelCount, setActiveModelCount] = useState(0);
  const [byProviderType, setByProviderType] = useState<Record<string, number>>({});
  const [byCategory, setByCategory] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  const loadStats = async () => {
    try {
      setError(null);
      const [providers, models] = await Promise.all([
        llmProviderApi.list(),
        llmModelApi.list(),
      ]);

      setProviderCount(providers.length);
      setModelCount(models.length);
      setActiveModelCount(models.filter((m) => m.is_active).length);

      // 按供应商类型聚合
      const byType: Record<string, number> = {};
      for (const p of providers) {
        byType[p.provider_type] = (byType[p.provider_type] || 0) + 1;
      }
      setByProviderType(byType);

      // 按分类聚合
      const byCat: Record<string, number> = {};
      for (const m of models) {
        byCat[m.category] = (byCat[m.category] || 0) + 1;
      }
      setByCategory(byCat);
    } catch {
      setError('加载统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading && providerCount === 0) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <p className="text-red-400">{error}</p>
        <button onClick={loadStats} className="mt-2 text-sm text-red-300 hover:text-red-100">
          重试
        </button>
      </div>
    );
  }

  const getProviderLabel = (type: string) => {
    const labels: Record<string, string> = {
      openai: 'OpenAI', anthropic: 'Anthropic', azure_openai: 'Azure OpenAI',
      baidu: '百度文心', aliyun: '阿里通义', doubao_seedream: '豆包 Seedream',
      qwen_image: '通义万相', zhipu: '智谱 AI', openrouter: 'OpenRouter',
      deepseek: 'DeepSeek', moonshot: '月之暗面', other: '其他',
    };
    return labels[type] || type;
  };

  const getCategoryLabel = (c: string) => (c === 'code' ? '编程' : '对话');

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* 供应商数 */}
      <div className="bg-slate-700 rounded-xl p-4 border border-slate-600">
        <div className="text-sm text-cyan-400 font-medium">供应商数</div>
        <div className="text-2xl font-bold text-white mt-1">{providerCount}</div>
      </div>

      {/* 模型总数 */}
      <div className="bg-slate-700 rounded-xl p-4 border border-slate-600">
        <div className="text-sm text-green-400 font-medium">模型总数</div>
        <div className="text-2xl font-bold text-white mt-1">{modelCount}</div>
      </div>

      {/* 活跃模型 */}
      <div className="bg-slate-700 rounded-xl p-4 border border-slate-600">
        <div className="text-sm text-purple-400 font-medium">活跃模型</div>
        <div className="text-2xl font-bold text-white mt-1">{activeModelCount}</div>
      </div>

      {/* 活跃率 */}
      <div className="bg-slate-700 rounded-xl p-4 border border-slate-600">
        <div className="text-sm text-orange-400 font-medium">活跃率</div>
        <div className="text-2xl font-bold text-white mt-1">
          {modelCount > 0 ? `${((activeModelCount / modelCount) * 100).toFixed(0)}%` : '0%'}
        </div>
      </div>

      {/* 按供应商类型统计 */}
      {Object.keys(byProviderType).length > 0 && (
        <div className="col-span-2 mt-2">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">按供应商类型</h4>
          <div className="space-y-2">
            {Object.entries(byProviderType).map(([type, count]) => (
              <div key={type} className="bg-slate-800 rounded-lg p-3 border border-slate-600">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-300">{getProviderLabel(type)}</span>
                  <span className="text-sm text-slate-400">{count} 个</span>
                </div>
                <div className="mt-1.5 w-full bg-slate-600 rounded-full h-1.5">
                  <div
                    className="bg-cyan-500 h-1.5 rounded-full"
                    style={{ width: `${Math.min(100, (count / Math.max(providerCount, 1)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 按分类统计 */}
      {Object.keys(byCategory).length > 0 && (
        <div className="col-span-2 mt-2">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">按分类</h4>
          <div className="space-y-2">
            {Object.entries(byCategory).map(([cat, count]) => (
              <div key={cat} className="bg-slate-800 rounded-lg p-3 border border-slate-600">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-300">{getCategoryLabel(cat)}</span>
                  <span className="text-sm text-slate-400">{count} 个</span>
                </div>
                <div className="mt-1.5 w-full bg-slate-600 rounded-full h-1.5">
                  <div
                    className="bg-purple-500 h-1.5 rounded-full"
                    style={{ width: `${Math.min(100, (count / Math.max(modelCount, 1)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LLMStats;

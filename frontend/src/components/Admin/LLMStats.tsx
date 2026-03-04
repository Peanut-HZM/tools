import React, { useState, useEffect } from 'react';
import { llmConfigApi } from '../../services/llmConfigApi';

interface LLMStatsData {
  total: number;
  active: number;
  by_provider: Record<string, number>;
}

interface LLMStatsProps {
  refreshInterval?: number;
}

const LLMStats: React.FC<LLMStatsProps> = ({ refreshInterval = 30000 }) => {
  const [stats, setStats] = useState<LLMStatsData | null>(null);
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
      const data = await llmConfigApi.getStats();
      setStats(data);
    } catch (err) {
      setError('加载统计数据失败');
      console.error('Failed to load LLM stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">{error}</p>
        <button 
          onClick={loadStats}
          className="mt-2 text-sm text-red-500 hover:text-red-700"
        >
          重试
        </button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* 总配置数 */}
      <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 border border-blue-200">
        <div className="text-sm text-blue-600 font-medium">总配置数</div>
        <div className="text-2xl font-bold text-blue-700 mt-1">
          {stats.total || 0}
        </div>
      </div>

      {/* 活跃配置 */}
      <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4 border border-green-200">
        <div className="text-sm text-green-600 font-medium">活跃配置</div>
        <div className="text-2xl font-bold text-green-700 mt-1">
          {stats.active || 0}
        </div>
      </div>

      {/* 活跃率 */}
      <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 border border-purple-200">
        <div className="text-sm text-purple-600 font-medium">活跃率</div>
        <div className="text-2xl font-bold text-purple-700 mt-1">
          {stats.total > 0 ? `${((stats.active / stats.total) * 100).toFixed(0)}%` : '0%'}
        </div>
      </div>

      {/* 供应商数 */}
      <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4 border border-orange-200">
        <div className="text-sm text-orange-600 font-medium">供应商数</div>
        <div className="text-2xl font-bold text-orange-700 mt-1">
          {Object.keys(stats.by_provider || {}).length}
        </div>
      </div>

      {/* 按供应商统计 */}
      {stats.by_provider && Object.keys(stats.by_provider).length > 0 && (
        <div className="col-span-2 md:col-span-4 mt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">按供应商统计</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {Object.entries(stats.by_provider).map(([provider, count]) => (
              <div 
                key={provider}
                className="bg-gray-50 rounded-lg p-3 border border-gray-200"
              >
                <div className="flex justify-between items-center">
                  <span className="font-medium text-gray-700">
                    {provider}
                  </span>
                  <span className="text-sm text-gray-500">
                    {count} 个
                  </span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ 
                      width: `${Math.min(100, (count / (stats.total || 1)) * 100)}%` 
                    }}
                  ></div>
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

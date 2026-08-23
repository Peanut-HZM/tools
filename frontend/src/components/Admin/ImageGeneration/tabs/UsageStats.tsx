/**
 * 使用统计 Tab — Task 12.1
 * 显示总调用数、成功率、模型分布、近 7 天调用量
 */
import { useEffect, useState } from 'react';
import { getStats, StatsResponse } from '../../../../api/adminImageGenerationApi';

export default function UsageStats() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    loadStats();
  }, [days]);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getStats(days);
      setStats(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载统计失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
        <p className="mt-4 text-slate-400">加载统计中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  if (!stats) return null;

  // 计算模型分布的最大值（用于柱状图）
  const maxModelCount = Math.max(...stats.model_distribution.map((m) => m.count), 1);
  const maxDailyCount = Math.max(...stats.daily_calls.map((d) => d.count), 1);

  return (
    <div className="space-y-6">
      {/* 时间窗口选择 */}
      <div className="flex items-center gap-3">
        <label className="text-slate-300 text-sm">统计窗口：</label>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-slate-700 border border-slate-600 text-white px-3 py-1.5 rounded text-sm focus:outline-none focus:border-cyan-500"
        >
          <option value={7}>最近 7 天</option>
          <option value={14}>最近 14 天</option>
          <option value={30}>最近 30 天</option>
          <option value={90}>最近 90 天</option>
        </select>
      </div>

      {/* 总览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="text-slate-400 text-xs mb-1">总调用数</div>
          <div className="text-2xl font-bold text-white">{stats.total_calls}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="text-slate-400 text-xs mb-1">成功调用</div>
          <div className="text-2xl font-bold text-green-400">{stats.success_calls}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="text-slate-400 text-xs mb-1">失败调用</div>
          <div className="text-2xl font-bold text-red-400">{stats.failed_calls}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="text-slate-400 text-xs mb-1">成功率</div>
          <div className="text-2xl font-bold text-cyan-400">
            {(stats.success_rate * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* 模型分布 */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">模型分布</h3>
        {stats.model_distribution.length === 0 ? (
          <p className="text-slate-400 text-sm">暂无数据</p>
        ) : (
          <div className="space-y-3">
            {stats.model_distribution.map((m) => (
              <div key={m.model}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-300">{m.model}</span>
                  <span className="text-slate-400">{m.count}</span>
                </div>
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all"
                    style={{ width: `${(m.count / maxModelCount) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 近 N 天调用量 */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">每日调用量</h3>
        {stats.daily_calls.length === 0 ? (
          <p className="text-slate-400 text-sm">暂无数据</p>
        ) : (
          <div className="space-y-2">
            {stats.daily_calls.map((d) => (
              <div key={d.date} className="flex items-center gap-3">
                <div className="text-slate-400 text-xs w-24 flex-shrink-0">{d.date}</div>
                <div className="flex-1 h-8 bg-slate-700 rounded relative overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all"
                    style={{ width: `${(d.count / maxDailyCount) * 100}%` }}
                  ></div>
                </div>
                <div className="text-white text-sm w-16 text-right">{d.count}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
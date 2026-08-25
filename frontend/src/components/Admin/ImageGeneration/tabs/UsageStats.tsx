/**
 * 使用统计 Tab — Task 12.1
 * 显示总调用数、成功率、模型分布、近 7 天调用量
 */
import { useEffect, useState } from 'react';
import { getStats, StatsResponse } from '../../../../api/adminImageGenerationApi';
import { useI18n } from '../../../../i18n';

export default function UsageStats() {
  const { t } = useI18n();
  const igT = t.imageGeneration.admin;
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
      setError(e instanceof Error ? e.message : t.imageGeneration.errors.defaultError);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent"></div>
        <p className="mt-4 text-ink-muted">{igT.loading}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg">
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
        <label className="text-ink-muted text-sm">{igT.window}</label>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-surface-2 border border-border text-ink-inverse px-3 py-1.5 rounded text-sm focus:outline-none focus:border-accent"
        >
          <option value={7}>{igT.window7}</option>
          <option value={14}>{igT.window14}</option>
          <option value={30}>{igT.window30}</option>
          <option value={90}>{igT.window90}</option>
        </select>
      </div>

      {/* 总览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-surface-1 border border-border rounded-lg p-4">
          <div className="text-ink-muted text-xs mb-1">{igT.totalCalls}</div>
          <div className="text-2xl font-bold text-ink-inverse">{stats.total_calls}</div>
        </div>
        <div className="bg-surface-1 border border-border rounded-lg p-4">
          <div className="text-ink-muted text-xs mb-1">{igT.successCalls}</div>
          <div className="text-2xl font-bold text-success">{stats.success_calls}</div>
        </div>
        <div className="bg-surface-1 border border-border rounded-lg p-4">
          <div className="text-ink-muted text-xs mb-1">{igT.failedCalls}</div>
          <div className="text-2xl font-bold text-danger">{stats.failed_calls}</div>
        </div>
        <div className="bg-surface-1 border border-border rounded-lg p-4">
          <div className="text-ink-muted text-xs mb-1">{igT.successRate}</div>
          <div className="text-2xl font-bold text-accent">
            {(stats.success_rate * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* 模型分布 */}
      <div className="bg-surface-1 border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-ink-inverse mb-4">{igT.modelDistribution}</h3>
        {stats.model_distribution.length === 0 ? (
          <p className="text-ink-muted text-sm">{igT.noData}</p>
        ) : (
          <div className="space-y-3">
            {stats.model_distribution.map((m) => (
              <div key={m.model}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-ink-muted">{m.model}</span>
                  <span className="text-ink-muted">{m.count}</span>
                </div>
                <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent to-accent-hover transition-all"
                    style={{ width: `${(m.count / maxModelCount) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 近 N 天调用量 */}
      <div className="bg-surface-1 border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-ink-inverse mb-4">{igT.dailyCalls}</h3>
        {stats.daily_calls.length === 0 ? (
          <p className="text-ink-muted text-sm">{igT.noData}</p>
        ) : (
          <div className="space-y-2">
            {stats.daily_calls.map((d) => (
              <div key={d.date} className="flex items-center gap-3">
                <div className="text-ink-muted text-xs w-24 flex-shrink-0">{d.date}</div>
                <div className="flex-1 h-8 bg-surface-2 rounded relative overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all"
                    style={{ width: `${(d.count / maxDailyCount) * 100}%` }}
                  ></div>
                </div>
                <div className="text-ink-inverse text-sm w-16 text-right">{d.count}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
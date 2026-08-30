/**
 * DashboardDialog — Agent 性能仪表盘弹窗
 *
 * P3-⑫ Agent 性能分析仪表盘
 * 统计卡片 + 14 天趋势（零依赖 div 条形图）+ 工具使用 Top 10。
 */
import React, { useState, useEffect, useCallback } from 'react';
import { agentApi } from '../../services/agentApi';

interface DashboardDialogProps {
  agentId: string;
  agentName: string;
  onClose: () => void;
}

interface DashboardData {
  basics: {
    conversation_count: number;
    message_count: number;
    trace_count: number;
    total_tokens: number;
    total_duration_ms: number;
    tool_usage: Array<{ tool_name: string; count: number }>;
  };
  status_breakdown: Record<string, number>;
  success_rate: number | null;
  avg_duration_ms: number | null;
  daily_trend: Array<{ date: string; trace_count: number; tokens: number }>;
}

function formatMs(ms: number | null): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-3 bg-surface-2 rounded-lg text-center">
      <div className="text-xl font-bold text-ink">{value}</div>
      <div className="text-xs text-ink-muted">{label}</div>
    </div>
  );
}

const DashboardDialog: React.FC<DashboardDialogProps> = ({ agentId, agentName, onClose }) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const result = await agentApi.getAgentDashboard(agentId);
      setData(result as unknown as DashboardData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load]);

  const maxTrend = data ? Math.max(1, ...data.daily_trend.map((d) => d.trace_count)) : 1;
  const topTools = data
    ? [...data.basics.tool_usage].sort((a, b) => b.count - a.count).slice(0, 10)
    : [];
  const maxToolCount = topTools.length > 0 ? topTools[0].count : 1;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-1 rounded-lg p-6 w-full max-w-2xl border border-border/50 shadow-xl max-h-[85vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 text-ink">性能仪表盘：{agentName}</h2>

        {loading && <div className="text-ink-muted text-sm">加载中...</div>}
        {error && <div className="text-danger text-sm mb-4">{error}</div>}

        {data && (
          <>
            {/* 统计卡片 */}
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
              <StatCard label="对话数" value={data.basics.conversation_count} />
              <StatCard label="消息数" value={data.basics.message_count} />
              <StatCard label="Trace 数" value={data.basics.trace_count} />
              <StatCard label="总 Token" value={data.basics.total_tokens} />
              <StatCard
                label="成功率"
                value={data.success_rate == null ? '-' : `${(data.success_rate * 100).toFixed(0)}%`}
              />
              <StatCard label="平均耗时" value={formatMs(data.avg_duration_ms)} />
            </div>

            {/* 14 天趋势（trace 数） */}
            <div className="mb-6">
              <div className="text-sm font-medium mb-2 text-ink">最近 14 天执行趋势</div>
              <div className="flex items-end gap-1 h-24" data-testid="daily-trend">
                {data.daily_trend.map((d) => (
                  <div
                    key={d.date}
                    title={`${d.date}：${d.trace_count} 次 / ${d.tokens} tokens`}
                    className="flex-1 bg-accent/70 hover:bg-accent rounded-t transition-colors"
                    style={{ height: `${Math.max(2, (d.trace_count / maxTrend) * 100)}%` }}
                  />
                ))}
              </div>
              <div className="flex justify-between text-xs text-ink-muted mt-1">
                <span>{data.daily_trend[0]?.date}</span>
                <span>{data.daily_trend[data.daily_trend.length - 1]?.date}</span>
              </div>
            </div>

            {/* 工具使用 Top 10 */}
            <div>
              <div className="text-sm font-medium mb-2 text-ink">工具使用 Top 10</div>
              {topTools.length === 0 ? (
                <div className="text-xs text-ink-muted">暂无工具调用记录</div>
              ) : (
                <ul className="space-y-1">
                  {topTools.map((t) => (
                    <li key={t.tool_name} className="flex items-center gap-2 text-sm">
                      <span className="w-32 truncate text-ink" title={t.tool_name}>
                        {t.tool_name}
                      </span>
                      <div className="flex-1 h-3 bg-surface-2 rounded overflow-hidden">
                        <div
                          className="h-full bg-accent-secondary/80 rounded"
                          style={{ width: `${(t.count / maxToolCount) * 100}%` }}
                        />
                      </div>
                      <span className="w-10 text-right text-ink-muted text-xs">{t.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        <div className="flex justify-end mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-ink-muted hover:text-ink"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardDialog;

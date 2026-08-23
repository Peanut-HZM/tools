/**
 * QuotaBadge — 显示今日/本月剩余配额
 */
import { useImageGenQuota } from '../../../../hooks/useImageGenQuota';

export default function QuotaBadge() {
  const { quota } = useImageGenQuota();

  if (!quota) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-700/50 text-slate-400 text-sm">
        <span className="animate-pulse">加载中...</span>
      </div>
    );
  }

  const dailyPct = quota.daily_limit > 0
    ? Math.round((quota.daily_remaining / quota.daily_limit) * 100)
    : 0;

  const barColor =
    dailyPct > 50 ? 'bg-emerald-500' :
    dailyPct > 20 ? 'bg-amber-500' :
    'bg-red-500';

  return (
    <div className="flex items-center gap-4 px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700/50">
      {/* 日配额 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">今日</span>
        <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${dailyPct}%` }}
          />
        </div>
        <span className="text-sm font-medium text-slate-200 tabular-nums">
          {quota.daily_remaining}/{quota.daily_limit}
        </span>
      </div>

      {/* 月配额 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">本月</span>
        <span className="text-sm font-medium text-slate-200 tabular-nums">
          {quota.monthly_remaining}/{quota.monthly_limit}
        </span>
      </div>
    </div>
  );
}

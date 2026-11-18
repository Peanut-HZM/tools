import { useMemo } from 'react';
import type { UsageSummaryDto } from '../../../api/subscriptionQuotaApi';
import {
  formatTokens,
  topN,
  usageDeltaPercent,
} from './usageRules';

interface UsagePanelProps {
  usage: UsageSummaryDto | null;
  loading: boolean;
  days: number;
  onDaysChange: (days: number) => void;
}

const DAY_OPTIONS = [7, 30, 90] as const;

/** 用量与成本面板（magpie 的 usage / cost 视图） */
export function UsagePanel({ usage, loading, days, onDaysChange }: UsagePanelProps) {
  const topProviders = useMemo(
    () => (usage ? topN(usage.byProvider, 6) : []),
    [usage]
  );
  const topModels = useMemo(() => (usage ? topN(usage.byModel, 6) : []), [usage]);
  const recentDays = useMemo(
    () => (usage ? usage.byDay.slice(-14) : []),
    [usage]
  );
  const maxDayCost = useMemo(
    () => Math.max(0.0001, ...recentDays.map((d) => d.costUsd)),
    [recentDays]
  );
  const delta = useMemo(() => {
    if (!usage || usage.byDay.length < 2) return null;
    const last = usage.byDay[usage.byDay.length - 1];
    const prev = usage.byDay[usage.byDay.length - 2];
    return usageDeltaPercent(prev.costUsd, last.costUsd);
  }, [usage]);

  if (loading && !usage) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-4 text-sm text-ink-muted">
        正在读取用量…
      </div>
    );
  }

  if (!usage || !usage.available) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-4">
        <div className="mb-1 text-sm font-medium text-ink">用量与成本</div>
        <p className="text-xs text-ink-muted">
          {usage?.message ?? '暂无用量数据'}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">用量与成本</h3>
          <p className="mt-0.5 text-xs text-ink-faint">
            数据来自本机 cc-switch · {usage.dateFrom} → {usage.dateTo}（{usage.days} 天）
          </p>
        </div>
        <div className="flex items-center gap-1">
          {DAY_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onDaysChange(option)}
              className={`rounded-md px-2 py-1 text-xs transition-colors ${
                days === option
                  ? 'bg-accent text-white'
                  : 'text-ink-muted hover:bg-surface-2'
              }`}
            >
              {option} 天
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="总成本" value={`$${usage.totals.costUsd.toFixed(2)}`} />
        <Stat label="请求数" value={usage.totals.requests.toLocaleString('zh-CN')} />
        <Stat label="总 Token" value={formatTokens(usage.totals.totalTokens)} />
        <Stat
          label="日均成本"
          value={`$${(usage.totals.costUsd / Math.max(1, usage.days)).toFixed(2)}`}
          hint={delta === null ? undefined : `较前一天 ${delta > 0 ? '+' : ''}${delta.toFixed(0)}%`}
        />
      </div>

      <div className="mb-3">
        <div className="mb-1 text-xs text-ink-muted">每日成本</div>
        <div className="flex h-16 items-end gap-0.5" role="img" aria-label="每日成本柱状图">
          {recentDays.map((day) => {
            const height = Math.max(2, (day.costUsd / maxDayCost) * 100);
            return (
              <div
                key={day.key}
                className="flex-1 rounded-t bg-accent/70 hover:bg-accent"
                style={{ height: `${height}%` }}
                title={`${day.key} · $${day.costUsd.toFixed(2)} · ${day.requests} 请求`}
              />
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <BreakdownList title="按供应商" buckets={topProviders} />
        <BreakdownList title="按模型" buckets={topModels} />
      </div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-surface-2 px-2.5 py-1.5">
      <div className="text-xs text-ink-faint">{label}</div>
      <div className="text-sm font-semibold tabular-nums text-ink">{value}</div>
      {hint && <div className="text-[10px] text-ink-faint">{hint}</div>}
    </div>
  );
}

function BreakdownList({
  title,
  buckets,
}: {
  title: string;
  buckets: { key: string; costUsd: number; requests: number; totalTokens: number }[];
}) {
  const max = Math.max(0.0001, ...buckets.map((b) => b.costUsd));
  return (
    <div>
      <div className="mb-1 text-xs text-ink-muted">{title}</div>
      <div className="flex flex-col gap-1">
        {buckets.map((bucket) => (
          <div key={bucket.key} className="flex items-center gap-2 text-xs">
            <span className="w-[92px] shrink-0 truncate text-ink-muted" title={bucket.key}>
              {bucket.key}
            </span>
            <span className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-3">
              <span
                className="absolute inset-y-0 left-0 rounded-full bg-accent/70"
                style={{ width: `${(bucket.costUsd / max) * 100}%` }}
              />
            </span>
            <span className="w-[58px] shrink-0 text-right tabular-nums text-ink">
              ${bucket.costUsd.toFixed(2)}
            </span>
            <span className="w-[64px] shrink-0 text-right tabular-nums text-ink-faint">
              {formatTokens(bucket.totalTokens)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

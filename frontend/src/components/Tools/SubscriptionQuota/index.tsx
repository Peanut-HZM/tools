import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Gauge, Loader2, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import * as quotaApi from '../../../api/subscriptionQuotaApi';
import type { SubscriptionQuotaDto } from '../../../api/subscriptionQuotaApi';
import {
  countdownStr,
  credentialStatusText,
  pickTiers,
  relativeTime,
  remainingPercent,
  sortTiers,
  tierLabel,
  toneForRemaining,
  toolLabel,
  type QuotaTier,
} from './quotaRules';

const TONE_STYLES = {
  normal: {
    text: 'text-accent-success',
    bar: 'bg-accent-success',
  },
  warning: {
    text: 'text-accent-warning',
    bar: 'bg-accent-warning',
  },
  danger: {
    text: 'text-accent-danger',
    bar: 'bg-accent-danger',
  },
} as const;

/** 每 30 秒刷新一次倒计时与相对时间 */
function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, [active]);
  return now;
}

interface TierRowProps {
  tier: QuotaTier;
  now: number;
  compact?: boolean;
}

/** 单个额度档位（条 + 剩余百分比 + 重置倒计时） */
function TierRow({ tier, now, compact = false }: TierRowProps) {
  const remaining = remainingPercent(tier.utilization);
  const tone = toneForRemaining(remaining);
  const styles = TONE_STYLES[tone];
  const countdown = countdownStr(tier.resetsAt, now);

  return (
    <div className="flex items-center gap-2 text-sm" title={`已用 ${tier.utilization.toFixed(1)}%`}>
      <span className={`shrink-0 text-ink-muted ${compact ? 'w-[68px]' : 'w-[76px]'} truncate`}>
        {tierLabel(tier.name)}
      </span>
      <span
        role="meter"
        aria-label={`${tierLabel(tier.name)} 剩余 ${Math.round(remaining)}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(remaining)}
        className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-3"
      >
        <span
          className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ${styles.bar}`}
          style={{ width: `${remaining}%` }}
        />
      </span>
      <span className={`shrink-0 tabular-nums ${styles.text}`}>{remaining.toFixed(0)}%</span>
      <span className="flex w-[58px] shrink-0 items-center gap-0.5 text-xs text-ink-faint">
        {countdown ? (
          <>
            <Clock className="h-3 w-3 shrink-0" aria-hidden />
            <span className="tabular-nums">{countdown}</span>
          </>
        ) : (
          <span aria-hidden>—</span>
        )}
      </span>
    </div>
  );
}

interface QuotaCardProps {
  quota: SubscriptionQuotaDto;
  now: number;
  refreshing: boolean;
  onRefresh: () => void;
}

/** 单个供应商的额度卡片 */
export function QuotaCard({ quota, now, refreshing, onRefresh }: QuotaCardProps) {
  const tiers = useMemo(() => sortTiers(quota.tiers ?? []), [quota.tiers]);
  const shownTiers = useMemo(() => pickTiers(tiers, 4), [tiers]);
  const updated = relativeTime(quota.queriedAt, now);

  const statusBadge = (() => {
    if (quota.success) {
      return (
        <Badge variant="tint-success" className="gap-1">
          <CheckCircle2 className="h-3 w-3" aria-hidden />
          {credentialStatusText(quota.credentialStatus)}
        </Badge>
      );
    }
    if (quota.credentialStatus === 'not_found') {
      return <Badge variant="outline">{credentialStatusText(quota.credentialStatus)}</Badge>;
    }
    return (
      <Badge variant="tint-warning" className="gap-1">
        <AlertCircle className="h-3 w-3" aria-hidden />
        {credentialStatusText(quota.credentialStatus)}
      </Badge>
    );
  })();

  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 shrink-0 text-ink-muted" aria-hidden />
            <h3 className="truncate text-sm font-semibold text-ink">{toolLabel(quota.tool)}</h3>
            {quota.planName && (
              <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-muted">
                {quota.planName}
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-ink-faint">
            {statusBadge}
            {updated && <span>{updated}更新</span>}
          </div>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          aria-label={`刷新 ${toolLabel(quota.tool)} 额度`}
          className="shrink-0 rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden />
        </button>
      </div>

      {quota.success ? (
        shownTiers.length > 0 ? (
          <div className="flex flex-col gap-2">
            {shownTiers.map((tier) => (
              <TierRow key={tier.name} tier={tier} now={now} />
            ))}
            {tiers.length > shownTiers.length && (
              <p className="text-xs text-ink-faint">另有 {tiers.length - shownTiers.length} 个档位未显示</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-muted">该套餐暂未返回额度档位</p>
        )
      ) : (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-accent-danger">
            {quota.credentialStatus === 'not_found' ? '未检测到本地登录凭据' : '额度查询失败'}
          </p>
          {(quota.error || quota.credentialMessage) && (
            <p className="break-words text-xs text-ink-faint">
              {quota.error || quota.credentialMessage}
            </p>
          )}
          {quota.credentialStatus === 'not_found' && (
            <p className="text-xs text-ink-faint">
              请先在本机用对应命令行工具登录，再回到这里刷新。
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

/** 订阅套餐额度工具主界面 */
export default function SubscriptionQuotaTool() {
  const [quotas, setQuotas] = useState<SubscriptionQuotaDto[]>([]);
  const [queriedAt, setQueriedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const now = useNow(quotas.length > 0 || Boolean(queriedAt));

  const load = useCallback(async (forceRefresh: boolean) => {
    if (forceRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await quotaApi.queryQuotas({ forceRefresh });
      if (!mountedRef.current) return;
      setQuotas(data.quotas ?? []);
      setQueriedAt(data.queriedAt ?? Date.now());
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err.message : '查询失败');
    } finally {
      if (!mountedRef.current) return;
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void load(false);
    return () => {
      mountedRef.current = false;
    };
  }, [load]);

  const handleRefreshAll = useCallback(() => {
    void load(true);
  }, [load]);

  const handleRefreshOne = useCallback(
    async (tool: string) => {
      setRefreshing(true);
      try {
        const data = await quotaApi.queryQuotas({ tools: [tool], forceRefresh: true });
        if (!mountedRef.current) return;
        setQuotas((prev) => {
          const next = prev.map((item) =>
            item.tool === tool ? data.quotas[0] ?? item : item
          );
          return next;
        });
        setQueriedAt(data.queriedAt ?? Date.now());
      } catch (err) {
        if (!mountedRef.current) return;
        setError(err instanceof Error ? err.message : '刷新失败');
      } finally {
        if (mountedRef.current) setRefreshing(false);
      }
    },
    []
  );

  const successCount = quotas.filter((q) => q.success).length;

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">订阅套餐额度</h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            读取本机各 CLI 的官方登录凭据查询订阅剩余额度；只读凭据，不做任何修改。
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefreshAll}
          disabled={refreshing || loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink transition-colors hover:bg-surface-2 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden />
          {refreshing ? '刷新中…' : '全部刷新'}
        </button>
      </div>

      {queriedAt && (
        <p className="text-xs text-ink-faint">
          共 {quotas.length} 家供应商，成功 {successCount} 家 · 更新于 {relativeTime(queriedAt, now)}
        </p>
      )}

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-ink-muted">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" aria-hidden />
          正在查询订阅额度…
        </div>
      ) : quotas.length === 0 ? (
        <p className="py-16 text-center text-sm text-ink-muted">暂无可用供应商</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {quotas.map((quota) => (
            <QuotaCard
              key={quota.tool}
              quota={quota}
              now={now}
              refreshing={refreshing}
              onRefresh={() => handleRefreshOne(quota.tool)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * QuotaBadge — 显示今日/本月剩余配额
 */
import { useImageGenQuota } from '../../../../hooks/useImageGenQuota';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useI18n } from '../../../../i18n';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

export default function QuotaBadge() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const { quota } = useImageGenQuota();
  const quotaLoadError = useImageGenStore((s) => s.quotaLoadError);

  if (!quota && !quotaLoadError) {
    return (
      <Badge variant="secondary">
        <span className="animate-pulse">{igT.admin.loading}</span>
      </Badge>
    );
  }

  if (!quota || quotaLoadError) {
    return null;
  }

  const dailyPct = quota.daily_limit > 0
    ? Math.round((quota.daily_remaining / quota.daily_limit) * 100)
    : 0;

  const barColor =
    dailyPct > 50 ? 'bg-emerald-500' :
    dailyPct > 20 ? 'bg-amber-500' :
    'bg-red-500';

  return (
    <Card className="flex items-center gap-4 px-4 py-2 border-border/50">
      {/* 日配额 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-ink-muted">{igT.quota.daily}</span>
        <div className="w-20 h-1.5 bg-surface-2 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${dailyPct}%` }}
          />
        </div>
        <span className="text-sm font-medium text-ink tabular-nums">
          {quota.daily_remaining}/{quota.daily_limit}
        </span>
      </div>

      {/* 月配额 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-ink-muted">{igT.quota.monthly}</span>
        <span className="text-sm font-medium text-ink tabular-nums">
          {quota.monthly_remaining}/{quota.monthly_limit}
        </span>
      </div>
    </Card>
  );
}
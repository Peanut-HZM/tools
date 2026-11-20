import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, ArrowRightLeft, CheckCircle2, Clock, Download, Gauge, LayoutDashboard,
  Package, Pencil, Plus, RefreshCw, Server, Settings2, Trash2, X,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import * as quotaApi from '../../../api/subscriptionQuotaApi';
import type {
  ProviderAggregateDto,
  ProviderSpecDto,
  QuotaAccountDto,
  QuotaResultDto,
  QuotaTierDto,
  SubscriptionStatusDto,
} from '../../../api/subscriptionQuotaApi';
import {
  countdownStr, credentialStatusText, formatAmount, isBalanceTier, kindLabel,
  needsHint, pickTiers, providerInitials, relativeTime, remainingPercent,
  sortTiers, tierLabel, toneForBalance, toneForRemaining,
} from './quotaRules';
import { GatewayPanel } from './GatewayPanel';
import { AgentSwitchPanel } from './AgentSwitchPanel';

const TONE_STYLES = {
  normal: { text: 'text-accent-success', bar: 'bg-accent-success' },
  warning: { text: 'text-accent-warning', bar: 'bg-accent-warning' },
  danger: { text: 'text-accent-danger', bar: 'bg-accent-danger' },
} as const;

type TabKey = 'overview' | 'providers' | 'agents' | 'gateway';

const TABS: { key: TabKey; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'overview', label: '概览', icon: LayoutDashboard },
  { key: 'providers', label: '供应商', icon: Package },
  { key: 'agents', label: 'Agent 切换', icon: ArrowRightLeft },
  { key: 'gateway', label: '本地网关', icon: Server },
];

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
  tier: QuotaTierDto;
  now: number;
}

/** 单个额度档位（窗口：条 + 剩余%；余额：金额） */
function TierRow({ tier, now }: TierRowProps) {
  if (isBalanceTier(tier)) {
    const amount = tier.balanceAmount ?? 0;
    const tone = toneForBalance(amount);
    return (
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="shrink-0 text-ink-muted">{tierLabel(tier.name)}</span>
        <span className={`tabular-nums font-medium ${TONE_STYLES[tone].text}`}>
          {formatAmount(amount, tier.balanceUnit)}
        </span>
      </div>
    );
  }

  const remaining = remainingPercent(tier.utilization);
  const tone = toneForRemaining(remaining);
  const styles = TONE_STYLES[tone];
  const countdown = countdownStr(tier.resetsAt, now);

  return (
    <div
      className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm sm:flex-nowrap"
      title={`已用 ${tier.utilization.toFixed(1)}%`}
    >
      <span className="min-w-0 flex-1 truncate text-ink-muted sm:w-[76px] sm:flex-none">
        {tierLabel(tier.name)}
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
      <span
        role="meter"
        aria-label={`${tierLabel(tier.name)} 剩余 ${Math.round(remaining)}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(remaining)}
        className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-3 sm:order-2 sm:h-1.5 sm:w-auto sm:min-w-0 sm:flex-1"
      >
        <span
          className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ${styles.bar}`}
          style={{ width: `${remaining}%` }}
        />
      </span>
    </div>
  );
}

interface QuotaCardProps {
  quota: QuotaResultDto;
  now: number;
  refreshing: boolean;
  onRefresh: () => void;
  onRemove?: () => void;
  onAdjust?: () => void;
  /** 编辑该账号的订阅配置（Key / 显示名 / 站点 / 备注 / 启用状态） */
  onEdit?: () => void;
}

/** 单个账号 / 订阅的额度卡片 */
export function QuotaCard({
  quota,
  now,
  refreshing,
  onRefresh,
  onRemove,
  onAdjust,
  onEdit,
}: QuotaCardProps) {
  const tiers = useMemo(() => sortTiers(quota.tiers ?? []), [quota.tiers]);
  const shownTiers = useMemo(() => pickTiers(tiers, 4), [tiers]);
  const updated = relativeTime(quota.queriedAt, now);

  const statusBadge = quota.success ? (
    <Badge variant="tint-success" className="gap-1">
      <CheckCircle2 className="h-3 w-3" aria-hidden />
      {credentialStatusText(quota.credentialStatus)}
    </Badge>
  ) : quota.credentialStatus === 'not_found' ? (
    <Badge variant="outline">{credentialStatusText(quota.credentialStatus)}</Badge>
  ) : (
    <Badge variant="tint-warning" className="gap-1">
      <AlertCircle className="h-3 w-3" aria-hidden />
      {credentialStatusText(quota.credentialStatus)}
    </Badge>
  );

  return (
    <Card className="flex flex-col gap-3 p-3 sm:p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              aria-hidden
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-2 text-[10px] font-semibold text-ink-muted"
            >
              {providerInitials(quota.label)}
            </span>
            <h3 className="min-w-0 flex-1 truncate text-sm font-semibold text-ink">{quota.label}</h3>
            <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-faint">
              {kindLabel(quota.kind)}
            </span>
            {quota.planName && (
              <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-muted">
                {quota.planName}
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-faint">
            {statusBadge}
            {quota.maskedKey && (
              <span className="min-w-0 break-all font-mono">{quota.maskedKey}</span>
            )}
            {quota.isLocal && (
              <span className="rounded-full bg-surface-2 px-2 py-0.5">本机登录</span>
            )}
            {updated && <span>{updated}更新</span>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          {onEdit && (
            <button
              type="button"
              onClick={onEdit}
              aria-label={`编辑 ${quota.label} 的订阅配置`}
              title="编辑订阅配置（Key / 显示名 / 站点 / 备注）"
              className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <Pencil className="h-4 w-4" aria-hidden />
            </button>
          )}
          {onAdjust && (
            <button
              type="button"
              onClick={onAdjust}
              aria-label={`调整 ${quota.label} 额度`}
              className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <Settings2 className="h-4 w-4" aria-hidden />
            </button>
          )}
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            aria-label={`刷新 ${quota.label} 额度`}
            className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden />
          </button>
          {onRemove && quota.accountId && !quota.isLocal && (
            <button
              type="button"
              onClick={onRemove}
              aria-label={`删除 ${quota.label}`}
              className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-danger/10 hover:text-accent-danger"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
      </div>

      {quota.success ? (
        shownTiers.length > 0 ? (
          <div className="flex flex-col gap-2">
            {shownTiers.map((tier) => (
              <TierRow key={tier.name} tier={tier} now={now} />
            ))}
            {tiers.length > shownTiers.length && (
              <p className="text-xs text-ink-faint">
                另有 {tiers.length - shownTiers.length} 个档位未显示
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-muted">该套餐暂未返回额度档位</p>
        )
      ) : (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-accent-danger">
            {quota.credentialStatus === 'not_found' ? '未检测到可用凭据' : '额度查询失败'}
          </p>
          {(quota.error || quota.credentialMessage) && (
            <p className="break-words text-xs text-ink-faint">
              {quota.error || quota.credentialMessage}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

interface AddAccountDialogProps {
  providers: ProviderSpecDto[];
  initialProviderId?: string;
  onClose: () => void;
  onSaved: () => void;
}

/** 添加供应商账号对话框 */
function AddAccountDialog({ providers, initialProviderId, onClose, onSaved }: AddAccountDialogProps) {
  const addable = useMemo(() => providers.filter((p) => p.addable), [providers]);
  const [providerId, setProviderId] = useState(initialProviderId ?? addable[0]?.id ?? '');
  const spec = useMemo(
    () => addable.find((p) => p.id === providerId) ?? null,
    [addable, providerId]
  );
  const [label, setLabel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [region, setRegion] = useState('cn');
  const [baseUrl, setBaseUrl] = useState('');
  const [extraValues, setExtraValues] = useState<Record<string, string>>({});
  const [manualTotal, setManualTotal] = useState('');
  const [manualUsed, setManualUsed] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLabel(spec?.name ?? '');
    setExtraValues({});
    setApiKey('');
    setBaseUrl('');
    setRegion(spec?.regions?.includes('cn') ? 'cn' : 'intl');
    setManualTotal('');
    setManualUsed('');
  }, [spec]);

  const isManual = spec?.kind === 'manual';

  const handleSave = useCallback(async () => {
    if (!spec) return;
    setSaving(true);
    setError(null);
    try {
      const extra: Record<string, unknown> = { ...extraValues };
      if (spec.regions.length > 0) extra.region = region;
      if ((spec.needsBaseUrl || isManual) && baseUrl.trim()) extra.base_url = baseUrl.trim();
      if (spec.needs.includes('control_key')) {
        extra.control_key = apiKey;
      } else if (spec.needs.includes('access_key')) {
        // AK/SK 都从 extraValues 来
      } else if (!isManual) {
        extra.api_key = apiKey;
      }
      await quotaApi.addAccount({
        providerId: spec.id,
        label: label.trim() || spec.name,
        apiKey: apiKey || undefined,
        extra,
        manualTotal: isManual && manualTotal ? Number(manualTotal) : undefined,
        manualUsed: isManual && manualUsed ? Number(manualUsed) : undefined,
        quotaUnit: isManual ? (extraValues.quota_unit || 'credits') : undefined,
        windowType: isManual ? (extraValues.window_type || 'none') : undefined,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }, [spec, label, apiKey, region, baseUrl, extraValues, manualTotal, manualUsed, isManual, onSaved, onClose]);

  const keyField = spec?.needs.find((n) => n === 'api_key' || n === 'control_key') ?? 'api_key';
  const otherFields = (spec?.needs.filter((n) => n !== 'api_key' && n !== 'control_key') ?? []).filter(
    (f) => !(isManual && (f === 'quota_unit' || f === 'window_type'))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="添加供应商"
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-xl border border-border bg-surface-1 p-4 shadow-xl sm:max-h-[88vh] sm:rounded-xl sm:p-5"
      >
        <div className="mb-4 flex items-start justify-between">
          <h2 className="text-base font-semibold text-ink">添加供应商</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="rounded-md p-1 text-ink-muted hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs text-ink-muted">
            供应商
            <select
              value={providerId}
              onChange={(e) => setProviderId(e.target.value)}
              className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
            >
              {addable.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}（{kindLabel(p.kind)}）
                </option>
              ))}
            </select>
          </label>

          {spec && (
            <p className="rounded-lg bg-surface-2 px-3 py-2 text-xs text-ink-muted">
              {spec.hint}
              <br />
              {needsHint(spec.needs, spec.extraFields)}
            </p>
          )}

          <label className="flex flex-col gap-1 text-xs text-ink-muted">
            显示名称
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={spec?.name}
              className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
            />
          </label>

          {spec?.regions && spec.regions.length > 1 && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              站点
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              >
                {spec.regions.map((r) => (
                  <option key={r} value={r}>
                    {r === 'cn' ? '国内站' : '国际站'}
                  </option>
                ))}
              </select>
            </label>
          )}

          {!isManual && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              {keyField === 'control_key' ? 'Control Key' : 'API Key'}
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                autoComplete="off"
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 font-mono text-sm text-ink"
              />
            </label>
          )}

          {isManual && (
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-1 text-xs text-ink-muted">
                总额度
                <input
                  type="number"
                  value={manualTotal}
                  onChange={(e) => setManualTotal(e.target.value)}
                  placeholder="100"
                  className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-ink-muted">
                已用
                <input
                  type="number"
                  value={manualUsed}
                  onChange={(e) => setManualUsed(e.target.value)}
                  placeholder="0"
                  className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
                />
              </label>
            </div>
          )}

          {spec?.needsBaseUrl && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              用量地址（base_url）
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://..."
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              />
            </label>
          )}

          {otherFields.map((field) => (
            <label key={field} className="flex flex-col gap-1 text-xs text-ink-muted">
              {spec?.extraFields[field] ?? field}
              <input
                value={extraValues[field] ?? ''}
                onChange={(e) =>
                  setExtraValues((prev) => ({ ...prev, [field]: e.target.value }))
                }
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 font-mono text-sm text-ink"
              />
            </label>
          ))}

          {error && <p className="text-xs text-accent-danger">{error}</p>}

          <div className="mt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink hover:bg-surface-2"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !spec}
              className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface QuotaAdjustDialogProps {
  account: QuotaAccountDto;
  onClose: () => void;
  onSaved: () => void;
}

/** 手动额度调整对话框（从 agent-hub 合并：额度支持手动增加） */
function QuotaAdjustDialog({ account, onClose, onSaved }: QuotaAdjustDialogProps) {
  const [total, setTotal] = useState(String(account.manualTotal || ''));
  const [used, setUsed] = useState(String(account.manualUsed || ''));
  const [add, setAdd] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await quotaApi.adjustQuota(account.id, {
        total: total ? Number(total) : undefined,
        used: used ? Number(used) : undefined,
        add: add ? Number(add) : undefined,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }, [account.id, total, used, add, onSaved, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="调整额度"
        className="max-h-[92vh] w-full max-w-md overflow-y-auto rounded-t-xl border border-border bg-surface-1 p-4 shadow-xl sm:rounded-xl sm:p-5"
      >
        <div className="mb-3 flex items-start justify-between">
          <h2 className="text-base font-semibold text-ink">调整额度 · {account.label}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="rounded-md p-1 text-ink-muted hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              总额度
              <input
                type="number"
                value={total}
                onChange={(e) => setTotal(e.target.value)}
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              已用
              <input
                type="number"
                value={used}
                onChange={(e) => setUsed(e.target.value)}
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1 text-xs text-ink-muted">
            在现有总额度上增加（套餐续期时用）
            <input
              type="number"
              value={add}
              onChange={(e) => setAdd(e.target.value)}
              placeholder="例如 500"
              className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
            />
          </label>

          <p className="rounded-lg bg-surface-2 px-3 py-2 text-xs text-ink-faint">
            填「总额度」会直接覆盖；只填「增加」则在当前总额上累加。单位与窗口沿用该订阅的原有设置。
          </p>

          {error && <p className="text-xs text-accent-danger">{error}</p>}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink hover:bg-surface-2"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface EditAccountDialogProps {
  account: QuotaAccountDto;
  spec: ProviderSpecDto | null;
  onClose: () => void;
  onSaved: () => void;
}

/** 编辑已有账号（对齐原 agent-hub 的「编辑供应商」能力） */
function EditAccountDialog({ account, spec, onClose, onSaved }: EditAccountDialogProps) {
  const [label, setLabel] = useState(account.label);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(String(account.extra?.base_url ?? ''));
  const [controlKey, setControlKey] = useState('');
  const [region, setRegion] = useState(String(account.extra?.region ?? 'cn'));
  const [extraValues, setExtraValues] = useState<Record<string, string>>(() => {
    // 供应商专属字段（如 zhipu_team 的 organization_id / project_id）从已有 extra 回填
    const init: Record<string, string> = {};
    for (const field of spec?.extraFields ? Object.keys(spec.extraFields) : []) {
      const value = account.extra?.[field];
      if (value !== undefined && value !== null) init[field] = String(value);
    }
    return init;
  });
  const [notes, setNotes] = useState(account.notes ?? '');
  const [enabled, setEnabled] = useState(account.enabled);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsControlKey = spec?.needs.includes('control_key') ?? false;
  const needsBaseUrl = Boolean(spec?.needsBaseUrl);
  const hasRegions = (spec?.regions?.length ?? 0) > 1;
  // 供应商专属字段（排除已单独渲染的 base_url / region / control_key）
  const extraFields = (spec?.extraFields ? Object.keys(spec.extraFields) : []).filter(
    (f) => !['base_url', 'region', 'control_key'].includes(f)
  );
  // 手动额度账号不查网络，没有任何 Key 需要填
  const showKeyField = !account.isManual && (spec ? spec.needs.length > 0 : true);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      // 保留原有 extra 的其他字段，只覆盖本次可编辑项
      const extra: Record<string, unknown> = { ...(account.extra ?? {}) };
      if (hasRegions) extra.region = region;
      for (const [field, value] of Object.entries(extraValues)) {
        const trimmed = value.trim();
        if (trimmed) extra[field] = trimmed;
        else delete extra[field];
      }
      if (needsBaseUrl) {
        if (baseUrl.trim()) extra.base_url = baseUrl.trim();
        else delete extra.base_url;
      }
      // 留空 = 不修改，避免把已有 Key 清掉
      const key = apiKey.trim();
      if (key) {
        if (needsControlKey) extra.control_key = key;
        // 同步写 extra.api_key：查询实现读的是 `extra.api_key or api_key`，
        // 只写 api_key 字段会出现「改了 Key 但查询仍用旧 Key」的问题。
        else extra.api_key = key;
      }
      if (controlKey.trim()) extra.control_key = controlKey.trim();

      await quotaApi.updateAccount(account.id, {
        label: label.trim() || account.label,
        apiKey: key || undefined,
        extra,
        enabled,
        notes,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }, [
    account,
    apiKey,
    baseUrl,
    controlKey,
    enabled,
    extraValues,
    hasRegions,
    label,
    needsBaseUrl,
    needsControlKey,
    notes,
    onSaved,
    onClose,
    region,
  ]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="编辑供应商账号"
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-xl border border-border bg-surface-1 p-4 shadow-xl sm:rounded-xl sm:p-5"
      >
        <div className="mb-4 flex items-start justify-between">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-ink">编辑 · {account.label}</h2>
            <p className="mt-0.5 text-xs text-ink-faint">
              {spec?.name ?? account.providerId} · Key 留空表示保持不变
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="shrink-0 rounded-md p-1 text-ink-muted hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs text-ink-muted">
            显示名称
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
            />
          </label>

          {showKeyField && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              {needsControlKey ? 'Control Key' : 'API Key'}
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={
                  account.maskedKey ? `当前 ${account.maskedKey}（留空不改）` : '未配置'
                }
                autoComplete="off"
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 font-mono text-sm text-ink"
              />
            </label>
          )}

          {hasRegions && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              站点
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              >
                {spec?.regions.map((r) => (
                  <option key={r} value={r}>
                    {r === 'cn' ? '国内站' : '国际站'}
                  </option>
                ))}
              </select>
            </label>
          )}

          {needsBaseUrl && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              站点地址（base_url）
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://..."
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              />
            </label>
          )}

          {extraFields.map((field) => (
            <label key={field} className="flex flex-col gap-1 text-xs text-ink-muted">
              {spec?.extraFields[field] ?? field}
              <input
                value={extraValues[field] ?? ''}
                onChange={(e) =>
                  setExtraValues((prev) => ({ ...prev, [field]: e.target.value }))
                }
                placeholder="留空表示不修改"
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 font-mono text-sm text-ink"
              />
            </label>
          ))}

          {needsControlKey && (
            <label className="flex flex-col gap-1 text-xs text-ink-muted">
              用量查询控制面 Key（可选）
              <input
                type="password"
                value={controlKey}
                onChange={(e) => setControlKey(e.target.value)}
                placeholder="留空不改"
                autoComplete="off"
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 font-mono text-sm text-ink"
              />
            </label>
          )}

          <label className="flex flex-col gap-1 text-xs text-ink-muted">
            备注
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="例如：工作号 / 备用"
              className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
            />
          </label>

          <label className="flex items-center gap-2 text-xs text-ink-muted">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            启用（停用后不在额度列表里查询与展示）
          </label>

          {error && <p className="text-xs text-accent-danger">{error}</p>}

          <div className="mt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink hover:bg-surface-2"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Agent 订阅中心（合并 订阅套餐额度 + Agent 订阅中心） */
export default function SubscriptionQuotaTool() {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [providers, setProviders] = useState<ProviderSpecDto[]>([]);
  const [accounts, setAccounts] = useState<QuotaAccountDto[]>([]);
  const [results, setResults] = useState<QuotaResultDto[]>([]);
  const [aggregates, setAggregates] = useState<ProviderAggregateDto[]>([]);
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatusDto[]>([]);
  const [queriedAt, setQueriedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [adjusting, setAdjusting] = useState<QuotaAccountDto | null>(null);
  const [editingAccount, setEditingAccount] = useState<QuotaAccountDto | null>(null);
  const mountedRef = useRef(true);

  const now = useNow(results.length > 0 || Boolean(queriedAt));

  const loadAll = useCallback(async (forceRefresh: boolean) => {
    if (forceRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [providerData, accountData, subData] = await Promise.all([
        quotaApi.getProviders(),
        quotaApi.getAccounts(),
        quotaApi.getSubscriptions(),
      ]);
      if (!mountedRef.current) return;
      setProviders(providerData.providers);
      setAccounts(accountData.accounts);
      setSubscriptionStatus(subData.subscriptions);

      // 无论有没有用户账号都查一次：本机 CLI 凭据会自动出现
      const quotaData = await quotaApi.queryQuotas({ forceRefresh });
      if (!mountedRef.current) return;
      setResults([...quotaData.accounts, ...quotaData.subscriptions]);
      setAggregates(quotaData.aggregates ?? []);
      setQueriedAt(quotaData.queriedAt);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      if (!mountedRef.current) return;
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void loadAll(false);
    return () => {
      mountedRef.current = false;
    };
  }, [loadAll]);

  const handleRefreshOne = useCallback(async (quota: QuotaResultDto) => {
    if (!quota.accountId) {
      void loadAll(true);
      return;
    }
    setRefreshing(true);
    try {
      const data = await quotaApi.queryQuotas({
        accountIds: [quota.accountId],
        includeSubscriptions: false,
        forceRefresh: true,
      });
      if (!mountedRef.current) return;
      const updated = data.accounts[0];
      if (updated) {
        setResults((prev) =>
          prev.map((item) => (item.accountId === quota.accountId ? updated : item))
        );
        setQueriedAt(data.queriedAt);
      }
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err.message : '刷新失败');
    } finally {
      if (mountedRef.current) setRefreshing(false);
    }
  }, [loadAll]);

  const handleRemove = useCallback(async (accountId: string) => {
    try {
      await quotaApi.deleteAccount(accountId);
      setAccounts((prev) => prev.filter((a) => a.id !== accountId));
      setResults((prev) => prev.filter((r) => r.accountId !== accountId));
      const providerData = await quotaApi.getProviders();
      if (mountedRef.current) setProviders(providerData.providers);
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  }, []);

  const handleToggleEnabled = useCallback(async (account: QuotaAccountDto) => {
    try {
      const { account: updated } = await quotaApi.updateAccount(account.id, {
        enabled: !account.enabled,
      });
      if (!mountedRef.current) return;
      setAccounts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      // 停用后需重新查询，让该账号从额度列表里消失
      await loadAll(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '切换启用状态失败');
    }
  }, [loadAll]);

  const handleCcSwitchImport = useCallback(async () => {
    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await quotaApi.importFromCcSwitch(false);
      if (!mountedRef.current) return;
      // 默认不覆盖已有数据：已存在的供应商会被跳过，这里要把跳过数一并告诉用户，
      // 否则「导入 0 个」看起来像失败，实际是刻意保护用户已有数据。
      if (result.imported === 0 && result.skipped === 0) {
        setImportResult('cc-switch 里没有可导入的供应商凭据');
      } else if (result.imported === 0) {
        setImportResult(
          `已存在的 ${result.skipped} 个供应商已跳过（不会覆盖你已有的 Key 与设置）`
        );
      } else {
        const control = result.items.filter((i) => i.fromControlKey).map((i) => i.providerId);
        setImportResult(
          `已从 cc-switch 同步 ${result.imported} 个供应商（新建 ${result.created} / 更新 ${result.updated}）` +
            (result.skipped > 0 ? `，已存在跳过 ${result.skipped} 个` : '') +
            (control.length > 0 ? `，其中控制面 Key：${control.join('、')}` : '')
        );
      }
      await loadAll(true);
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : '从 cc-switch 同步失败');
      }
    } finally {
      if (mountedRef.current) setImporting(false);
    }
  }, [loadAll]);

  const handleMagpieImport = useCallback(async () => {
    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await quotaApi.importFromMagpie(false, true);
      if (!mountedRef.current) return;
      if (result.message) {
        setImportResult(result.message);
      } else if (result.imported === 0 && result.skipped === 0) {
        setImportResult('magpie 里没有可同步的供应商或账号');
      } else {
        const parts = [
          `已从 magpie 同步 ${result.imported} 项（新建 ${result.created} / 更新 ${result.updated}）`,
        ];
        if (result.skipped > 0) parts.push(`已存在跳过 ${result.skipped} 项`);
        if (result.skippedItems.length > 0) {
          const reasons = Array.from(
            new Set(result.skippedItems.map((i) => i.reason))
          ).slice(0, 3);
          parts.push(`另有 ${result.skippedItems.length} 项无法映射：${reasons.join('；')}`);
        }
        setImportResult(parts.join('；'));
      }
      await loadAll(true);
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : '从 magpie 同步失败');
      }
    } finally {
      if (mountedRef.current) setImporting(false);
    }
  }, [loadAll]);

  const successCount = results.filter((r) => r.success).length;
  const hasAnything =
    accounts.length > 0 ||
    subscriptionStatus.some((s) => s.hasCredential) ||
    results.some((r) => r.isLocal);
  const failoverGroups = aggregates.filter((a) => a.isFailoverReady);

  const manualAccount = useMemo(() => {
    if (!adjusting) return null;
    return accounts.find((a) => a.id === adjusting.id) ?? adjusting;
  }, [adjusting, accounts]);

  const renderQuotaGrid = () =>
    results.length === 0 ? (
      <p className="py-16 text-center text-sm text-ink-muted">暂无已配置的供应商</p>
    ) : (
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {results.map((quota) => {
          const account = accounts.find((a) => a.id === quota.accountId);
          return (
            <QuotaCard
              key={`${quota.providerId}:${quota.accountId ?? 'subscription'}`}
              quota={quota}
              now={now}
              refreshing={refreshing}
              onRefresh={() => void handleRefreshOne(quota)}
              onRemove={
                quota.accountId ? () => void handleRemove(quota.accountId!) : undefined
              }
              onAdjust={
                account?.isManual ? () => setAdjusting(account) : undefined
              }
              onEdit={account ? () => setEditingAccount(account) : undefined}
            />
          );
        })}
      </div>
    );

  return (
    // 外层固定一屏高度、不滚动：Tab 导航必须始终可见。
    // 之前把 overflow-y-auto 放在这个外层容器上，滚动时整页（含 Tab 栏）一起滚出视口，
    // 且因容器自身高度随内容增长、页面滚动条又属于外层工作区，用户再也滚不回来。
    <div className="flex h-full min-h-0 flex-col">
      {/* Tab 导航：常驻顶部，不随内容滚动 */}
      <div className="shrink-0 border-b border-border bg-canvas px-3 pt-3 pb-2 sm:px-4 sm:pt-4">
        {/* 移动端横向可滚动 */}
        <div className="flex gap-1 overflow-x-auto pb-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                aria-current={active ? 'page' : undefined}
                className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? 'bg-accent text-white'
                    : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 内容区：独立滚动，Tab 栏不受影响 */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3 sm:gap-4 sm:p-4">
        {error && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
            {error}
          </div>
        )}

        {importResult && (
        <div className="flex items-start justify-between gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-accent-success">
          <span className="min-w-0 break-words">{importResult}</span>
          <button
            type="button"
            onClick={() => setImportResult(null)}
            aria-label="关闭导入提示"
            className="shrink-0 rounded p-0.5 hover:bg-success/20"
          >
            <X className="h-3.5 w-3.5" aria-hidden />
          </button>
        </div>
      )}

      {/* ---------- Tab: 概览 ---------- */}
      {activeTab === 'overview' && (
        <>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between sm:gap-3">
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-ink sm:text-lg">Agent 订阅中心</h2>
              <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                套餐额度 / 供应商 / Agent 切换 / 本地网关，都在这里。
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setShowAdd(true)}
                className="inline-flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover sm:flex-none"
              >
                <Plus className="h-4 w-4" aria-hidden />
                添加供应商
              </button>
              <button
                type="button"
                onClick={() => void handleCcSwitchImport()}
                disabled={importing}
                title="从本机 cc-switch 自动导入已配置的供应商（含 OpenDesign 控制面 Key）"
                className="inline-flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50 sm:flex-none"
              >
                <Download className={`h-4 w-4 ${importing ? 'animate-pulse' : ''}`} aria-hidden />
                <span className="hidden sm:inline">
                  {importing ? '同步中…' : '从 cc-switch 同步'}
                </span>
                <span className="sm:hidden">{importing ? '同步中…' : 'cc-switch'}</span>
              </button>
              <button
                type="button"
                onClick={() => void handleMagpieImport()}
                disabled={importing}
                title="从本机 magpie 同步已配置的供应商与订阅账号"
                className="inline-flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50 sm:flex-none"
              >
                <Download className={`h-4 w-4 ${importing ? 'animate-pulse' : ''}`} aria-hidden />
                <span className="hidden sm:inline">
                  {importing ? '同步中…' : '从 magpie 同步'}
                </span>
                <span className="sm:hidden">{importing ? '同步中…' : 'magpie'}</span>
              </button>
              <button
                type="button"
                onClick={() => void loadAll(true)}
                disabled={refreshing || loading}
                className="inline-flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50 sm:flex-none"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden />
                {refreshing ? '刷新中…' : '全部刷新'}
              </button>
            </div>
          </div>

          {queriedAt && hasAnything && (
            <p className="text-xs text-ink-faint">
              共 {results.length} 项，成功 {successCount} 项 · 更新于 {relativeTime(queriedAt, now)}
            </p>
          )}

          {failoverGroups.length > 0 && (
            <div className="rounded-lg border border-border bg-surface-1 px-3 py-2">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-ink-muted">
                <Settings2 className="h-3.5 w-3.5" aria-hidden />
                多账号可切换（同供应商配了多个账号，额度用完自动换下一个）
              </div>
              <div className="flex flex-wrap gap-2">
                {failoverGroups.map((group) => (
                  <span
                    key={group.providerId}
                    className="rounded-full bg-surface-2 px-2.5 py-1 text-xs text-ink"
                    title={`该供应商 ${group.accounts} 个账号，${group.available} 个可用`}
                  >
                    {group.label}
                    <span className="ml-1 text-ink-faint">
                      {group.available}/{group.accounts} 可用
                      {group.tightestRemaining !== null &&
                        ` · 最紧 ${group.tightestRemaining.toFixed(0)}%`}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 套餐额度：概览首屏置顶（用户明确要求） */}
          <div className="flex items-center justify-between gap-2">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
              <Gauge className="h-4 w-4" aria-hidden />
              套餐额度
            </h3>
            {queriedAt && hasAnything && (
              <span className="text-xs text-ink-faint">
                共 {results.length} 项，成功 {successCount} 项
              </span>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16 text-ink-muted">
              <RefreshCw className="mr-2 h-5 w-5 animate-spin" aria-hidden />
              正在加载…
            </div>
          ) : !hasAnything ? (
            <div className="flex flex-col items-center gap-3 px-2 py-12 text-center sm:py-16">
              <Settings2 className="h-10 w-10 text-ink-faint" aria-hidden />
              <p className="text-sm font-medium text-ink">还没有配置任何订阅</p>
              <p className="max-w-md text-xs text-ink-muted">
                大多数供应商只需要一个 API Key：点「添加供应商」，选择供应商并粘贴 Key 即可。
                本机已登录的 Kimi Code / ZCode / Claude Code / Codex / Gemini 会自动出现。
              </p>
              <button
                type="button"
                onClick={() => setShowAdd(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
              >
                <Plus className="h-4 w-4" aria-hidden />
                添加第一个供应商
              </button>
            </div>
          ) : (
            renderQuotaGrid()
          )}
        </>
      )}

      {/* ---------- Tab: 供应商 ---------- */}
      {activeTab === 'providers' && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-semibold text-ink">供应商</h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                共 {providers.length} 家可选，已配置 {accounts.length} 个账号
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setShowAdd(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
              >
                <Plus className="h-4 w-4" aria-hidden />
                添加
              </button>
              <button
                type="button"
                onClick={() => void handleCcSwitchImport()}
                disabled={importing}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50"
              >
                <Download className={`h-4 w-4 ${importing ? 'animate-pulse' : ''}`} aria-hidden />
                {importing ? '同步中…' : 'cc-switch 同步'}
              </button>
              <button
                type="button"
                onClick={() => void handleMagpieImport()}
                disabled={importing}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50"
              >
                <Download className={`h-4 w-4 ${importing ? 'animate-pulse' : ''}`} aria-hidden />
                {importing ? '同步中…' : 'magpie 同步'}
              </button>
            </div>
          </div>

          {accounts.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-ink-muted">
              还没有供应商账号。点「添加」选择预设后粘贴 API Key 即可。
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {accounts.map((account) => {
                const spec = providers.find((p) => p.id === account.providerId);
                return (
                  <div
                    key={account.id}
                    className="flex flex-col gap-1.5 rounded-lg border border-border p-3"
                  >
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">
                        {account.label}
                      </span>
                      <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-faint">
                        {kindLabel(spec?.kind ?? 'window')}
                      </span>
                      {!account.enabled && <Badge variant="outline">已停用</Badge>}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-faint">
                      {account.maskedKey ? (
                        <span className="break-all font-mono">{account.maskedKey}</span>
                      ) : (
                        <span>无需 Key</span>
                      )}
                      {account.isManual && (
                        <span>
                          手动：{account.manualUsed}/{account.manualTotal} {account.quotaUnit}
                        </span>
                      )}
                    </div>
                    {spec?.hint && (
                      <p className="line-clamp-2 text-[11px] text-ink-faint">{spec.hint}</p>
                    )}
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      {account.isManual && (
                        <button
                          type="button"
                          onClick={() => setAdjusting(account)}
                          className="rounded-md px-2 py-1 text-xs text-ink-muted hover:bg-surface-2 hover:text-ink"
                        >
                          调整额度
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setEditingAccount(account)}
                        className="rounded-md px-2 py-1 text-xs text-ink-muted hover:bg-surface-2 hover:text-ink"
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleToggleEnabled(account)}
                        className="rounded-md px-2 py-1 text-xs text-ink-muted hover:bg-surface-2 hover:text-ink"
                      >
                        {account.enabled ? '停用' : '启用'}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleRemove(account.id)}
                        className="rounded-md px-2 py-1 text-xs text-ink-muted hover:bg-danger/10 hover:text-accent-danger"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ---------- Tab: Agent 切换 ---------- */}
      {activeTab === 'agents' && <AgentSwitchPanel accounts={accounts} />}

      {/* ---------- Tab: 本地网关 ---------- */}
      {activeTab === 'gateway' && <GatewayPanel />}
      </div>

      {/* 弹窗放在滚动容器之外，避免受内容滚动影响 */}
      {showAdd && (
        <AddAccountDialog
          providers={providers}
          onClose={() => setShowAdd(false)}
          onSaved={() => void loadAll(true)}
        />
      )}

      {manualAccount && (
        <QuotaAdjustDialog
          account={manualAccount}
          onClose={() => setAdjusting(null)}
          onSaved={() => void loadAll(true)}
        />
      )}

      {editingAccount && (
        <EditAccountDialog
          account={
            accounts.find((a) => a.id === editingAccount.id) ?? editingAccount
          }
          spec={providers.find((p) => p.id === editingAccount.providerId) ?? null}
          onClose={() => setEditingAccount(null)}
          onSaved={() => void loadAll(true)}
        />
      )}
    </div>
  );
}

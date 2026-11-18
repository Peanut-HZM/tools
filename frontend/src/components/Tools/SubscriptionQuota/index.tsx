import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Plus,
  RefreshCw,
  Settings2,
  Trash2,
  X,
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
  countdownStr,
  credentialStatusText,
  formatAmount,
  isBalanceTier,
  kindLabel,
  needsHint,
  pickTiers,
  providerInitials,
  relativeTime,
  remainingPercent,
  sortTiers,
  tierLabel,
  toneForBalance,
  toneForRemaining,
} from './quotaRules';

const TONE_STYLES = {
  normal: { text: 'text-accent-success', bar: 'bg-accent-success' },
  warning: { text: 'text-accent-warning', bar: 'bg-accent-warning' },
  danger: { text: 'text-accent-danger', bar: 'bg-accent-danger' },
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
    <div className="flex items-center gap-2 text-sm" title={`已用 ${tier.utilization.toFixed(1)}%`}>
      <span className="w-[76px] shrink-0 truncate text-ink-muted">{tierLabel(tier.name)}</span>
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
  quota: QuotaResultDto;
  now: number;
  refreshing: boolean;
  onRefresh: () => void;
  onRemove?: () => void;
}

/** 单个账号 / 订阅的额度卡片 */
export function QuotaCard({ quota, now, refreshing, onRefresh, onRemove }: QuotaCardProps) {
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

  const removable = Boolean(onRemove) && Boolean(quota.accountId) && !quota.isLocal;

  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              aria-hidden
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-2 text-[10px] font-semibold text-ink-muted"
            >
              {providerInitials(quota.label)}
            </span>
            <h3 className="truncate text-sm font-semibold text-ink">{quota.label}</h3>
            <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-faint">
              {kindLabel(quota.kind)}
            </span>
            {quota.planName && (
              <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-muted">
                {quota.planName}
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
            {statusBadge}
            {quota.maskedKey && <span className="font-mono">{quota.maskedKey}</span>}
            {quota.isLocal && (
              <span className="rounded-full bg-surface-2 px-2 py-0.5">本机登录</span>
            )}
            {updated && <span>{updated}更新</span>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLabel(spec?.name ?? '');
    setExtraValues({});
    setApiKey('');
    setBaseUrl('');
    setRegion(spec?.regions?.includes('cn') ? 'cn' : 'intl');
  }, [spec]);

  const handleSave = useCallback(async () => {
    if (!spec) return;
    setSaving(true);
    setError(null);
    try {
      const extra: Record<string, unknown> = { ...extraValues };
      if (spec.regions.length > 0) extra.region = region;
      if (spec.needsBaseUrl && baseUrl.trim()) extra.base_url = baseUrl.trim();
      if (spec.needs.includes('control_key')) {
        extra.control_key = apiKey;
      } else if (spec.needs.includes('access_key')) {
        // AK/SK 都从 extraValues 来
      } else {
        extra.api_key = apiKey;
      }
      await quotaApi.addAccount({
        providerId: spec.id,
        label: label.trim() || spec.name,
        apiKey: apiKey || undefined,
        extra,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }, [spec, label, apiKey, region, baseUrl, extraValues, onSaved, onClose]);

  const keyField = spec?.needs.find((n) => n === 'api_key' || n === 'control_key') ?? 'api_key';
  const otherFields = spec?.needs.filter((n) => n !== 'api_key' && n !== 'control_key') ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="添加供应商"
        className="w-full max-w-lg rounded-xl border border-border bg-surface-1 p-5 shadow-xl"
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

/** 订阅套餐额度工具主界面 */
export default function SubscriptionQuotaTool() {
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

      // 无论有没有用户账号都查一次：本机 CLI 凭据（如 Kimi Code / ZCode 登录）会自动出现
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

  const handleImport = useCallback(async () => {
    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await quotaApi.importFromCcSwitch(false);
      if (!mountedRef.current) return;
      if (result.imported === 0) {
        setImportResult('cc-switch 里没有可导入的供应商凭据');
      } else {
        const control = result.items.filter((i) => i.fromControlKey).map((i) => i.providerId);
        setImportResult(
          `已导入 ${result.imported} 个供应商（新建 ${result.created} / 更新 ${result.updated}）` +
            (control.length > 0 ? `，其中控制面 Key：${control.join('、')}` : '')
        );
      }
      await loadAll(true);
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : '导入失败');
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

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">订阅套餐额度</h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            添加供应商并填入 API Key 即可查询套餐窗口与账户余额；只读凭据，不做任何修改。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
          >
            <Plus className="h-4 w-4" aria-hidden />
            添加供应商
          </button>
          <button
            type="button"
            onClick={() => void handleImport()}
            disabled={importing}
            title="从本机 cc-switch 自动导入已配置的供应商（含 OpenDesign 控制面 Key）"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50"
          >
            <Download className={`h-4 w-4 ${importing ? 'animate-pulse' : ''}`} aria-hidden />
            {importing ? '导入中…' : '从 cc-switch 导入'}
          </button>
          <button
            type="button"
            onClick={() => void loadAll(true)}
            disabled={refreshing || loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-1.5 text-sm text-ink hover:bg-surface-2 disabled:opacity-50"
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

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}

      {importResult && (
        <div className="flex items-start justify-between gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-accent-success">
          <span>{importResult}</span>
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

      {loading ? (
        <div className="flex items-center justify-center py-16 text-ink-muted">
          <RefreshCw className="mr-2 h-5 w-5 animate-spin" aria-hidden />
          正在加载…
        </div>
      ) : !hasAnything ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
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
      ) : results.length === 0 ? (
        <p className="py-16 text-center text-sm text-ink-muted">暂无已配置的供应商</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {results.map((quota) => (
            <QuotaCard
              key={`${quota.providerId}:${quota.accountId ?? 'subscription'}`}
              quota={quota}
              now={now}
              refreshing={refreshing}
              onRefresh={() => void handleRefreshOne(quota)}
              onRemove={
                quota.accountId ? () => void handleRemove(quota.accountId!) : undefined
              }
            />
          ))}
        </div>
      )}

      {showAdd && (
        <AddAccountDialog
          providers={providers}
          onClose={() => setShowAdd(false)}
          onSaved={() => void loadAll(true)}
        />
      )}
    </div>
  );
}

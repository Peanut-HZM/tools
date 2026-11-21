import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Taro, { useDidShow, useDidHide } from '@tarojs/taro';
import { View, Text, Picker, Input } from '@tarojs/components';
import {
  subscriptionQuotaApi,
  type ProviderSpec,
  type QuotaAccount,
  type QuotaItem,
  type QuotaQueryResponse,
} from '../../../services/subscriptionQuota';
import { useQuotaCacheStore, QUOTA_CACHE_TTL_MS } from '../../../stores/subscriptionQuota';
import { formatApiError } from '../../../utils/mobileTool';
import { remainingPercent, tierLabel, toneForRemaining } from '../../../utils/quotaDisplay';
import Loading from '../../../components/Loading';
import './index.scss';

/**
 * Agent 订阅中心（移动端，只读为主）
 *
 * 数据源与 PC 端「Agent 订阅中心」完全一致：/api/subscription-quota/query
 * - 展示所有已配置账号 + 本机订阅的额度（窗口/余额/失败原因）
 * - 支持添加供应商账号（不做上传、同步、Agent 切换）
 */

const PROVIDER_LABELS: Record<string, string> = {
  claude: 'Claude Code', codex: 'Codex', gemini: 'Gemini CLI',
  kimi: 'Kimi For Coding', zhipu: '智谱 GLM', zhipu_team: '智谱 GLM 团队',
  minimax: 'MiniMax', zenmux: 'ZenMux', opencode_go: 'OpenCode Go',
  command_code: 'Command Code', opendesign: 'OpenDesign', zcode: 'ZCode',
  volcengine: '火山方舟', deepseek: 'DeepSeek', stepfun: 'StepFun',
  siliconflow: 'SiliconFlow', openrouter: 'OpenRouter', novita: 'Novita AI',
  ollama_cloud: 'Ollama Cloud', zhipu_payg: '智谱按量付费', newapi: 'NewAPI',
  sub2api: 'Sub2API', generic_balance: '通用余额', manual: '手动额度',
};

function providerLabel(id: string): string {
  return PROVIDER_LABELS[id] || id;
}

function fmtNum(n: number): string {
  if (!Number.isFinite(n)) return '-';
  return n >= 1000
    ? n.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : String(Math.round(n * 100) / 100);
}

function countdown(resetsAt?: string | null, now = Date.now()): string {
  if (!resetsAt) return '';
  const ts = Date.parse(resetsAt);
  if (Number.isNaN(ts)) return '';
  const diff = ts - now;
  if (diff <= 0) return '已重置';
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return h >= 24 ? `${Math.floor(h / 24)}天${h % 24}时后重置` : `${h}时${m}分后重置`;
}

function fmtQueriedAt(ms?: number | null): string {
  if (!ms) return '';
  try {
    return new Date(ms).toLocaleString();
  } catch {
    return '';
  }
}

type SectionKey = 'usage' | 'providers';

export default function AgentHubPage() {
  const [section, setSection] = useState<SectionKey>('usage');
  const [quota, setQuota] = useState<QuotaQueryResponse | null>(null);
  const [providers, setProviders] = useState<ProviderSpec[]>([]);
  const [accounts, setAccounts] = useState<QuotaAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const bootstrappedRef = useRef(false);

  const hydrateCache = useQuotaCacheStore(state => state.hydrate);
  const saveCache = useQuotaCacheStore(state => state.setData);

  const loadUsage = useCallback(async (force = false) => {
    const data = await subscriptionQuotaApi.query(force);
    if (!data || !Array.isArray(data.accounts) || !Array.isArray(data.subscriptions)) {
      const detail = (data as unknown as { detail?: string })?.detail;
      throw new Error(detail || '额度数据格式异常');
    }
    setQuota(data);
    saveCache(data);
    setError('');
  }, [saveCache]);

  const loadProviders = useCallback(async () => {
    const [providerRes, accountRes] = await Promise.all([
      subscriptionQuotaApi.listProviders(),
      subscriptionQuotaApi.listAccounts(),
    ]);
    setProviders(providerRes.providers);
    setAccounts(accountRes.accounts);
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      // 先同步恢复本地缓存：有缓存时立即渲染，不等接口
      hydrateCache();
      const cached = useQuotaCacheStore.getState().data;
      const cachedAt = useQuotaCacheStore.getState().updatedAt;
      const hasCache = Boolean(cached);
      if (hasCache) {
        setQuota(cached);
        setLoading(false);
      }

      const stale = !hasCache || Date.now() - cachedAt > QUOTA_CACHE_TTL_MS;

      try {
        // 无本地缓存时，先用数据库快照兜底（8s 超时，不发外部网络请求）
        if (!hasCache) {
          try {
            const snapshot = await subscriptionQuotaApi.snapshot();
            if (alive && snapshot && Array.isArray(snapshot.accounts) && snapshot.accounts.length > 0) {
              setQuota(snapshot);
              setLoading(false);
            }
          } catch {
            // 快照不可用不阻断完整查询
          }
        }

        if (stale) {
          if (hasCache) setRefreshing(true);
          await loadUsage(false);
        }
        await loadProviders();
      } catch (e) {
        if (alive) setError(formatApiError(e));
      } finally {
        if (alive) {
          setLoading(false);
          setRefreshing(false);
          bootstrappedRef.current = true;
        }
      }
    })();
    return () => { alive = false; };
  }, [hydrateCache, loadUsage, loadProviders]);

  // 页面再次显示：缓存超过 5 分钟才后台刷新，避免频繁请求外部额度接口
  useDidShow(() => {
    if (!bootstrappedRef.current) return;
    const { updatedAt } = useQuotaCacheStore.getState();
    if (Date.now() - updatedAt > QUOTA_CACHE_TTL_MS && !refreshing) {
      loadUsage(false).catch(() => {
        // 后台刷新失败保留旧数据，不打断页面
      });
    }
  });

  // 订阅用量页：可见时每分钟静默刷新一次（与 Web 端一致）
  // 约束：不切 loading、不弹 toast、失败保留旧数据、请求不叠加、页面隐藏时暂停
  const visibleRef = useRef(true);
  useDidShow(() => { visibleRef.current = true; });
  useDidHide(() => { visibleRef.current = false; });
  const autoRefreshingRef = useRef(false);
  useEffect(() => {
    if (section !== 'usage') return;
    const timer = setInterval(() => {
      if (!visibleRef.current || autoRefreshingRef.current || refreshing) return;
      autoRefreshingRef.current = true;
      loadUsage(false)
        .catch(() => {
          // 自动刷新失败：保留现有数据，不打扰用户
        })
        .finally(() => { autoRefreshingRef.current = false; });
    }, 60_000);
    return () => clearInterval(timer);
  }, [section, loadUsage, refreshing]);

  const refreshAll = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await loadUsage(true);
      Taro.showToast({ title: '额度已刷新', icon: 'success' });
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setRefreshing(false);
    }
  };

  const allItems = useMemo(() => {
    if (!quota) return [] as QuotaItem[];
    return [...quota.accounts, ...quota.subscriptions].sort((a, b) => {
      const aEnabled = a.enabled === false ? 1 : 0;
      const bEnabled = b.enabled === false ? 1 : 0;
      if (aEnabled !== bEnabled) return aEnabled - bEnabled;
      return (a.label || a.providerId).localeCompare(b.label || b.providerId);
    });
  }, [quota]);

  const successCount = allItems.filter(item => item.success).length;
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, []);

  if (loading) return <Loading text='加载订阅额度...' />;

  return (
    <View className='agent-hub-page'>
      <View className='section-tabs'>
        {([
          { key: 'usage', label: '订阅用量' },
          { key: 'providers', label: '供应商' },
        ] as { key: SectionKey; label: string }[]).map(item => (
          <View
            key={item.key}
            className={`section-tab ${section === item.key ? 'active' : ''}`}
            onClick={() => setSection(item.key)}
          >
            <Text>{item.label}</Text>
          </View>
        ))}
      </View>

      {section === 'usage' && (
        <View className='section-body'>
          <View className='meta-row'>
            <View>
              <Text className='meta-text'>共 {allItems.length} 个订阅</Text>
              <Text className='meta-sub'>额度查询成功 {successCount} 个</Text>
            </View>
            <View className={`btn btn-primary ${refreshing ? 'disabled' : ''}`} onClick={refreshAll}>
              <Text>{refreshing ? '刷新中…' : '全部刷新'}</Text>
            </View>
          </View>

          {error ? (
            <View className='empty-card'>
              <Text className='error-text'>{error}</Text>
              <View className='btn' onClick={() => { setLoading(true); loadUsage(true).finally(() => setLoading(false)); }}>
                <Text>重试</Text>
              </View>
            </View>
          ) : allItems.length === 0 ? (
            <View className='empty-card'>
              <Text>暂未配置订阅额度</Text>
              <Text className='meta-sub'>切换到「供应商」添加账号后即可在这里查看用量</Text>
              <Text className='meta-sub'>订阅按登录账号隔离；若数据在另一个账号下，请先登录/绑定该账号</Text>
            </View>
          ) : (
            allItems.map((item, idx) => (
              <QuotaCard key={`${item.providerId}-${item.accountId || 'sub'}-${idx}`} item={item} now={now} />
            ))
          )}
        </View>
      )}

      {section === 'providers' && (
        <View className='section-body'>
          <AddAccountForm
            providers={providers.filter(p => p.addable)}
            onCreated={async () => {
              await loadProviders();
              await loadUsage(true);
            }}
          />
          {accounts.length === 0 ? (
            <View className='empty-card'><Text>还没有供应商账号</Text></View>
          ) : (
            accounts.map(account => (
              <View key={account.id} className='glass-card provider-card'>
                <View className='card-head'>
                  <Text className='card-title'>{account.label || providerLabel(account.providerId)}</Text>
                  <Text className='kind-badge'>{providerLabel(account.providerId)}</Text>
                </View>
                {!account.enabled ? <Text className='status-badge status-muted provider-status'>已停用</Text> : null}
                <Text className='muted small'>
                  {account.isManual
                    ? `手动额度 剩余 ${fmtNum(Math.max(0, account.manualTotal - account.manualUsed))} / ${fmtNum(account.manualTotal)} ${account.quotaUnit}`
                    : `Key: ${account.hasKey ? account.maskedKey : '未配置'}`}
                </Text>
                {account.baseUrl ? <Text className='muted small'>{account.baseUrl}</Text> : null}
                <View className='card-actions'>
                  <View
                    className='btn btn-danger'
                    onClick={async () => {
                      const { confirm } = await Taro.showModal({
                        title: '删除供应商账号',
                        content: `删除「${account.label || providerLabel(account.providerId)}」？`,
                        confirmColor: '#F87171',
                      });
                      if (!confirm) return;
                      try {
                        await subscriptionQuotaApi.deleteAccount(account.id);
                        setAccounts(prev => prev.filter(x => x.id !== account.id));
                        await loadUsage(true);
                        Taro.showToast({ title: '已删除', icon: 'none' });
                      } catch (e) {
                        Taro.showToast({ title: formatApiError(e), icon: 'none' });
                      }
                    }}
                  >
                    <Text>删除</Text>
                  </View>
                </View>
              </View>
            ))
          )}
        </View>
      )}
    </View>
  );
}

/* ------------------------------------------------------------------ */
/* 额度卡片                                                            */
/* ------------------------------------------------------------------ */

function QuotaCard({ item, now }: { item: QuotaItem; now: number }) {
  const tiers = item.tiers || [];
  const disabled = item.enabled === false;
  const statusText = disabled
    ? '已停用'
    : item.success
      ? (item.isLocal ? '本机登录' : '正常')
      : item.credentialStatus === 'not_found'
        ? '未配置'
        : '查询失败';

  return (
    <View className={`glass-card sub-card ${disabled ? 'sub-card--disabled' : ''}`}>
      <View className='card-head'>
        <View className='card-title-row'>
          <Text className='card-title'>{item.label || providerLabel(item.providerId)}</Text>
          {item.isLocal ? <Text className='chip chip--local'>本机</Text> : null}
          {item.isChannel ? <Text className='chip chip--channel'>渠道</Text> : null}
        </View>
        <Text className={`status-badge ${disabled ? 'status-muted' : item.success ? 'status-ok' : item.credentialStatus === 'not_found' ? 'status-muted' : 'status-error'}`}>
          {statusText}
        </Text>
      </View>
      <Text className='muted small'>{providerLabel(item.providerId)}{item.planName ? ` · ${item.planName}` : ''}</Text>

      {tiers.length > 0 ? (
        tiers.map((tier, idx) => {
          const remaining = remainingPercent(tier.utilization || 0);
          const balanceText = tier.balanceAmount != null
            ? `余额 ${fmtNum(tier.balanceAmount)} ${tier.balanceUnit || ''}`
            : undefined;
          const usdText = tier.usedValueUsd != null && tier.maxValueUsd != null
            ? `剩余 $${fmtNum(Math.max(0, tier.maxValueUsd - tier.usedValueUsd))}`
            : undefined;
          return (
            <View key={idx} className='tier-block'>
              <View className='tier-row'>
                <Text className='tier-name'>{tierLabel(tier.name)}</Text>
                <Text className={`tier-value ${toneForRemaining(remaining)}`}>
                  {balanceText || usdText || `剩余 ${fmtNum(remaining)}%`}
                </Text>
              </View>
              <View className='bar-track'>
                <View className={`bar-fill ${toneForRemaining(remaining)}`} style={{ width: `${remaining}%` }} />
              </View>
              {tier.resetsAt ? (
                <Text className='tier-reset'>{countdown(tier.resetsAt, now)}</Text>
              ) : null}
            </View>
          );
        })
      ) : item.success ? (
        <Text className='muted small'>暂无窗口数据</Text>
      ) : (
        <Text className='error-text'>{item.error || item.credentialMessage || '查询失败'}</Text>
      )}

      {item.maskedKey ? <Text className='tiny'>Key: {item.maskedKey}</Text> : null}
      {item.queriedAt ? <Text className='tiny'>上次查询: {fmtQueriedAt(item.queriedAt)}</Text> : null}
    </View>
  );
}

/* ------------------------------------------------------------------ */
/* 添加供应商账号                                                      */
/* ------------------------------------------------------------------ */

function AddAccountForm({ providers, onCreated }: {
  providers: ProviderSpec[];
  onCreated: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [providerId, setProviderId] = useState('');
  const [label, setLabel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [region, setRegion] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [extraValues, setExtraValues] = useState<Record<string, string>>({});
  const [manualTotal, setManualTotal] = useState('100');
  const [manualUsed, setManualUsed] = useState('0');
  const [unit, setUnit] = useState('credits');
  const [saving, setSaving] = useState(false);

  const spec = useMemo(
    () => providers.find(p => p.id === providerId),
    [providers, providerId],
  );

  const pickProvider = (id: string) => {
    setProviderId(id);
    const next = providers.find(p => p.id === id);
    if (next) {
      setLabel(next.name);
      setRegion(next.regions[0] || '');
      setBaseUrl('');
      setExtraValues({});
      if (next.kind === 'manual') {
        setManualTotal('100');
        setManualUsed('0');
        setUnit('credits');
      }
    }
  };

  const reset = () => {
    setOpen(false);
    setProviderId('');
    setLabel('');
    setApiKey('');
    setRegion('');
    setBaseUrl('');
    setExtraValues({});
    setSaving(false);
  };

  const save = async () => {
    if (!spec) { Taro.showToast({ title: '请选择供应商类型', icon: 'none' }); return; }
    if (!label.trim()) { Taro.showToast({ title: '请填写显示名', icon: 'none' }); return; }
    const needsKey = spec.needs.includes('api_key');
    if (needsKey && !apiKey.trim()) {
      Taro.showToast({ title: '请填写 API Key', icon: 'none' }); return;
    }
    setSaving(true);
    try {
      const extra: Record<string, unknown> = {};
      if (region) extra.region = region;
      if (baseUrl.trim()) extra.base_url = baseUrl.trim();
      Object.entries(extraValues).forEach(([key, value]) => {
        if (value.trim()) extra[key] = value.trim();
      });
      await subscriptionQuotaApi.createAccount({
        provider_id: spec.id,
        label: label.trim(),
        api_key: apiKey.trim() || undefined,
        extra,
        manual_total: spec.kind === 'manual' ? Number(manualTotal) || 0 : undefined,
        manual_used: spec.kind === 'manual' ? Number(manualUsed) || 0 : undefined,
        quota_unit: spec.kind === 'manual' ? unit : undefined,
        window_type: spec.kind === 'manual' ? '5h' : undefined,
      });
      Taro.showToast({ title: '已添加', icon: 'success' });
      await onCreated();
      reset();
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <View className='btn btn-primary add-btn' onClick={() => setOpen(true)}>
        <Text>+ 添加供应商账号</Text>
      </View>
    );
  }

  const extraFieldEntries = Object.entries(spec?.extraFields || {});
  const needEntries = (spec?.needs || []).filter(key => key !== 'api_key');

  return (
    <View className='glass-card add-card'>
      <Text className='card-title'>添加供应商账号</Text>
      {spec?.hint ? <Text className='tiny'>{spec.hint}</Text> : null}

      <Text className='field-label'>供应商类型</Text>
      <Picker
        mode='selector'
        range={providers.map(p => p.name)}
        onChange={(e) => pickProvider(providers[Number(e.detail.value)]?.id || '')}
      >
        <View className='layer-input'><Text>{spec ? spec.name : '选择供应商'}</Text></View>
      </Picker>
      {spec ? (
        <Text className='tiny'>
          {spec.configuredCount > 0
            ? `当前已配置 ${spec.configuredCount} 个账号`
            : '当前未配置，可直接添加'}
        </Text>
      ) : null}

      <Text className='field-label'>显示名</Text>
      <Input className='layer-input' value={label} onInput={(e) => setLabel(e.detail.value)} />

      {spec?.regions && spec.regions.length > 1 ? (
        <>
          <Text className='field-label'>区域</Text>
          <Picker
            mode='selector'
            range={spec.regions}
            onChange={(e) => setRegion(spec.regions[Number(e.detail.value)] || '')}
          >
            <View className='layer-input'><Text>{region || spec.regions[0]}</Text></View>
          </Picker>
        </>
      ) : null}

      {spec?.needs.includes('api_key') ? (
        <>
          <Text className='field-label'>API Key</Text>
          <Input className='layer-input' password value={apiKey} onInput={(e) => setApiKey(e.detail.value)} placeholder='粘贴 API Key' />
        </>
      ) : null}

      {needEntries.map(key => (
        <View key={key}>
          <Text className='field-label'>{key}</Text>
          <Input
            className='layer-input'
            password
            value={extraValues[key] || ''}
            onInput={(e) => setExtraValues(prev => ({ ...prev, [key]: e.detail.value }))}
          />
        </View>
      ))}

      {spec?.needsBaseUrl ? (
        <>
          <Text className='field-label'>站点 base_url</Text>
          <Input className='layer-input' value={baseUrl} onInput={(e) => setBaseUrl(e.detail.value)} placeholder='https://...' />
        </>
      ) : null}

      {extraFieldEntries.map(([key, hint]) => (
        <View key={key}>
          <Text className='field-label'>{hint || key}</Text>
          <Input
            className='layer-input'
            password={key.toLowerCase().includes('key') || key.toLowerCase().includes('secret')}
            value={extraValues[key] || ''}
            onInput={(e) => setExtraValues(prev => ({ ...prev, [key]: e.detail.value }))}
          />
        </View>
      ))}

      {spec?.kind === 'manual' ? (
        <>
          <Text className='field-label'>总额度</Text>
          <Input className='layer-input' type='digit' value={manualTotal} onInput={(e) => setManualTotal(e.detail.value)} />
          <Text className='field-label'>已用量</Text>
          <Input className='layer-input' type='digit' value={manualUsed} onInput={(e) => setManualUsed(e.detail.value)} />
          <Text className='field-label'>单位</Text>
          <Picker
            mode='selector'
            range={['credits', 'USD', 'tokens', 'requests', 'percent']}
            onChange={(e) => setUnit(['credits', 'USD', 'tokens', 'requests', 'percent'][Number(e.detail.value)])}
          >
            <View className='layer-input'><Text>{unit}</Text></View>
          </Picker>
        </>
      ) : null}

      <View className='layer-actions'>
        <View className='btn' onClick={reset}><Text>取消</Text></View>
        <View className={`btn btn-primary ${saving ? 'disabled' : ''}`} onClick={() => { if (!saving) save(); }}>
          <Text>{saving ? '保存中…' : '保存'}</Text>
        </View>
      </View>
    </View>
  );
}
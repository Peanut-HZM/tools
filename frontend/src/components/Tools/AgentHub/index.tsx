/**
 * Agent Hub — Agent 订阅与供应商中心
 *
 * 整合 cc-switch（供应商管理/一键切换/订阅套餐用量）与 magpie（多 agent 配置改写/额度聚合）的核心能力。
 * 设计文档: docs/plans/2026-11-18-agent-hub-design.md
 *
 * 页面轮询规范：卡片局部更新（无整页刷新）、全局最多一个 loading、失败保留原数据轻提示。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw, Plus, Pencil, Trash2, ArrowRightLeft, Undo2, Eye, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import {
  agentHubApi, AgentHubPreset, AgentHubProvider, AgentHubSubscription,
  AgentHubAgent, QuotaTier, UsageResult, SwitchPreview,
} from '@/api/agentHubApi';

const KIND_LABELS: Record<string, string> = {
  claude_official: 'Claude 官方', codex_official: 'ChatGPT/Codex', gemini_official: 'Gemini 订阅',
  opendesign: 'OpenDesign', kimi: 'Kimi', zhipu: '智谱 GLM', minimax: 'MiniMax', zenmux: 'ZenMux',
  opencode_go: 'OpenCode Go', deepseek: 'DeepSeek', openrouter: 'OpenRouter', siliconflow: '硅基流动',
  newapi: 'NewAPI 中转', sub2api: 'Sub2API', generic_balance: '通用余额', manual: '手动额度',
};

const AGENT_LABELS: Record<string, string> = {
  claude: 'Claude Code', codex: 'Codex CLI', gemini: 'Gemini CLI',
  kimi: 'Kimi Code', opencode: 'OpenCode', minimax: 'MiniMax Code',
};

function countdown(resetsAt?: string): string {
  if (!resetsAt) return '';
  const ts = Date.parse(resetsAt);
  if (Number.isNaN(ts)) return '';
  const diff = ts - Date.now();
  if (diff <= 0) return '已重置';
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return h >= 24 ? `${Math.floor(h / 24)}天${h % 24}时后重置` : `${h}时${m}分后重置`;
}

/** 进度条色调：剩余 <10% 红、<20% 橙、其余绿（对齐 cc-switch WARN_BELOW_PERCENT=20） */
function barTone(usedPct: number): string {
  if (usedPct >= 90) return 'bg-red-500';
  if (usedPct >= 80) return 'bg-orange-500';
  return 'bg-emerald-500';
}

function fmtNum(n: number): string {
  return n >= 1000 ? n.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : String(Math.round(n * 100) / 100);
}

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------

export default function AgentHub() {
  const [activeTab, setActiveTab] = useState<'usage' | 'providers' | 'agents'>('usage');
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-bold">Agent 订阅中心</h1>
        <span className="text-xs text-gray-400">供应商管理 · 套餐用量 · 一键切换</span>
      </div>
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
        <TabsList>
          <TabsTrigger value="usage">订阅用量</TabsTrigger>
          <TabsTrigger value="providers">供应商</TabsTrigger>
          <TabsTrigger value="agents">Agent 切换</TabsTrigger>
        </TabsList>
        <TabsContent value="usage"><UsageTab /></TabsContent>
        <TabsContent value="providers"><ProvidersTab /></TabsContent>
        <TabsContent value="agents"><AgentsTab /></TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 1：订阅用量（第一优先级）
// ---------------------------------------------------------------------------

function UsageTab() {
  const [subs, setSubs] = useState<AgentHubSubscription[]>([]);
  const [usageMap, setUsageMap] = useState<Record<string, UsageResult | null>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<{ ok: boolean; text: string } | null>(null);
  const [editing, setEditing] = useState<AgentHubSubscription | null>(null);
  const [addingSub, setAddingSub] = useState(false);
  const toastTimer = useRef<number | null>(null);

  const showToast = useCallback((ok: boolean, text: string) => {
    setToast({ ok, text });
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 3500);
  }, []);

  const loadSubs = useCallback(async () => {
    try {
      const data = await agentHubApi.listSubscriptions();
      setSubs(data.subscriptions);
    } catch (e) {
      showToast(false, `加载订阅失败: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const reloadSubs = loadSubs;

  const applyUsageResults = useCallback((results: (UsageResult & { id: string })[]) => {
    // 局部更新：只改对应卡片的用量（不重置整页状态）
    setUsageMap((prev) => {
      const next = { ...prev };
      for (const r of results) next[r.id] = r;
      return next;
    });
  }, []);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    try {
      const { results } = await agentHubApi.queryAllUsage();
      applyUsageResults(results);
      const failed = results.filter((r) => !r.success);
      if (failed.length === 0) showToast(true, `已刷新 ${results.length} 个订阅用量`);
      else showToast(false, `${results.length - failed.length} 个成功，${failed.length} 个失败（保留上次数据）`);
    } catch (e) {
      showToast(false, `批量刷新失败: ${(e as Error).message}（保留上次数据）`);
    } finally {
      setRefreshing(false);
    }
  }, [applyUsageResults, showToast]);

  const refreshOne = useCallback(async (sub: AgentHubSubscription) => {
    try {
      const r = await agentHubApi.queryUsage(sub.id);
      setUsageMap((prev) => ({ ...prev, [sub.id]: r }));
      showToast(r.success, r.success ? `${sub.name}: 已刷新` : `${sub.name}: ${r.error}`);
    } catch (e) {
      showToast(false, `${sub.name}: ${(e as Error).message}（保留上次数据）`);
    }
  }, [showToast]);

  useEffect(() => { loadSubs(); }, [loadSubs]);
  // 轮询：60s 局部刷新
  useEffect(() => {
    const timer = window.setInterval(() => { refreshAll(); }, 60000);
    return () => window.clearInterval(timer);
  }, [refreshAll]);

  // 初次加载后自动查一次
  const autoQueried = useRef(false);
  useEffect(() => {
    if (!loading && !autoQueried.current) {
      autoQueried.current = true;
      refreshAll();
    }
  }, [loading, refreshAll]);

  const displayable = useMemo(
    () => subs.filter((s) => s.displayable && s.enabled),
    [subs],
  );

  if (loading) return <div className="text-sm text-gray-400 p-6">加载中…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">已启用订阅 {displayable.length} 个（未配置/未启用的不显示）</span>
        <div className="flex items-center gap-2">
          <button onClick={() => setAddingSub(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500">
            <Plus size={14} /> 添加订阅
          </button>
          <button
            onClick={() => refreshAll()}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? '刷新中…' : '全部刷新'}
          </button>
        </div>
      </div>

      {toast && (
        <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg ${toast.ok
          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
          : 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'}`}>
          {toast.ok ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />} {toast.text}
        </div>
      )}

      {displayable.length === 0 ? (
        <div className="text-sm text-gray-400 p-8 text-center border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
          暂无已启用的订阅。去「供应商」页添加供应商，或添加手动额度订阅。
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {displayable.map((sub) => (
            <SubscriptionCard
              key={sub.id} sub={sub} usage={usageMap[sub.id] ?? sub.last_query}
              onRefresh={() => refreshOne(sub)}
              onEdit={() => setEditing(sub)}
              onDelete={async () => {
                if (!window.confirm(`删除订阅「${sub.name}」？`)) return;
                await agentHubApi.deleteSubscription(sub.id);
                setSubs((prev) => prev.filter((s) => s.id !== sub.id));
                showToast(true, '已删除');
              }}
            />
          ))}
        </div>
      )}

      {editing && (
        <QuotaEditModal
          sub={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setSubs((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
            setEditing(null);
            showToast(true, '额度已更新');
            if (updated.kind === 'manual') {
              // manual 额度变化后重算显示（否则卡片仍显示旧查询缓存）
              agentHubApi.queryUsage(updated.id).then((r) => {
                setUsageMap((prev) => ({ ...prev, [updated.id]: r }));
              }).catch(() => {});
            }
          }}
        />
      )}
      {addingSub && (
        <SubscriptionModal
          onClose={() => setAddingSub(false)}
          onSaved={(created) => {
            setSubs((prev) => [created, ...prev]);
            setAddingSub(false);
            showToast(true, '订阅已创建');
          }}
        />
      )}
    </div>
  );
}

function SubscriptionCard({ sub, usage, onRefresh, onEdit, onDelete }: {
  sub: AgentHubSubscription;
  usage: UsageResult | null;
  onRefresh: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const tiers: QuotaTier[] = (usage && usage.success && usage.tiers) ? usage.tiers.slice(0, 4) : [];
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-semibold truncate">{sub.name}</span>
          <Badge variant="secondary">{KIND_LABELS[sub.kind] || sub.kind}</Badge>
          {usage && !usage.success && <Badge variant="destructive">查询失败</Badge>}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button title="编辑额度" onClick={onEdit}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Pencil size={14} /></button>
          <button title="刷新" onClick={onRefresh}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><RefreshCw size={14} /></button>
          <button title="删除" onClick={onDelete}
            className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/30 text-red-500"><Trash2 size={14} /></button>
        </div>
      </div>

      {usage?.plan_name && <div className="text-xs text-gray-500">套餐: {usage.plan_name}</div>}

      {tiers.length > 0 ? (
        <div className="space-y-2">
          {tiers.map((t, i) => {
            const usedPct = t.total > 0 ? (t.used / t.total) * 100 : 0;
            return (
              <div key={i} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-300">{t.name}</span>
                  <span className="text-gray-500">
                    {t.unit === 'percent' ? `${fmtNum(t.used)}%` : `${fmtNum(t.used)} / ${fmtNum(t.total)} ${t.unit}`}
                    {countdown(t.resets_at) && ` · ${countdown(t.resets_at)}`}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                  <div className={`h-full rounded-full ${barTone(usedPct)}`}
                    style={{ width: `${Math.min(100, Math.max(0, usedPct))}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      ) : usage?.balance ? (
        <div className="text-sm">
          余额: <span className={usage.balance.value <= 0 ? 'text-red-500 font-semibold' : 'font-semibold'}>
            {fmtNum(usage.balance.value)} {usage.balance.unit}
          </span>
        </div>
      ) : usage?.success ? (
        <div className="text-xs text-gray-400">暂无可显示的用量窗口</div>
      ) : usage && !usage.success ? (
        <div className="text-xs text-orange-600 dark:text-orange-400 flex items-start gap-1">
          <XCircle size={13} className="mt-0.5 shrink-0" /> {usage.error}
        </div>
      ) : (
        <div className="text-xs text-gray-400">尚未查询（点刷新或等待自动轮询）</div>
      )}

      {usage?.queried_at && (
        <div className="text-[10px] text-gray-400">上次查询: {new Date(usage.queried_at).toLocaleString()}</div>
      )}
      {sub.kind === 'manual' && (
        <div className="text-[10px] text-gray-400">手动模式：额度由你维护，可随时「编辑额度」增加</div>
      )}
    </div>
  );
}

function QuotaEditModal({ sub, onClose, onSaved }: {
  sub: AgentHubSubscription; onClose: () => void;
  onSaved: (s: AgentHubSubscription) => void;
}) {
  const [total, setTotal] = useState(String(sub.total_quota));
  const [used, setUsed] = useState(String(sub.used_quota));
  const [unit, setUnit] = useState(sub.quota_unit);
  const [resetAt, setResetAt] = useState(sub.window_reset_at);
  const [saving, setSaving] = useState(false);
  const isManual = sub.kind === 'manual';

  const save = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        quota_unit: unit, window_reset_at: resetAt,
      };
      if (isManual) {
        payload.total_quota = Number(total) || 0;
        payload.used_quota = Number(used) || 0;
      }
      const { subscription } = await agentHubApi.adjustQuota(sub.id, payload);
      onSaved(subscription);
    } catch (e) {
      window.alert(`保存失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 w-[420px] space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">编辑额度 — {sub.name}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <p className="text-xs text-gray-500">
          {isManual ? '手动模式：可直接修改总额度（支持随时增加）与已用量。' : `该订阅由 API 自动查询（${KIND_LABELS[sub.kind] || sub.kind}），此处仅可调整展示单位与重置时间。`}
        </p>
        {isManual && (
          <>
            <label className="block text-sm">总额度
              <input type="number" min={0} value={total} onChange={(e) => setTotal(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
            </label>
            <label className="block text-sm">已用量
              <input type="number" min={0} value={used} onChange={(e) => setUsed(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
            </label>
          </>
        )}
        <label className="block text-sm">单位
          <select value={unit} onChange={(e) => setUnit(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm">
            {['credits', 'USD', 'tokens', 'requests', 'percent'].map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </label>
        <label className="block text-sm">重置时间（ISO，可空）
          <input value={resetAt} onChange={(e) => setResetAt(e.target.value)} placeholder="2026-11-25T00:00:00Z"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
        </label>
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600">取消</button>
          <button onClick={save} disabled={saving}
            className="px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2：供应商
// ---------------------------------------------------------------------------

function ProvidersTab() {
  const [providers, setProviders] = useState<AgentHubProvider[]>([]);
  const [presets, setPresets] = useState<AgentHubPreset[]>([]);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<AgentHubProvider | null>(null);
  const [toast, setToast] = useState<{ ok: boolean; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [p, pr] = await Promise.all([agentHubApi.listProviders(), agentHubApi.listPresets()]);
      setProviders(p.providers);
      setPresets(pr.presets);
    } catch (e) {
      setToast({ ok: false, text: `加载失败: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="text-sm text-gray-400 p-6">加载中…</div>;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">供应商 {providers.length} 个（多数预设只需粘贴一个 API Key）</span>
        <button onClick={() => setAdding(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500">
          <Plus size={14} /> 添加供应商
        </button>
      </div>
      {toast && <div className={`text-sm px-3 py-2 rounded-lg ${toast.ok ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'}`}>{toast.text}</div>}

      {providers.length === 0 ? (
        <div className="text-sm text-gray-400 p-8 text-center border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
          还没有供应商。点「添加供应商」选择预设后粘贴 API Key 即可。
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {providers.map((p) => (
            <div key={p.id} className="rounded-xl border border-gray-200 dark:border-gray-700 p-3.5 space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-semibold truncate">{p.name}</span>
                  <Badge variant="secondary">{KIND_LABELS[p.kind] || p.kind}</Badge>
                  {!p.enabled && <Badge variant="outline">已停用</Badge>}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button title="编辑" onClick={() => setEditing(p)}
                    className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"><Pencil size={14} /></button>
                  <button title="删除" onClick={async () => {
                    if (!window.confirm(`删除供应商「${p.name}」？`)) return;
                    await agentHubApi.deleteProvider(p.id);
                    setProviders((prev) => prev.filter((x) => x.id !== p.id));
                  }} className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/30 text-red-500"><Trash2 size={14} /></button>
                </div>
              </div>
              {p.base_url && <div className="text-xs text-gray-500 truncate">{p.base_url}</div>}
              <div className="text-xs text-gray-400">Key: {p.has_api_key ? p.api_key_masked : '未配置'}
                {p.has_usage_api_key && ` · 查询Key: ${p.usage_api_key_masked}`}</div>
              {p.notes && <div className="text-xs text-gray-400 line-clamp-2">{p.notes}</div>}
            </div>
          ))}
        </div>
      )}

      {adding && (
        <ProviderModal presets={presets} onClose={() => setAdding(false)}
          onSaved={(p) => { setProviders((prev) => [p, ...prev]); setAdding(false); }} />
      )}
      {editing && (
        <ProviderModal presets={presets} existing={editing} onClose={() => setEditing(null)}
          onSaved={(p) => { setProviders((prev) => prev.map((x) => (x.id === p.id ? p : x))); setEditing(null); }} />
      )}
    </div>
  );
}

function ProviderModal({ presets, existing, onClose, onSaved }: {
  presets: AgentHubPreset[]; existing?: AgentHubProvider | null;
  onClose: () => void; onSaved: (p: AgentHubProvider) => void;
}) {
  const [kind, setKind] = useState(existing?.kind || presets[0]?.kind || 'newapi');
  const preset = presets.find((x) => x.kind === kind);
  const [name, setName] = useState(existing?.name || preset?.name || '');
  const [apiKey, setApiKey] = useState('');
  const [usageApiKey, setUsageApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(existing?.base_url || preset?.base_url || '');
  const [usageBaseUrl, setUsageBaseUrl] = useState(existing?.usage_base_url || '');
  const [notes, setNotes] = useState(existing?.notes || '');
  const [saving, setSaving] = useState(false);

  const pickPreset = (k: string) => {
    setKind(k);
    const p = presets.find((x) => x.kind === k);
    if (p) {
      if (!existing) setName(p.name);
      setBaseUrl(p.base_url || '');
    }
  };

  const save = async () => {
    if (!name.trim()) { window.alert('请填写名称'); return; }
    setSaving(true);
    try {
      const payload = {
        name: name.trim(), kind, app: existing?.app || preset?.app || 'claude',
        base_url: baseUrl.trim(), api_key: apiKey.trim(),
        usage_api_key: usageApiKey.trim(), usage_base_url: usageBaseUrl.trim(),
        category: existing?.category || preset?.category || 'third_party',
        website_url: preset?.website_url || '', notes: notes.trim(),
        enabled: existing ? existing.enabled : true,
      };
      const { provider } = existing
        ? await agentHubApi.updateProvider(existing.id, payload)
        : await agentHubApi.createProvider(payload);
      onSaved(provider);
    } catch (e) {
      window.alert(`保存失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 w-[520px] max-h-[85vh] overflow-y-auto space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{existing ? '编辑供应商' : '添加供应商'}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <label className="block text-sm">类型预设
          <select value={kind} onChange={(e) => pickPreset(e.target.value)} disabled={!!existing}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm">
            {presets.map((p) => <option key={p.kind} value={p.kind}>{p.name}</option>)}
          </select>
        </label>
        {preset?.notes && <p className="text-xs text-gray-500">{preset.notes}</p>}
        {preset?.usage_api_key_hint && (
          <p className="text-xs text-orange-600 dark:text-orange-400">⚠ {preset.usage_api_key_hint}</p>
        )}
        <label className="block text-sm">名称
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
        </label>
        {preset?.needs_api_key && (
          <>
            <label className="block text-sm">API Key {existing ? '（留空=保持不变）' : ''}
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="粘贴 API Key"
                className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
            </label>
            {(kind === 'opendesign' || kind === 'newapi') && (
              <label className="block text-sm">用量查询专用凭据{kind === 'newapi' ? '（accessToken）' : ''} {existing ? '（留空=保持不变）' : ''}
                <input type="password" value={usageApiKey} onChange={(e) => setUsageApiKey(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
              </label>
            )}
          </>
        )}
        {(kind === 'newapi' || kind === 'sub2api' || kind === 'generic_balance' || kind === 'zenmux') && (
          <label className="block text-sm">站点 base_url
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://..."
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
          </label>
        )}
        {kind === 'newapi' && (
          <label className="block text-sm">用量查询 base_url（可选，默认同站点）
            <input value={usageBaseUrl} onChange={(e) => setUsageBaseUrl(e.target.value)} placeholder="https://..."
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
          </label>
        )}
        <label className="block text-sm">备注
          <input value={notes} onChange={(e) => setNotes(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
        </label>
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600">取消</button>
          <button onClick={save} disabled={saving}
            className="px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3：Agent 切换
// ---------------------------------------------------------------------------

function AgentsTab() {
  const [agents, setAgents] = useState<AgentHubAgent[]>([]);
  const [providers, setProviders] = useState<AgentHubProvider[]>([]);
  const [toast, setToast] = useState<{ ok: boolean; text: string } | null>(null);
  const [preview, setPreview] = useState<{ agent: string; preview: SwitchPreview; providerId: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [a, p] = await Promise.all([agentHubApi.listAgents(), agentHubApi.listProviders()]);
      setAgents(a.agents);
      setProviders(p.providers);
    } catch (e) {
      setToast({ ok: false, text: `加载失败: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const doSwitch = async (agent: string, providerId: string) => {
    try {
      const { switch: sw } = await agentHubApi.switchAgent(agent, providerId);
      setToast({ ok: true, text: `${AGENT_LABELS[agent] || agent} 已切换到「${sw.provider_name}」（原配置已备份）` });
      await load();
    } catch (e) {
      setToast({ ok: false, text: `切换失败: ${(e as Error).message}` });
    }
  };

  const doPreview = async (agent: string, providerId: string) => {
    try {
      const p = await agentHubApi.previewSwitch(agent, providerId);
      setPreview({ agent, preview: p, providerId });
    } catch (e) {
      setToast({ ok: false, text: `预览失败: ${(e as Error).message}` });
    }
  };

  const doRestore = async (agent: string) => {
    if (!window.confirm(`恢复 ${AGENT_LABELS[agent] || agent} 的首次备份？当前配置将被覆盖。`)) return;
    try {
      const { restored } = await agentHubApi.restoreAgent(agent);
      setToast({ ok: true, text: `已恢复 ${restored.length} 个文件：${restored.join(', ')}` });
    } catch (e) {
      setToast({ ok: false, text: `恢复失败: ${(e as Error).message}` });
    }
  };

  if (loading) return <div className="text-sm text-gray-400 p-6">加载中…</div>;

  return (
    <div className="space-y-3">
      {toast && (
        <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg ${toast.ok ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'}`}>
          {toast.ok ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />} {toast.text}
        </div>
      )}
      <div className="text-xs text-gray-500">
        切换会改写本机 agent 的配置文件（只改请求地址/凭据等关键字段），首次写入前自动备份，可随时恢复。
      </div>
      <div className="space-y-2">
        {agents.map((a) => {
          const applicable = providers.filter((p) => p.app === a.agent);
          return (
            <div key={a.agent}
              className="flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 dark:border-gray-700 p-3">
              <span className="font-semibold w-36">{AGENT_LABELS[a.agent] || a.agent}</span>
              <Badge variant={a.configured ? 'default' : 'outline'}>
                {a.configured ? '已安装' : '未检测到配置'}
              </Badge>
              {a.current_provider_name && (
                <span className="text-xs text-gray-500">当前: {a.current_provider_name}</span>
              )}
              <div className="flex items-center gap-2 ml-auto">
                <select value={a.current_provider_id}
                  onChange={(e) => doPreview(a.agent, e.target.value)}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-2 py-1.5 text-sm min-w-[180px]">
                  <option value="">选择要切换到的供应商…</option>
                  {applicable.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <button title="恢复首次备份" onClick={() => doRestore(a.agent)}
                  className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800" disabled={!a.configured}>
                  <Undo2 size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={(e) => { if (e.target === e.currentTarget) setPreview(null); }}>
          <div className="bg-white dark:bg-gray-900 rounded-xl p-5 w-[560px] max-h-[80vh] overflow-y-auto space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">切换预览 — {AGENT_LABELS[preview.agent] || preview.agent}</h3>
              <button onClick={() => setPreview(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <div className="text-xs text-gray-500">将写入以下关键字段（其余内容不动）：</div>
            <pre className="text-xs bg-gray-50 dark:bg-gray-800 rounded-lg p-3 whitespace-pre-wrap">
              {JSON.stringify(preview.preview.floor, null, 2)}
            </pre>
            <div className="text-xs text-gray-500">涉及文件：
              {preview.preview.files.map((f) => (
                <div key={f.path} className="flex items-center gap-1">
                  <Eye size={11} /> {f.path} {f.exists ? '' : '（不存在，将报错）'} {f.backed_up ? '· 已有备份' : '· 将创建备份'}
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setPreview(null)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600">取消</button>
              <button onClick={async () => {
                await doSwitch(preview.agent, preview.providerId);
                setPreview(null);
              }} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500">
                <ArrowRightLeft size={14} /> 确认切换
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 添加订阅弹窗（含 manual 额度字段 ✅ / OpenDesign controlKey 等）
// ---------------------------------------------------------------------------

function SubscriptionModal({ onClose, onSaved }: {
  onClose: () => void;
  onSaved: (s: AgentHubSubscription) => void;
}) {
  const [presets, setPresets] = useState<AgentHubPreset[]>([]);
  const [providers, setProviders] = useState<AgentHubProvider[]>([]);
  const [kind, setKind] = useState('manual');
  const preset = presets.find((x) => x.kind === kind);
  const [name, setName] = useState('');
  const [providerId, setProviderId] = useState('');
  const [credential, setCredential] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [extraUserId, setExtraUserId] = useState('');
  const [total, setTotal] = useState('100');
  const [used, setUsed] = useState('0');
  const [unit, setUnit] = useState('credits');
  const [resetAt, setResetAt] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([agentHubApi.listPresets(), agentHubApi.listProviders()])
      .then(([p, pr]) => { setPresets(p.presets); setProviders(pr.providers.filter((x) => x.enabled)); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const p = presets.find((x) => x.kind === kind);
    if (p) setName((prev) => prev || p.name);
  }, [presets, kind]);

  const applicableProviders = providers.filter((x) => x.kind === kind);

  const save = async () => {
    if (!name.trim()) { window.alert('请填写订阅名称'); return; }
    setSaving(true);
    try {
      const extra: Record<string, unknown> = {};
      if (extraUserId.trim()) extra.userId = extraUserId.trim();
      const { subscription } = await agentHubApi.createSubscription({
        name: name.trim(), kind,
        provider_id: providerId,
        credential: credential.trim(),
        credential_source: providerId ? 'provider' : (preset?.credential_source === 'agent_file' ? 'agent_file' : 'manual'),
        agent_app: preset?.app || '',
        base_url: baseUrl.trim(),
        extra_json: JSON.stringify(extra),
        total_quota: Number(total) || 0,
        used_quota: Number(used) || 0,
        quota_unit: unit,
        window_type: kind === 'manual' ? '5h' : 'none',
        window_reset_at: resetAt.trim(),
        enabled: true,
      });
      onSaved(subscription);
    } catch (e) {
      window.alert(`创建失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white dark:bg-gray-900 rounded-xl p-5 w-[520px] max-h-[85vh] overflow-y-auto space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">添加订阅</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <label className="block text-sm">订阅类型
          <select value={kind} onChange={(e) => setKind(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm">
            {presets.map((p) => <option key={p.kind} value={p.kind}>{p.name}</option>)}
          </select>
        </label>
        {preset?.notes && <p className="text-xs text-gray-500">{preset.notes}</p>}
        {preset?.usage_api_key_hint && (
          <p className="text-xs text-orange-600 dark:text-orange-400">⚠ {preset.usage_api_key_hint}</p>
        )}
        <label className="block text-sm">订阅名称
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
        </label>
        {applicableProviders.length > 0 && (
          <label className="block text-sm">关联供应商（凭据继承）
            <select value={providerId} onChange={(e) => setProviderId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm">
              <option value="">不关联</option>
              {applicableProviders.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        )}
        {preset?.needs_api_key && (
          <label className="block text-sm">查询凭据（API Key / controlKey）
            <input type="password" value={credential} onChange={(e) => setCredential(e.target.value)} placeholder="粘贴查询凭据"
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
          </label>
        )}
        {kind === 'claude_official' && (
          <p className="text-xs text-gray-500">将自动读取本机 Claude Code 的登录凭据（无需填写）</p>
        )}
        {kind === 'codex_official' && (
          <p className="text-xs text-gray-500">将自动读取本机 Codex CLI 的登录凭据（无需填写）</p>
        )}
        {(kind === 'newapi' || kind === 'sub2api' || kind === 'generic_balance' || kind === 'zenmux' || kind === 'opendesign') && (
          <label className="block text-sm">站点 / 控制面 base_url
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder={preset?.base_url || 'https://...'}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
          </label>
        )}
        {kind === 'newapi' && (
          <label className="block text-sm">用户 ID（New-Api-User，可选）
            <input value={extraUserId} onChange={(e) => setExtraUserId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
          </label>
        )}
        {kind === 'manual' && (
          <>
            <div className="grid grid-cols-3 gap-2">
              <label className="block text-sm">总额度
                <input type="number" min={0} value={total} onChange={(e) => setTotal(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
              </label>
              <label className="block text-sm">已用量
                <input type="number" min={0} value={used} onChange={(e) => setUsed(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
              </label>
              <label className="block text-sm">单位
                <select value={unit} onChange={(e) => setUnit(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm">
                  {['credits', 'USD', 'tokens', 'requests'].map((u) => <option key={u} value={u}>{u}</option>)}
                </select>
              </label>
            </div>
            <p className="text-xs text-gray-500">额度创建后可随时「编辑额度」手动增加。</p>
          </>
        )}
        <label className="block text-sm">重置时间（ISO，可空）
          <input value={resetAt} onChange={(e) => setResetAt(e.target.value)} placeholder="2026-11-25T00:00:00Z"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-1.5 text-sm" />
        </label>
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600">取消</button>
          <button onClick={save} disabled={saving}
            className="px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">
            {saving ? '创建中…' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}

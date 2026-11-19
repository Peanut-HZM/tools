import { useCallback, useEffect, useState } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Picker, Input } from '@tarojs/components';
import {
  agentHubApi,
  AgentHubSubscription,
  AgentHubProvider,
  AgentHubPreset,
  AgentHubAgent,
} from '../../../services/agentHub';
import { formatApiError } from '../../../utils/mobileTool';
import Loading from '../../../components/Loading';
import './index.scss';

/**
 * Agent 订阅中心（移动端）— cc-switch + magpie 核心能力的小程序端。
 *
 * 与 Web 端共用同一后端 /api/agent-hub（功能不重复、数据同源）：
 * - 订阅用量仪表（进度条/倒计时/手动额度编辑）
 * - 供应商轻量管理（添加/删除）
 * - Agent 一键切换（写入本机 agent 配置文件，由后端执行）
 */

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

function barTone(usedPct: number): string {
  if (usedPct >= 90) return 'tone-danger';
  if (usedPct >= 80) return 'tone-warn';
  return 'tone-ok';
}

function fmtNum(n: number): string {
  return n >= 1000 ? n.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : String(Math.round(n * 100) / 100);
}

type SectionKey = 'usage' | 'providers' | 'agents';

const SECTIONS: { key: SectionKey; label: string }[] = [
  { key: 'usage', label: '订阅用量' },
  { key: 'providers', label: '供应商' },
  { key: 'agents', label: 'Agent 切换' },
];

export default function AgentHubPage() {
  const [section, setSection] = useState<SectionKey>('usage');
  const [subs, setSubs] = useState<AgentHubSubscription[]>([]);
  const [usageMap, setUsageMap] = useState<Record<string, Record<string, unknown>>>({});
  const [providers, setProviders] = useState<AgentHubProvider[]>([]);
  const [presets, setPresets] = useState<AgentHubPreset[]>([]);
  const [agents, setAgents] = useState<AgentHubAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editingSub, setEditingSub] = useState<AgentHubSubscription | null>(null);
  const [addingProvider, setAddingProvider] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [s, p, pr, a] = await Promise.all([
        agentHubApi.listSubscriptions(),
        agentHubApi.listProviders(),
        agentHubApi.listPresets(),
        agentHubApi.listAgents(),
      ]);
      setSubs(s.subscriptions);
      setProviders(p.providers);
      setPresets(pr.presets);
      setAgents(a.agents);
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    try {
      const { results } = await agentHubApi.queryAllUsage();
      const next: Record<string, Record<string, unknown>> = {};
      for (const r of results) next[r.id] = r;
      setUsageMap((prev) => ({ ...prev, ...next }));
      const failed = results.filter((r) => !(r as { success?: boolean }).success);
      Taro.showToast({
        title: failed.length === 0 ? `已刷新 ${results.length} 个订阅`
          : `${results.length - failed.length} 成功 / ${failed.length} 失败`,
        icon: 'none',
      });
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setRefreshing(false);
    }
  }, []);

  const refreshOne = useCallback(async (sub: AgentHubSubscription) => {
    try {
      const r = await agentHubApi.queryUsage(sub.id);
      setUsageMap((prev) => ({ ...prev, [sub.id]: r as Record<string, unknown> }));
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const displayable = subs.filter((s) => s.displayable && s.enabled);

  if (loading) return <Loading />;

  return (
    <View className='agent-hub-page'>
      <View className='section-tabs'>
        {SECTIONS.map((s) => (
          <View key={s.key}
            className={`section-tab ${section === s.key ? 'active' : ''}`}
            onClick={() => setSection(s.key)}>
            <Text>{s.label}</Text>
          </View>
        ))}
      </View>

      {section === 'usage' && (
        <View className='section-body'>
          <View className='meta-row'>
            <Text className='meta-text'>已启用 {displayable.length} 个（未配置不显示）</Text>
            <View className={`btn ${refreshing ? 'disabled' : ''}`} onClick={() => { if (!refreshing) refreshAll(); }}>
              <Text>{refreshing ? '刷新中…' : '全部刷新'}</Text>
            </View>
          </View>
          {displayable.length === 0 ? (
            <View className='empty-card'><Text>暂无已启用订阅。可在下方添加手动额度订阅。</Text></View>
          ) : (
            displayable.map((sub) => (
              <SubCard key={sub.id} sub={sub}
                usage={usageMap[sub.id] || sub.last_query || undefined}
                onRefresh={() => refreshOne(sub)}
                onEdit={() => setEditingSub(sub)}
                onDelete={async () => {
                  const { confirm } = await Taro.showModal({ title: '删除订阅', content: `删除「${sub.name}」？` });
                  if (!confirm) return;
                  await agentHubApi.deleteSubscription(sub.id);
                  setSubs((prev) => prev.filter((x) => x.id !== sub.id));
                  Taro.showToast({ title: '已删除', icon: 'none' });
                }} />
            ))
          )}
          <AddSubscriptionInline presets={presets} providers={providers}
            onCreated={(created) => { setSubs((prev) => [created, ...prev]); }} />
        </View>
      )}

      {section === 'providers' && (
        <View className='section-body'>
          <AddProviderInline presets={presets}
            onCreated={(p) => setProviders((prev) => [p, ...prev])} />
          {providers.map((p) => (
            <View key={p.id} className='glass-card provider-card'>
              <View className='card-head'>
                <Text className='card-title'>{p.name}</Text>
                <Text className='kind-badge'>{KIND_LABELS[p.kind] || p.kind}</Text>
              </View>
              <Text className='muted small'>{p.base_url || '—'}</Text>
              <Text className='muted small'>Key: {p.has_api_key ? p.api_key_masked : '未配置'}</Text>
              <View className='btn btn-danger' onClick={async () => {
                const { confirm } = await Taro.showModal({ title: '删除供应商', content: `删除「${p.name}」？` });
                if (!confirm) return;
                await agentHubApi.deleteProvider(p.id);
                setProviders((prev) => prev.filter((x) => x.id !== p.id));
                Taro.showToast({ title: '已删除', icon: 'none' });
              }}><Text>删除</Text></View>
            </View>
          ))}
        </View>
      )}

      {section === 'agents' && (
        <View className='section-body'>
          <View className='hint-card'><Text>切换将写入本机 agent 的配置文件（由后端执行），首次写入前自动备份。</Text></View>
          {agents.map((a) => {
            const applicable = providers.filter((p) => p.app === a.agent);
            return (
              <View key={a.agent} className='glass-card agent-card'>
                <View className='card-head'>
                  <Text className='card-title'>{AGENT_LABELS[a.agent] || a.agent}</Text>
                  <Text className={`kind-badge ${a.configured ? '' : 'badge-off'}`}>
                    {a.configured ? '已安装' : '未检测到'}
                  </Text>
                </View>
                <Text className='muted small'>
                  当前: {a.current_provider_name || '未设置'}
                </Text>
                {applicable.length > 0 ? (
                  <Picker mode='selector' range={applicable.map((p) => p.name)}
                    onChange={async (e) => {
                      const idx = Number(e.detail.value);
                      const target = applicable[idx];
                      if (!target) return;
                      try {
                        await agentHubApi.switchAgent(a.agent, target.id);
                        Taro.showToast({ title: `已切换到「${target.name}」`, icon: 'none' });
                        await loadAll();
                      } catch (err) {
                        Taro.showToast({ title: formatApiError(err), icon: 'none' });
                      }
                    }}>
                    <View className='btn'><Text>选择供应商并切换</Text></View>
                  </Picker>
                ) : (
                  <Text className='muted small'>暂无适用于该 Agent 的供应商（先在供应商页按对应应用添加）</Text>
                )}
              </View>
            );
          })}
        </View>
      )}

      {editingSub && (
        <QuotaEditLayer sub={editingSub}
          onClose={() => setEditingSub(null)}
          onSaved={(updated) => {
            setSubs((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
            setEditingSub(null);
            if (updated.kind === 'manual') refreshOne(updated);
          }} />
      )}
      {addingProvider && (
        <AddProviderLayer presets={presets}
          onClose={() => setAddingProvider(false)}
          onSaved={(p) => { setProviders((prev) => [p, ...prev]); setAddingProvider(false); }} />
      )}
    </View>
  );
}

function SubCard({ sub, usage, onRefresh, onEdit, onDelete }: {
  sub: AgentHubSubscription;
  usage?: Record<string, unknown>;
  onRefresh: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const u = usage as { success?: boolean; plan_name?: string;
    tiers?: { name: string; used: number; total: number; unit: string; resets_at?: string }[];
    balance?: { value: number; unit: string }; error?: string; queried_at?: string } | undefined;
  const tiers = u && u.success && u.tiers ? u.tiers.slice(0, 4) : [];
  return (
    <View className='glass-card sub-card'>
      <View className='card-head'>
        <Text className='card-title'>{sub.name}</Text>
        <Text className='kind-badge'>{KIND_LABELS[sub.kind] || sub.kind}</Text>
      </View>
      {u?.plan_name ? <Text className='muted small'>套餐: {u.plan_name}</Text> : null}
      {tiers.length > 0 ? (
        tiers.map((t, idx) => {
          const pct = t.total > 0 ? (t.used / t.total) * 100 : 0;
          return (
            <View key={idx} className='tier-block'>
              <View className='tier-row'>
                <Text className='tier-name'>{t.name}</Text>
                <Text className='tier-value'>
                  {t.unit === 'percent' ? `${fmtNum(t.used)}%`
                    : `${fmtNum(t.used)} / ${fmtNum(t.total)} ${t.unit}`}
                  {countdown(t.resets_at) ? ` · ${countdown(t.resets_at)}` : ''}
                </Text>
              </View>
              <View className='bar-track'>
                <View className={`bar-fill ${barTone(pct)}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
              </View>
            </View>
          );
        })
      ) : u?.balance ? (
        <Text className={`balance ${u.balance.value <= 0 ? 'balance-zero' : ''}`}>
          余额: {fmtNum(u.balance.value)} {u.balance.unit}
        </Text>
      ) : u && u.success === false ? (
        <Text className='error-text'>{u.error}</Text>
      ) : (
        <Text className='muted small'>尚未查询（点刷新或等待轮询）</Text>
      )}
      {u?.queried_at ? <Text className='tiny'>上次查询: {new Date(u.queried_at).toLocaleString()}</Text> : null}
      {sub.kind === 'manual' ? <Text className='tiny'>手动模式：可随时「编辑额度」增加</Text> : null}
      <View className='card-actions'>
        <View className='btn' onClick={onEdit}><Text>编辑额度</Text></View>
        <View className='btn' onClick={onRefresh}><Text>刷新</Text></View>
        <View className='btn btn-danger' onClick={onDelete}><Text>删除</Text></View>
      </View>
    </View>
  );
}

function QuotaEditLayer({ sub, onClose, onSaved }: {
  sub: AgentHubSubscription; onClose: () => void;
  onSaved: (s: AgentHubSubscription) => void;
}) {
  const isManual = sub.kind === 'manual';
  const [total, setTotal] = useState(String(sub.total_quota));
  const [used, setUsed] = useState(String(sub.used_quota));
  const [unit, setUnit] = useState(sub.quota_unit);
  const [resetAt, setResetAt] = useState(sub.window_reset_at);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { quota_unit: unit, window_reset_at: resetAt };
      if (isManual) {
        payload.total_quota = Number(total) || 0;
        payload.used_quota = Number(used) || 0;
      }
      const { subscription } = await agentHubApi.adjustQuota(sub.id, payload);
      onSaved(subscription);
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <View className='layer-mask' onClick={onClose}>
      <View className='layer-card' onClick={(e) => e.stopPropagation()}>
        <Text className='layer-title'>编辑额度 — {sub.name}</Text>
        {isManual ? (
          <>
            <Text className='field-label'>总额度（可手动增加）</Text>
            <Input type='digit' value={total} onInput={(e) => setTotal(e.detail.value)} className='layer-input' />
            <Text className='field-label'>已用量</Text>
            <Input type='digit' value={used} onInput={(e) => setUsed(e.detail.value)} className='layer-input' />
          </>
        ) : (
          <Text className='muted small'>该订阅由 API 自动查询，此处仅调整单位与重置时间。</Text>
        )}
        <Text className='field-label'>单位</Text>
        <Picker mode='selector' range={['credits', 'USD', 'tokens', 'requests', 'percent']}
          value={['credits', 'USD', 'tokens', 'requests', 'percent'].indexOf(unit)}
          onChange={(e) => setUnit(['credits', 'USD', 'tokens', 'requests', 'percent'][Number(e.detail.value)])}>
          <View className='layer-input'><Text>{unit}</Text></View>
        </Picker>
        <Text className='field-label'>重置时间（ISO，可空）</Text>
        <Input value={resetAt} onInput={(e) => setResetAt(e.detail.value)} placeholder='2026-11-25T00:00:00Z' className='layer-input' />
        <View className='layer-actions'>
          <View className='btn' onClick={onClose}><Text>取消</Text></View>
          <View className={`btn btn-primary ${saving ? 'disabled' : ''}`} onClick={() => { if (!saving) save(); }}>
            <Text>{saving ? '保存中…' : '保存'}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

function AddProviderInline({ presets, onCreated }: {
  presets: AgentHubPreset[];
  onCreated: (p: AgentHubProvider) => void;
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('');
  const preset = presets.find((x) => x.kind === kind);
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [usageApiKey, setUsageApiKey] = useState('');
  const [saving, setSaving] = useState(false);

  const pick = (k: string) => {
    setKind(k);
    const p = presets.find((x) => x.kind === k);
    if (p) { setName(p.name); setBaseUrl(p.base_url || ''); }
  };

  const save = async () => {
    if (!name.trim()) { Taro.showToast({ title: '请填写名称', icon: 'none' }); return; }
    setSaving(true);
    try {
      const { provider } = await agentHubApi.createProvider({
        name: name.trim(), kind, app: preset?.app || 'claude',
        base_url: baseUrl.trim(), api_key: apiKey.trim(),
        usage_api_key: usageApiKey.trim(),
        category: preset?.category || 'third_party',
        website_url: preset?.website_url || '', notes: '',
        enabled: true,
      });
      onCreated(provider);
      setOpen(false); setKind(''); setName(''); setApiKey(''); setBaseUrl(''); setUsageApiKey('');
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <View className='btn btn-primary add-btn' onClick={() => setOpen(true)}><Text>+ 添加供应商</Text></View>
    );
  }
  return (
    <View className='glass-card add-card'>
      <Text className='card-title'>添加供应商</Text>
      {preset?.usage_api_key_hint ? <Text className='tiny warn'>{preset.usage_api_key_hint}</Text> : null}
      <Text className='field-label'>类型预设</Text>
      <Picker mode='selector' range={presets.map((p) => p.name)}
        onChange={(e) => pick(presets[Number(e.detail.value)].kind)}>
        <View className='layer-input'><Text>{preset ? preset.name : '选择预设'}</Text></View>
      </Picker>
      <Text className='field-label'>名称</Text>
      <Input value={name} onInput={(e) => setName(e.detail.value)} className='layer-input' />
      {preset?.needs_api_key ? (
        <>
          <Text className='field-label'>API Key</Text>
          <Input password value={apiKey} onInput={(e) => setApiKey(e.detail.value)} placeholder='粘贴 API Key' className='layer-input' />
          {(kind === 'opendesign' || kind === 'newapi') ? (
            <>
              <Text className='field-label'>用量查询专用凭据</Text>
              <Input password value={usageApiKey} onInput={(e) => setUsageApiKey(e.detail.value)} className='layer-input' />
            </>
          ) : null}
        </>
      ) : null}
      {(kind === 'newapi' || kind === 'sub2api' || kind === 'generic_balance' || kind === 'zenmux') ? (
        <>
          <Text className='field-label'>站点 base_url</Text>
          <Input value={baseUrl} onInput={(e) => setBaseUrl(e.detail.value)} placeholder='https://...' className='layer-input' />
        </>
      ) : null}
      <View className='layer-actions'>
        <View className='btn' onClick={() => setOpen(false)}><Text>取消</Text></View>
        <View className={`btn btn-primary ${saving ? 'disabled' : ''}`} onClick={() => { if (!saving) save(); }}>
          <Text>{saving ? '保存中…' : '保存'}</Text>
        </View>
      </View>
    </View>
  );
}

function AddProviderLayer({ presets, onClose, onSaved }: {
  presets: AgentHubPreset[]; onClose: () => void;
  onSaved: (p: AgentHubProvider) => void;
}) {
  return (
    <View className='layer-mask' onClick={onClose}>
      <View className='layer-card' onClick={(e) => e.stopPropagation()}>
        <Text className='layer-title'>添加供应商（见「供应商」分区）</Text>
        <View className='layer-actions'><View className='btn' onClick={onClose}><Text>知道了</Text></View></View>
      </View>
    </View>
  );
}

function AddSubscriptionInline({ presets, providers, onCreated }: {
  presets: AgentHubPreset[];
  providers: AgentHubProvider[];
  onCreated: (s: AgentHubSubscription) => void;
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('manual');
  const preset = presets.find((x) => x.kind === kind);
  const [name, setName] = useState('');
  const [credential, setCredential] = useState('');
  const [total, setTotal] = useState('100');
  const [used, setUsed] = useState('0');
  const [unit, setUnit] = useState('credits');
  const [saving, setSaving] = useState(false);

  const pick = (k: string) => {
    setKind(k);
    const p = presets.find((x) => x.kind === k);
    if (p) setName(p.name);
  };

  const save = async () => {
    if (!name.trim()) { Taro.showToast({ title: '请填写订阅名称', icon: 'none' }); return; }
    setSaving(true);
    try {
      const { subscription } = await agentHubApi.createSubscription({
        name: name.trim(), kind,
        provider_id: '',
        credential: credential.trim(),
        credential_source: preset?.needs_api_key ? 'manual' : (preset?.credential_source === 'agent_file' ? 'agent_file' : 'manual'),
        agent_app: preset?.app || '',
        base_url: preset?.base_url || '',
        extra_json: '{}',
        total_quota: Number(total) || 0,
        used_quota: Number(used) || 0,
        quota_unit: unit,
        window_type: kind === 'manual' ? '5h' : 'none',
        window_reset_at: '',
        enabled: true,
      });
      onCreated(subscription);
      setOpen(false); setName(''); setCredential('');
    } catch (e) {
      Taro.showToast({ title: formatApiError(e), icon: 'none' });
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <View className='btn btn-primary add-btn' onClick={() => setOpen(true)}><Text>+ 添加订阅</Text></View>
    );
  }
  return (
    <View className='glass-card add-card'>
      <Text className='card-title'>添加订阅</Text>
      {preset?.notes ? <Text className='tiny'>{preset.notes}</Text> : null}
      {preset?.usage_api_key_hint ? <Text className='tiny warn'>{preset.usage_api_key_hint}</Text> : null}
      <Text className='field-label'>订阅类型</Text>
      <Picker mode='selector' range={presets.map((p) => p.name)}
        onChange={(e) => pick(presets[Number(e.detail.value)].kind)}>
        <View className='layer-input'><Text>{preset ? preset.name : '选择类型'}</Text></View>
      </Picker>
      <Text className='field-label'>订阅名称</Text>
      <Input value={name} onInput={(e) => setName(e.detail.value)} className='layer-input' />
      {preset?.needs_api_key ? (
        <>
          <Text className='field-label'>查询凭据（API Key / controlKey）</Text>
          <Input password value={credential} onInput={(e) => setCredential(e.detail.value)} className='layer-input' />
        </>
      ) : null}
      {kind === 'claude_official' || kind === 'codex_official' ? (
        <Text className='tiny'>将自动读取本机该 Agent 的登录凭据（无需填写）</Text>
      ) : null}
      {kind === 'manual' ? (
        <>
          <Text className='field-label'>总额度</Text>
          <Input type='digit' value={total} onInput={(e) => setTotal(e.detail.value)} className='layer-input' />
          <Text className='field-label'>已用量</Text>
          <Input type='digit' value={used} onInput={(e) => setUsed(e.detail.value)} className='layer-input' />
          <Text className='field-label'>单位</Text>
          <Picker mode='selector' range={['credits', 'USD', 'tokens', 'requests']}
            onChange={(e) => setUnit(['credits', 'USD', 'tokens', 'requests'][Number(e.detail.value)])}>
            <View className='layer-input'><Text>{unit}</Text></View>
          </Picker>
        </>
      ) : null}
      <View className='layer-actions'>
        <View className='btn' onClick={() => setOpen(false)}><Text>取消</Text></View>
        <View className={`btn btn-primary ${saving ? 'disabled' : ''}`} onClick={() => { if (!saving) save(); }}>
          <Text>{saving ? '创建中…' : '创建'}</Text>
        </View>
      </View>
    </View>
  );
}

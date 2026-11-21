// Agent 切换：卡片式流式布局（只列已安装；未安装的在「添加 Agent」弹窗里可选）
// 真实有效性：当前供应商来自后端解析真实配置文件（不是我们的切换记录），
// 切换后后端会回读校验，verified=false 时明确显示失败。
import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRightLeft,
  CheckCircle2,
  FileCode,
  Lock,
  Plus,
  RefreshCw,
  Undo2,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import * as quotaApi from '../../../api/subscriptionQuotaApi';
import type {
  AgentCatalogItemDto,
  AgentSwitchStatusDto,
  QuotaAccountDto,
  SwitchPreviewDto,
} from '../../../api/subscriptionQuotaApi';

interface AgentSwitchPanelProps {
  accounts: QuotaAccountDto[];
}

const KIND_LABEL: Record<string, string> = { cli: 'CLI', desktop: '桌面端' };

/** 这些 agent 的写入必须带模型名，否则不会真正生效 */
const MODEL_REQUIRED = new Set(['opencode', 'minimax']);

export function AgentSwitchPanel({ accounts }: AgentSwitchPanelProps) {
  const [agents, setAgents] = useState<AgentSwitchStatusDto[]>([]);
  const [available, setAvailable] = useState<AgentCatalogItemDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [showAdd, setShowAdd] = useState(false);
  const [target, setTarget] = useState<AgentSwitchStatusDto | null>(null);
  const [accountId, setAccountId] = useState('');
  const [model, setModel] = useState('');
  const [preview, setPreview] = useState<SwitchPreviewDto | null>(null);
  const [verifyResult, setVerifyResult] = useState<{ verified: boolean; message: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await quotaApi.listAgents();
      setAgents(data.agents ?? []);
      setAvailable(data.available ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '读取 agent 配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const usableAccounts = accounts.filter((a) => a.hasKey && !a.isManual);

  const openSwitch = (agent: AgentSwitchStatusDto) => {
    setTarget(agent);
    setPreview(null);
    setVerifyResult(null);
    setModel(agent.current?.model ?? '');
    const matchedId = agent.currentAccount?.accountId;
    setAccountId(matchedId && usableAccounts.some((a) => a.id === matchedId) ? matchedId : usableAccounts[0]?.id ?? '');
  };

  const handlePreview = async () => {
    if (!target || !accountId) return;
    setBusy(target.agent);
    setError(null);
    try {
      setPreview(await quotaApi.previewAgentSwitch(target.agent, accountId, model));
    } catch (err) {
      setError(err instanceof Error ? err.message : '预览失败');
    } finally {
      setBusy(null);
    }
  };

  const handleSwitch = async () => {
    if (!target || !accountId) return;
    setBusy(target.agent);
    setError(null);
    setNotice(null);
    try {
      const result = await quotaApi.switchAgent(target.agent, accountId, model);
      const account = accounts.find((a) => a.id === accountId);
      const label = account?.label ?? result.providerName;
      if (result.verified) {
        setVerifyResult({ verified: true, message: `已切换到「${label}」，回读校验通过` });
        setNotice(`已把 ${target.name} 切换到「${label}」（写入 ${result.written.length} 个文件，校验通过）`);
      } else {
        const reason = result.current?.error || '配置文件里读不到刚写入的 Key/地址';
        setVerifyResult({ verified: false, message: `写入完成但校验未通过：${reason}` });
        setNotice(null);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : '切换失败');
    } finally {
      setBusy(null);
    }
  };

  const handleRestore = async (agent: AgentSwitchStatusDto) => {
    if (!window.confirm(`恢复 ${agent.name} 的原始配置备份？`)) return;
    setBusy(agent.agent);
    setError(null);
    setNotice(null);
    try {
      const result = await quotaApi.restoreAgent(agent.agent);
      setNotice(result.restored.length > 0 ? `已恢复 ${result.restored.length} 个文件` : '没有可恢复的备份（可能从未切换过）');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : '恢复失败');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
            <ArrowRightLeft className="h-4 w-4" aria-hidden />
            已安装的 Agent
          </h3>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-faint">
            只列出本机已安装的 agent；「当前」来自<b>真实配置文件解析</b>，切换后会回读校验，校验不通过不会显示成功。
            <br />
            <span className="text-accent-warning">会改写配置文件</span>：首次写入前自动备份，可随时「恢复备份」。
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowAdd(true)}>
            <Plus className="h-4 w-4" />
            添加 Agent
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-accent-danger">{error}</div>
      )}
      {notice && (
        <div className="rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-xs text-accent-success">{notice}</div>
      )}
      {usableAccounts.length === 0 && (
        <p className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-accent-warning">
          还没有可写入的供应商账号（先在「供应商」页添加并填入 API Key）
        </p>
      )}

      {loading && agents.length === 0 ? (
        <div className="rounded-xl border border-border bg-surface-1 p-4 text-sm text-ink-muted">
          正在解析本机 agent 配置…
        </div>
      ) : agents.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border py-10 text-center text-sm text-ink-muted">
          本机未检测到已安装的 agent。装好后点「刷新」，或从「添加 Agent」查看支持的清单。
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {agents.map((agent) => {
            const current = agent.current;
            const label = agent.currentAccount?.label;
            return (
              <div key={agent.agent} className="flex flex-col gap-2 rounded-xl border border-border bg-surface-1 p-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{agent.name}</span>
                  <Badge variant="outline">{KIND_LABEL[agent.kind] ?? agent.kind}</Badge>
                  {agent.writable ? (
                    <Badge variant="tint-success" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" aria-hidden />
                      可切换
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="gap-1">
                      <Lock className="h-3 w-3" aria-hidden />
                      仅检测
                    </Badge>
                  )}
                </div>

                <div className="flex flex-col gap-0.5 text-xs">
                  <span className="text-ink-muted">
                    当前：
                    {label ? (
                      <span className="text-accent-success">{label}</span>
                    ) : current?.hasKey ? (
                      <span className="text-accent-warning">自定义配置（不匹配任何订阅账号）</span>
                    ) : (
                      <span className="text-ink-faint">未配置</span>
                    )}
                  </span>
                  {current?.baseUrl && <span className="break-all font-mono text-[11px] text-ink-faint">{current.baseUrl}</span>}
                  {current?.model && <span className="text-[11px] text-ink-faint">模型：{current.model}</span>}
                  {current?.error && <span className="text-[11px] text-ink-faint">{current.error}</span>}
                </div>

                {!agent.writable && agent.readonlyReason && (
                  <p className="rounded bg-surface-2 px-2 py-1 text-[11px] text-ink-faint">{agent.readonlyReason}</p>
                )}

                <div className="flex flex-wrap gap-1">
                  <Button
                    size="sm"
                    disabled={!agent.writable || usableAccounts.length === 0 || busy === agent.agent}
                    onClick={() => openSwitch(agent)}
                  >
                    切换
                  </Button>
                  <Button variant="outline" size="sm" disabled={busy === agent.agent} onClick={() => void handleRestore(agent)}>
                    <Undo2 className="h-3.5 w-3.5" />
                    恢复备份
                  </Button>
                  <details className="w-full">
                    <summary className="cursor-pointer text-[11px] text-ink-faint">配置文件（{agent.files.filter((f) => f.exists).length}/{agent.files.length} 存在）</summary>
                    <div className="mt-1 flex flex-col gap-0.5">
                      {agent.files.map((file) => (
                        <span key={file.path} className="flex items-center gap-1 break-all font-mono text-[10px] text-ink-faint">
                          <FileCode className="h-3 w-3 shrink-0" aria-hidden />
                          {file.path}
                          {!file.exists && <span className="text-accent-warning">（不存在）</span>}
                        </span>
                      ))}
                    </div>
                  </details>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 添加 Agent 弹窗：只列未安装的 */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div role="dialog" aria-modal="true" aria-label="添加 Agent"
            className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-xl border border-border bg-surface-1 p-4 shadow-xl sm:rounded-xl">
            <h3 className="mb-1 text-base font-semibold text-ink">添加 Agent</h3>
            <p className="mb-3 text-xs text-ink-faint">
              下面是本机<b>未检测到</b>的 agent。安装后回到本页点「刷新」即会出现在上面；这里只列出可选项与检测依据。
            </p>
            {available.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border py-6 text-center text-sm text-ink-muted">
                所有支持的 agent 都已安装
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {available.map((item) => (
                  <li key={item.agent} className="rounded-lg border border-border p-2.5 text-xs">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-medium text-ink">{item.name}</span>
                      <Badge variant="outline">{KIND_LABEL[item.kind] ?? item.kind}</Badge>
                      {!item.writable && <Badge variant="outline">仅检测</Badge>}
                    </div>
                    {item.hint && <p className="mt-1 text-[11px] text-ink-faint">{item.hint}</p>}
                    <p className="mt-1 break-all font-mono text-[10px] text-ink-faint">检测路径：{item.files.join(' , ')}</p>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>关闭</Button>
            </div>
          </div>
        </div>
      )}

      {/* 切换弹窗 */}
      {target && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div role="dialog" aria-modal="true" aria-label="切换供应商"
            className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-xl border border-border bg-surface-1 p-4 shadow-xl sm:rounded-xl sm:p-5">
            <h3 className="mb-1 text-base font-semibold text-ink">切换：{target.name}</h3>
            <p className="mb-3 text-xs text-ink-faint">选择要写入的订阅账号；确认后立即回读校验。</p>

            <label className="mb-3 flex flex-col gap-1 text-xs text-ink-muted">
              订阅账号
              <select
                value={accountId}
                onChange={(e) => { setAccountId(e.target.value); setPreview(null); setVerifyResult(null); }}
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              >
                {usableAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.label}（{account.maskedKey || '无 Key'}）
                  </option>
                ))}
              </select>
            </label>

            <label className="mb-1 flex flex-col gap-1 text-xs text-ink-muted">
              模型{MODEL_REQUIRED.has(target.agent) ? '（必填，否则切换不生效）' : '（可选）'}
              <input
                value={model}
                onChange={(e) => { setModel(e.target.value); setPreview(null); }}
                placeholder={target.agent === 'opencode' ? '例如 k3 或 claude-sonnet-4-5' : '留空表示不改模型字段'}
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              />
            </label>
            {MODEL_REQUIRED.has(target.agent) && (
              <p className="mb-2 text-[11px] text-ink-faint">
                {target.name} 只有同时指定模型才会真正生效（会写成 <code>model=&lt;provider&gt;/&lt;model&gt;</code>）
              </p>
            )}

            {preview && (
              <div className="mb-3 rounded-lg bg-surface-2 px-3 py-2">
                <div className="mb-1 text-[11px] text-ink-muted">将写入的字段（dry-run）</div>
                {Object.entries(preview.floor).map(([key, value]) => (
                  <div key={key} className="flex flex-wrap gap-1 text-[11px]">
                    <span className="font-mono text-ink-muted">{key}</span>
                    <span className="text-ink-faint">=</span>
                    <span className="min-w-0 break-all font-mono text-ink">{value}</span>
                  </div>
                ))}
              </div>
            )}

            {verifyResult && (
              <div className={`mb-3 rounded-lg border px-3 py-2 text-xs ${verifyResult.verified ? 'border-success/30 bg-success/10 text-accent-success' : 'border-danger/30 bg-danger/10 text-accent-danger'}`}>
                {verifyResult.verified ? <CheckCircle2 className="mr-1 inline h-3.5 w-3.5" aria-hidden /> : <AlertTriangle className="mr-1 inline h-3.5 w-3.5" aria-hidden />}
                {verifyResult.message}
              </div>
            )}

            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => void handlePreview()} disabled={busy === target.agent || !accountId}>
                预览
              </Button>
              <Button variant="outline" size="sm" onClick={() => { setTarget(null); setPreview(null); setVerifyResult(null); }}>
                关闭
              </Button>
              <Button size="sm" onClick={() => void handleSwitch()} disabled={busy === target.agent || !accountId}>
                {busy === target.agent ? '执行中…' : '确认切换'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
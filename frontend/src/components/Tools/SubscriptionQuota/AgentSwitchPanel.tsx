import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRightLeft,
  CheckCircle2,
  FileCode,
  RefreshCw,
  Undo2,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import * as quotaApi from '../../../api/subscriptionQuotaApi';
import type {
  AgentSwitchStatusDto,
  QuotaAccountDto,
  SwitchPreviewDto,
} from '../../../api/subscriptionQuotaApi';

const AGENT_LABELS: Record<string, string> = {
  claude: 'Claude Code',
  codex: 'Codex CLI',
  gemini: 'Gemini CLI',
  kimi: 'Kimi Code',
  opencode: 'OpenCode',
  minimax: 'MiniMax Code',
};

interface AgentSwitchPanelProps {
  accounts: QuotaAccountDto[];
}

/** Agent 切换面板（合并 agent-hub：把选中的供应商写进本机 CLI 配置） */
export function AgentSwitchPanel({ accounts }: AgentSwitchPanelProps) {
  const [agents, setAgents] = useState<AgentSwitchStatusDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [preview, setPreview] = useState<SwitchPreviewDto | null>(null);
  const [picking, setPicking] = useState<string | null>(null);
  const [model, setModel] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await quotaApi.listAgents();
      setAgents(data.agents ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '读取 agent 配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const hasKeyAccounts = accounts.filter((a) => a.hasKey && !a.isManual);

  const handlePreview = useCallback(async (agent: string, accountId: string) => {
    setBusy(agent);
    setError(null);
    try {
      const data = await quotaApi.previewAgentSwitch(agent, accountId, model);
      setPreview(data);
      setPicking(agent);
    } catch (err) {
      setError(err instanceof Error ? err.message : '预览失败');
    } finally {
      setBusy(null);
    }
  }, [model]);

  const handleSwitch = useCallback(
    async (agent: string, accountId: string) => {
      setBusy(agent);
      setError(null);
      setNotice(null);
      try {
        const result = await quotaApi.switchAgent(agent, accountId, model);
        setNotice(
          `已把 ${AGENT_LABELS[agent] ?? agent} 切换到「${result.providerName}」，写入 ${result.written.length} 个文件`
        );
        setPreview(null);
        setPicking(null);
        await load();
      } catch (err) {
        setError(err instanceof Error ? err.message : '切换失败');
      } finally {
        setBusy(null);
      }
    },
    [model, load]
  );

  const handleRestore = useCallback(
    async (agent: string) => {
      if (!window.confirm(`恢复 ${AGENT_LABELS[agent] ?? agent} 的原始配置备份？`)) return;
      setBusy(agent);
      setError(null);
      setNotice(null);
      try {
        const result = await quotaApi.restoreAgent(agent);
        setNotice(
          result.restored.length > 0
            ? `已恢复 ${result.restored.length} 个文件`
            : '没有可恢复的备份（可能从未切换过）'
        );
        await load();
      } catch (err) {
        setError(err instanceof Error ? err.message : '恢复失败');
      } finally {
        setBusy(null);
      }
    },
    [load]
  );

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-4 text-sm text-ink-muted">
        正在读取本机 agent 配置…
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface-1 p-3 sm:p-4">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
            <ArrowRightLeft className="h-4 w-4" aria-hidden />
            Agent 切换
          </h3>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-faint">
            把选中的供应商写进本机 CLI 配置，让该 agent 直接使用它。
            <br />
            <span className="text-accent-warning">会改写配置文件</span> ：
            首次写入前自动备份，可随时「恢复备份」还原到最初状态。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          aria-label="刷新 agent 状态"
          className="shrink-0 rounded-md p-1.5 text-ink-muted hover:bg-surface-2 hover:text-ink disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden />
        </button>
      </div>

      {error && (
        <div className="mb-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-accent-danger">
          {error}
        </div>
      )}
      {notice && (
        <div className="mb-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-xs text-accent-success">
          {notice}
        </div>
      )}

      {hasKeyAccounts.length === 0 && (
        <p className="mb-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-accent-warning">
          还没有可写入的供应商账号（需要先「添加供应商」并填入 API Key）
        </p>
      )}

      <div className="flex flex-col gap-2">
        {agents.map((item) => (
          <div
            key={item.agent}
            className="rounded-lg border border-border p-2.5 sm:p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-ink">
                {AGENT_LABELS[item.agent] ?? item.agent}
              </span>
              {item.configured ? (
                <Badge variant="tint-success" className="gap-1">
                  <CheckCircle2 className="h-3 w-3" aria-hidden />
                  已安装
                </Badge>
              ) : (
                <Badge variant="outline">未检测到</Badge>
              )}
              {item.currentProviderName && (
                <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-muted">
                  当前：{item.currentProviderName}
                </span>
              )}
            </div>

            <div className="mt-1 flex flex-col gap-0.5">
              {item.files.map((file) => (
                <span
                  key={file.path}
                  className="flex items-center gap-1 break-all font-mono text-[11px] text-ink-faint"
                >
                  <FileCode className="h-3 w-3 shrink-0" aria-hidden />
                  {file.path}
                  {!file.exists && <span className="text-accent-warning">（不存在）</span>}
                </span>
              ))}
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select
                aria-label={`为 ${AGENT_LABELS[item.agent] ?? item.agent} 选择供应商`}
                value=""
                disabled={busy === item.agent || hasKeyAccounts.length === 0}
                onChange={(event) => {
                  const accountId = event.target.value;
                  if (accountId) void handlePreview(item.agent, accountId);
                }}
                className="min-w-0 flex-1 rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-xs text-ink disabled:opacity-50 sm:flex-none"
              >
                <option value="">选择供应商…</option>
                {hasKeyAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void handleRestore(item.agent)}
                disabled={busy === item.agent}
                className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-ink hover:bg-surface-2 disabled:opacity-50"
              >
                <Undo2 className="h-3.5 w-3.5" aria-hidden />
                恢复备份
              </button>
              {busy === item.agent && (
                <RefreshCw className="h-4 w-4 animate-spin text-ink-muted" aria-hidden />
              )}
            </div>
          </div>
        ))}
      </div>

      {preview && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-label="切换预览"
            className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-xl border border-border bg-surface-1 p-4 shadow-xl sm:rounded-xl sm:p-5"
          >
            <h3 className="mb-1 text-base font-semibold text-ink">
              预览：{AGENT_LABELS[preview.agent] ?? preview.agent}
            </h3>
            <p className="mb-3 text-xs text-ink-faint">
              下面是将要写入的关键字段（dry-run，尚未落盘）
            </p>

            <div className="mb-3 flex flex-col gap-1">
              {preview.files.map((file) => (
                <div key={file.path} className="flex flex-wrap items-center gap-1.5 text-xs">
                  <FileCode className="h-3 w-3 shrink-0 text-ink-faint" aria-hidden />
                  <span className="min-w-0 break-all font-mono text-ink-muted">{file.path}</span>
                  {file.backed_up && (
                    <span className="rounded-full bg-success/15 px-1.5 py-0.5 text-[10px] text-accent-success">
                      已备份
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div className="mb-3 rounded-lg bg-surface-2 px-3 py-2">
              {Object.entries(preview.floor).map(([key, value]) => (
                <div key={key} className="flex flex-wrap gap-1 text-[11px]">
                  <span className="font-mono text-ink-muted">{key}</span>
                  <span className="text-ink-faint">=</span>
                  <span className="min-w-0 break-all font-mono text-ink">{value}</span>
                </div>
              ))}
            </div>

            <label className="mb-3 flex flex-col gap-1 text-xs text-ink-muted">
              模型（可选，留空表示不改模型字段）
              <input
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder="例如 claude-opus-5.0"
                className="rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm text-ink"
              />
            </label>

            <div className="flex items-start gap-1.5 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-accent-warning">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              确认后会立即改写上面的配置文件。首次写入前会自动备份，可用「恢复备份」还原。
            </div>

            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setPreview(null);
                  setPicking(null);
                }}
                className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink hover:bg-surface-2"
              >
                取消
              </button>
              <button
                type="button"
                disabled={!picking || busy === preview.agent}
                onClick={() => {
                  const accountId = document.querySelector<HTMLSelectElement>(
                    `select[aria-label="为 ${AGENT_LABELS[preview.agent] ?? preview.agent} 选择供应商"]`
                  )?.value;
                  if (accountId) void handleSwitch(preview.agent, accountId);
                }}
                className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
              >
                确认切换
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

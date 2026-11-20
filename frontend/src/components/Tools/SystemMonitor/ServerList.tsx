// frontend/src/components/Tools/SystemMonitor/ServerList.tsx
/**
 * 页签①服务器列表
 *
 * 设计参考 awesome-design-md / Linear：
 * - 顶部：概览统计条（服务器数 / 在线 / 异常 / 平均 CPU）+ 主动作按钮
 * - 中部：按分组排列的卡片网格（分组标题为 eyebrow 小字）
 * - 卡片：见 components/ServerCard（状态点、四个关键指标、快捷操作）
 * - 空态：虚线大方框 + 主 CTA，引导首次添加
 */
import { useCallback, useEffect, useState } from 'react';
import { Plus, Server, RefreshCw, ArrowRightLeft, CheckCircle2, AlertTriangle, Cpu } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import type { MonitorServer } from '../../../api/monitorApi';
import * as monitorApi from '../../../api/monitorApi';
import * as sshApi from '../../../api/sshToolApi';
import { ServerCard } from './components/ServerCard';
import AddServerModal from './components/AddServerModal';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

/** 顶部统计小卡 */
function StatPill({
  icon: Icon,
  label,
  value,
  tone = 'text-ink',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-3 py-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-ink-faint" aria-hidden />
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
        <div className={`text-sm font-semibold tabular-nums leading-tight ${tone}`}>{value}</div>
      </div>
    </div>
  );
}

export default function ServerList() {
  const { servers, setServers, setSelectedServerId, setActiveTab } = useMonitorStore();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<MonitorServer | null>(null);
  const [deleting, setDeleting] = useState<MonitorServer | null>(null);
  const [sshConfigs, setSshConfigs] = useState<sshApi.SSHConfig[]>([]);
  const [error, setError] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  const refresh = useCallback(async () => {
    try {
      setServers(await monitorApi.getServers());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    }
  }, [setServers]);

  // 进页面自动同步一次 SSH 配置（幂等：只补缺、不覆盖）
  const syncFromSsh = useCallback(async (silent = false) => {
    setSyncing(true);
    if (!silent) { setError(''); setSyncMsg(''); }
    try {
      const res = await monitorApi.syncServersFromSsh();
      const changed = res.created + res.updated + res.disabled;
      if (changed > 0) {
        setSyncMsg(
          `已同步 SSH 配置：新增 ${res.created} / 更新 ${res.updated} / 停用 ${res.disabled}`,
        );
      } else if (!silent) {
        setSyncMsg(`SSH 配置 ${res.sshTotal} 台，全部已同步`);
      }
      await refresh();
    } catch (e: unknown) {
      if (!silent) setError(e instanceof Error ? e.message : '同步失败');
    } finally {
      setSyncing(false);
    }
  }, [refresh]);

  useEffect(() => {
    void refresh();
    void syncFromSsh(true);
  }, [refresh, syncFromSsh]);

  const openAdd = async () => {
    setError('');
    try {
      setSshConfigs(await sshApi.getSSHConfigs());
    } catch {
      setSshConfigs([]);
    }
    setAddOpen(true);
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await monitorApi.deleteServer(deleting.id);
      setDeleting(null);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '删除失败');
      setDeleting(null);
    }
  };

  const handleRetry = async (server: MonitorServer) => {
    try {
      await monitorApi.retryServer(server.id);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '重试失败');
    }
  };

  const enter = (id: string) => {
    setSelectedServerId(id);
    setActiveTab('overview');
  };

  const groups: Record<string, MonitorServer[]> = {};
  for (const s of servers) {
    const g = s.group_name || '默认分组';
    (groups[g] ||= []).push(s);
  }

  const online = servers.filter((s) => s.status === 'online');
  const abnormal = servers.filter((s) => s.status === 'error' || s.status === 'offline');
  const avgCpu = online.length
    ? Math.round(
        online.reduce((sum, s) => sum + (s.metric?.cpu_percent ?? 0), 0) / online.length,
      )
    : null;

  return (
    <div className="flex flex-col gap-4">
      {/* ---------- 顶部：统计 + 主动作 ---------- */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatPill icon={Server} label="服务器" value={`${servers.length} 台`} />
          <StatPill
            icon={CheckCircle2}
            label="在线"
            value={`${online.length}`}
            tone="text-accent-success"
          />
          <StatPill
            icon={AlertTriangle}
            label="异常"
            value={`${abnormal.length}`}
            tone={abnormal.length > 0 ? 'text-accent-danger' : 'text-ink-faint'}
          />
          <StatPill
            icon={Cpu}
            label="平均 CPU"
            value={avgCpu === null ? '—' : `${avgCpu}%`}
            tone={avgCpu !== null && avgCpu >= 80 ? 'text-accent-warning' : 'text-ink'}
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void syncFromSsh()}
            disabled={syncing}
            title="从 SSH 工具同步服务器配置（只补缺，不覆盖已有监控配置）"
          >
            <ArrowRightLeft className={`mr-1.5 h-3.5 w-3.5 ${syncing ? 'animate-pulse' : ''}`} aria-hidden />
            {syncing ? '同步中…' : '同步 SSH 配置'}
          </Button>
          <Button variant="secondary" size="sm" onClick={() => void refresh()}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            刷新
          </Button>
          <Button size="sm" onClick={openAdd}>
            <Plus className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            添加服务器
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}
      {syncMsg && (
        <div className="flex items-start justify-between gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-accent-success">
          <span className="min-w-0 break-words">{syncMsg}</span>
          <button
            type="button"
            onClick={() => setSyncMsg('')}
            aria-label="关闭同步提示"
            className="shrink-0 rounded p-0.5 hover:bg-success/20"
          >
            ×
          </button>
        </div>
      )}

      {/* ---------- 分组卡片网格 ---------- */}
      {Object.entries(groups).map(([group, list]) => (
        <section key={group} className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">
              {group}
            </h3>
            <span className="text-[11px] text-ink-faint/70">{list.length}</span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {list.map((server) => (
              <ServerCard
                key={server.id}
                server={server}
                onSelect={enter}
                onEdit={(s) => setEditing(s)}
                onDelete={(s) => setDeleting(s)}
                onRetry={handleRetry}
              />
            ))}
          </div>
        </section>
      ))}

      {/* ---------- 空态 ---------- */}
      {servers.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border px-6 py-16 text-center">
          <Server className="h-10 w-10 text-ink-faint" aria-hidden />
          <p className="text-sm font-medium text-ink">还没有监控服务器</p>
          <p className="max-w-sm text-xs text-ink-muted">
            已经配过 SSH 连接的话，点「同步 SSH 配置」即可自动接入；也可以手动添加服务器。
          </p>
          <div className="mt-1 flex items-center gap-2">
            <Button size="sm" onClick={() => void syncFromSsh()}>
              <ArrowRightLeft className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              同步 SSH 配置
            </Button>
            <Button variant="secondary" size="sm" onClick={openAdd}>
              <Plus className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              手动添加
            </Button>
          </div>
        </div>
      )}

      <AddServerModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSaved={refresh}
        sshConfigs={sshConfigs}
      />

      {editing && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setEditing(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="编辑服务器"
            className="w-full max-w-[420px] rounded-xl border border-border bg-surface-1 p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 text-sm font-semibold text-ink">
              编辑服务器
              <span className="ml-2 text-[11px] font-normal text-ink-faint">
                仅改名称，连接信息由 SSH 配置同步
              </span>
            </div>
            <Input className="mb-3 w-full" defaultValue={editing.name} placeholder="服务器名称" id="edit-name" />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEditing(null)}>
                取消
              </Button>
              <Button
                onClick={async () => {
                  const input = document.getElementById('edit-name') as HTMLInputElement;
                  try {
                    await monitorApi.updateServer(editing.id, { name: input.value });
                    setEditing(null);
                    await refresh();
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : '更新失败');
                  }
                }}
              >
                保存
              </Button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title="删除服务器"
        description={`确定删除监控服务器「${deleting?.name}」？其历史指标与关联告警记录将保留。`}
        confirmText="删除"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}

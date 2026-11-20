// frontend/src/components/Tools/SystemMonitor/Services.tsx
/**
 * 页签⑤服务管理（systemd 服务列表与启停）
 *
 * 设计参考 awesome-design-md / Linear：
 * - 顶部：服务器选择 + 搜索 + 刷新 + 运行中/已停止统计 pill
 * - sudo 不可用时给黄色提示条（不阻断浏览，只提示操作可能失败）
 * - 表格：状态用圆点 + 文字而非色块徽章，操作按钮只在悬停时上色
 */
import { useEffect, useState, useCallback, useMemo } from 'react';
import { RefreshCw, Search, PlayCircle, StopCircle, RotateCw, ShieldAlert } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { ServiceInfo } from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

/** 状态 → 圆点与文字颜色 */
function statusTone(state: string): { dot: string; text: string; label: string } {
  const s = (state || '').toLowerCase();
  if (s === 'running') return { dot: 'bg-accent-success', text: 'text-accent-success', label: 'running' };
  if (s === 'failed') return { dot: 'bg-accent-danger', text: 'text-accent-danger', label: 'failed' };
  if (s === 'inactive' || s === 'dead') return { dot: 'bg-ink-faint', text: 'text-ink-faint', label: state };
  return { dot: 'bg-accent-warning', text: 'text-accent-warning', label: state };
}

/** 页签⑤服务管理：systemd 服务列表与启停 */
export default function Services() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [sudoOk, setSudoOk] = useState(false);
  const [confirm, setConfirm] = useState<{
    unit: string;
    action: 'start' | 'stop' | 'restart';
  } | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    if (!selectedServerId) return;
    setLoading(true);
    setError('');
    try {
      const [svcRes, privRes] = await Promise.all([
        monitorApi.getServices(selectedServerId),
        monitorApi.getPrivileges(selectedServerId),
      ]);
      setServices(svcRes.services);
      setSudoOk(privRes.sudo_available);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedServerId]);

  useEffect(() => {
    void load();
  }, [load]);

  const doAction = async () => {
    if (!confirm || !selectedServerId) return;
    try {
      await monitorApi.serviceAction(selectedServerId, confirm.unit, confirm.action);
      setConfirm(null);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '操作失败');
      setConfirm(null);
    }
  };

  const filtered = useMemo(
    () =>
      services.filter(
        (s) =>
          search === '' ||
          s.name.toLowerCase().includes(search.toLowerCase()) ||
          (s.description || '').toLowerCase().includes(search.toLowerCase()),
      ),
    [services, search],
  );

  const runningCount = services.filter((s) => s.state === 'running').length;
  const stoppedCount = services.length - runningCount;

  return (
    <div className="flex flex-col gap-3">
      {/* ---------- 顶部：筛选 + 统计 ---------- */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-3 py-2 text-[11px]">
            <span className="flex items-center gap-1 text-accent-success">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-success" />
              运行中 {runningCount}
            </span>
            <span className="h-3 w-px bg-border" />
            <span className="flex items-center gap-1 text-ink-faint">
              <span className="h-1.5 w-1.5 rounded-full bg-ink-faint" />
              未运行 {stoppedCount}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" aria-hidden />
            <Input
              className="w-[200px] pl-8 text-xs"
              placeholder="搜索服务名 / 描述"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden />
            {loading ? '刷新中…' : '刷新'}
          </Button>
        </div>
      </div>

      {!sudoOk && selectedServerId && (
        <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-accent-warning">
          <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          当前用户可能没有 sudo 权限，启动/停止/重启可能需要 root 或免密 sudo 才能生效
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}

      {/* ---------- 服务列表 ---------- */}
      <div className="overflow-hidden rounded-xl border border-border bg-surface-1">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-xs">
            <thead>
              <tr className="border-b border-border text-ink-faint">
                <th className="px-3 py-2 text-left font-normal">服务名</th>
                <th className="px-3 py-2 text-left font-normal">状态</th>
                <th className="hidden px-3 py-2 text-left font-normal md:table-cell">描述</th>
                <th className="hidden px-3 py-2 text-left font-normal lg:table-cell">开机自启</th>
                <th className="px-3 py-2 text-right font-normal">操作</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const tone = statusTone(s.state);
                const running = s.state === 'running';
                return (
                  <tr
                    key={s.name}
                    className="group border-b border-border/60 last:border-0 hover:bg-surface-2/60"
                  >
                    <td className="px-3 py-2 font-mono text-[11px] text-ink">{s.name}</td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center gap-1.5 ${tone.text}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
                        {tone.label}
                      </span>
                    </td>
                    <td
                      className="hidden max-w-[320px] truncate px-3 py-2 text-ink-faint md:table-cell"
                      title={s.description}
                    >
                      {s.description || '—'}
                    </td>
                    <td className="hidden px-3 py-2 text-ink-muted lg:table-cell">
                      {s.enabled ? '已启用' : '未启用'}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-end gap-1 opacity-60 transition-opacity group-hover:opacity-100">
                        {running ? (
                          <>
                            <button
                              type="button"
                              onClick={() => setConfirm({ unit: s.name, action: 'restart' })}
                              className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-ink-muted hover:bg-surface-3 hover:text-ink"
                              title="重启"
                            >
                              <RotateCw className="h-3 w-3" aria-hidden />
                              重启
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirm({ unit: s.name, action: 'stop' })}
                              className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-ink-muted hover:bg-danger/10 hover:text-accent-danger"
                              title="停止"
                            >
                              <StopCircle className="h-3 w-3" aria-hidden />
                              停止
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirm({ unit: s.name, action: 'start' })}
                            className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-ink-muted hover:bg-success/10 hover:text-accent-success"
                            title="启动"
                          >
                            <PlayCircle className="h-3 w-3" aria-hidden />
                            启动
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="px-3 py-10 text-center text-ink-faint">
                    {services.length === 0 ? '暂无服务' : '没有匹配的服务'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(open) => {
          if (!open) setConfirm(null);
        }}
        title="服务操作"
        description={`确定要${
          confirm?.action === 'start' ? '启动' : confirm?.action === 'stop' ? '停止' : '重启'
        }服务 ${confirm?.unit}？`}
        onConfirm={doAction}
      />
    </div>
  );
}

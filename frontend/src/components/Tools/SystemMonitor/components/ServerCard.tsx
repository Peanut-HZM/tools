// frontend/src/components/Tools/SystemMonitor/components/ServerCard.tsx
/**
 * 服务器状态卡片
 *
 * 设计参考 awesome-design-md 的 Linear 方案：
 * - 表面分层：canvas → surface-1 卡片 → surface-2 内嵌块
 * - hairline 边框（不靠重阴影），悬停时才微微提亮 + 边框变强
 * - 每个指标一行「标签 + 数值 + 细进度条」，数值用等宽数字（tabular-nums）
 * - 状态用语义色小圆点 + 呼吸光晕，离线时整卡降饱和
 * - 强调色只用在「便携入口」和关键数字上，不做装饰
 */
import type { MonitorServer } from '../../../../api/monitorApi';
import { Cpu, HardDrive, MemoryStick, Network, Activity, RefreshCw, Settings2, Trash2, ArrowUpRight } from 'lucide-react';

interface ServerCardProps {
  server: MonitorServer;
  onSelect: (id: string) => void;
  onEdit?: (server: MonitorServer) => void;
  onDelete?: (server: MonitorServer) => void;
  onRetry?: (server: MonitorServer) => void;
}

function fmtRate(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  if (v < 1024) return `${v.toFixed(0)} B/s`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB/s`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB/s`;
}

function fmtBytes(v: number | null | undefined): string {
  if (!v) return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
  return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function fmtUptime(sec: number | null | undefined): string {
  if (!sec) return '';
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  if (d > 0) return `${d}天${h}小时`;
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}小时${m}分` : `${m}分钟`;
}

/** 占用率配色：<60 正常 / 60-85 警告 / ≥85 危险 */
function toneOf(pct: number | null | undefined): { text: string; bar: string } {
  if (pct === null || pct === undefined) {
    return { text: 'text-ink-faint', bar: 'bg-surface-3' };
  }
  if (pct >= 85) return { text: 'text-accent-danger', bar: 'bg-accent-danger' };
  if (pct >= 60) return { text: 'text-accent-warning', bar: 'bg-accent-warning' };
  return { text: 'text-accent-success', bar: 'bg-accent-success' };
}

const STATUS_META: Record<string, { dot: string; label: string; text: string }> = {
  online: { dot: 'bg-accent-success', label: '在线', text: 'text-accent-success' },
  offline: { dot: 'bg-accent-danger', label: '离线', text: 'text-accent-danger' },
  error: { dot: 'bg-accent-warning', label: '异常', text: 'text-accent-warning' },
  collecting: { dot: 'bg-accent-info', label: '采集中', text: 'text-accent-info' },
  disabled: { dot: 'bg-ink-faint', label: '已停用', text: 'text-ink-faint' },
};

/** 一行指标：图标 + 标签 + 数值 + 细进度条 */
function MetricRow({
  icon: Icon,
  label,
  value,
  percent,
  hint,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  percent?: number | null;
  hint?: string;
}) {
  const tone = toneOf(percent);
  return (
    <div className="group/metric flex items-center gap-2">
      <Icon className="h-3 w-3 shrink-0 text-ink-faint" aria-hidden />
      <span className="w-9 shrink-0 text-[11px] text-ink-faint">{label}</span>
      <div className="h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-3">
        {percent !== null && percent !== undefined && (
          <div
            className={`h-full rounded-full transition-[width] duration-500 ${tone.bar}`}
            style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
          />
        )}
      </div>
      <span className={`w-14 shrink-0 text-right text-[11px] tabular-nums ${tone.text}`} title={hint}>
        {value}
      </span>
    </div>
  );
}

/** 服务器状态卡片：连接状态 + 关键性能指标 + 快捷操作 */
export function ServerCard({ server, onSelect, onEdit, onDelete, onRetry }: ServerCardProps) {
  const m = server.metric;
  const isOnline = server.status === 'online';
  const isLocal = server.server_type === 'local';
  const meta = STATUS_META[server.status] ?? STATUS_META.disabled;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(server.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(server.id);
        }
      }}
      data-testid={`server-card-${server.id}`}
      className={[
        'group relative flex flex-col gap-3 rounded-xl border bg-surface-1 p-4',
        'transition-all duration-200 outline-none',
        'hover:-translate-y-px hover:border-border-strong hover:bg-surface-2',
        'focus-visible:ring-2 focus-visible:ring-accent/60',
        isOnline ? 'border-border' : 'border-border opacity-80',
      ].join(' ')}
    >
      {/* ---------- 头部：状态 + 名称 + 主机 ---------- */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="relative flex h-2 w-2 shrink-0" aria-label={meta.label}>
            <span className={`absolute inset-0 rounded-full ${meta.dot} ${isOnline ? 'animate-ping opacity-40' : ''}`} />
            <span className={`relative h-2 w-2 rounded-full ${meta.dot}`} />
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium leading-tight text-ink" title={server.name}>
              {server.name}
            </div>
            <div className="mt-0.5 truncate text-[11px] text-ink-faint" title={isLocal ? '本机' : `${server.username}@${server.host}:${server.port}`}>
              {isLocal ? '本机节点' : `${server.username}@${server.host}`}
            </div>
          </div>
        </div>
        <span className={`shrink-0 rounded-full border border-border px-2 py-0.5 text-[10px] ${meta.text}`}>
          {meta.label}
        </span>
      </div>

      {/* ---------- 指标区 ---------- */}
      {isOnline && m ? (
        <div className="flex flex-col gap-1.5">
          <MetricRow
            icon={Cpu}
            label="CPU"
            value={m.cpu_percent !== null && m.cpu_percent !== undefined ? `${m.cpu_percent}%` : '—'}
            percent={m.cpu_percent}
            hint={m.load_avg ? `负载 ${m.load_avg.map((x) => x.toFixed(2)).join(' / ')}` : undefined}
          />
          <MetricRow
            icon={MemoryStick}
            label="内存"
            value={m.mem_percent !== null && m.mem_percent !== undefined ? `${m.mem_percent}%` : '—'}
            percent={m.mem_percent}
            hint={m.mem_total ? `${fmtBytes(m.mem_used)} / ${fmtBytes(m.mem_total)}` : undefined}
          />
          <MetricRow
            icon={HardDrive}
            label="磁盘"
            value={m.disk_percent !== null && m.disk_percent !== undefined ? `${m.disk_percent}%` : '—'}
            percent={m.disk_percent}
            hint={m.disk_total ? `${fmtBytes(m.disk_used)} / ${fmtBytes(m.disk_total)}` : undefined}
          />
          <MetricRow
            icon={Network}
            label="网络"
            value={fmtRate(m.net_recv_rate)}
            percent={null}
            hint={`↓ ${fmtRate(m.net_recv_rate)} · ↑ ${fmtRate(m.net_sent_rate)}`}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-1 rounded-lg bg-surface-2 px-2.5 py-2">
          <span className="text-[11px] text-accent-danger/85">
            {server.last_error || (server.status === 'disabled' ? '已停用（SSH 配置已移除）' : '服务器离线')}
          </span>
          {server.status === 'error' && onRetry && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRetry(server); }}
              className="mt-0.5 inline-flex w-fit items-center gap-1 text-[11px] text-accent-info hover:underline"
            >
              <RefreshCw className="h-3 w-3" aria-hidden />
              重试采集
            </button>
          )}
        </div>
      )}

      {/* ---------- 底部：采集时间 + 操作 ---------- */}
      <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-2">
        <span className="flex min-w-0 items-center gap-1 text-[10px] text-ink-faint">
          <Activity className="h-3 w-3 shrink-0" aria-hidden />
          <span className="truncate">
            {server.last_seen_at
              ? server.last_seen_at.replace('T', ' ').slice(0, 19)
              : '尚未采集'}
            {m?.uptime_seconds ? ` · 已运行 ${fmtUptime(m.uptime_seconds)}` : ''}
          </span>
        </span>

        <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onSelect(server.id); }}
            className="rounded-md p-1 text-ink-faint hover:bg-surface-3 hover:text-ink"
            title="查看详情"
            aria-label={`查看 ${server.name} 详情`}
          >
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
          </button>
          {onEdit && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onEdit(server); }}
              className="rounded-md p-1 text-ink-faint hover:bg-surface-3 hover:text-ink"
              title="编辑"
              aria-label={`编辑 ${server.name}`}
            >
              <Settings2 className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
          {onDelete && !isLocal && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onDelete(server); }}
              className="rounded-md p-1 text-ink-faint hover:bg-danger/10 hover:text-accent-danger"
              title="删除"
              aria-label={`删除 ${server.name}`}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

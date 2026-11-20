// frontend/src/components/Tools/SystemMonitor/components/ResourceCards.tsx
/**
 * 资源占用卡片（总览页核心指标）
 *
 * 设计参考 awesome-design-md / Linear：
 * - 每张卡一个主指标：大号等宽数字 + 语义色进度条 + 副行绝对值
 * - 卡片表面 surface-1，进度条底槽 surface-3，靠色彩而非阴影表达状态
 * - 网络 / 磁盘 IO 用双行速率，不做进度条（没有上限概念）
 */
import { Cpu, HardDrive, MemoryStick, Network, Activity, ArrowDown, ArrowUp } from 'lucide-react';
import type { MetricPoint } from '../../../../api/monitorApi';

function fmtBytes(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  // 0 是正常业务值（空闲网卡/无磁盘 IO），直接短路避免 Math.log(0) 产生 NaN
  if (v === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
  return `${(v / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function fmtRate(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return `${fmtBytes(v)}/s`;
}

/** 占用率语义色：<60 正常 / 60-85 警告 / ≥85 危险 */
function toneOf(pct: number | null | undefined): { text: string; bar: string; glow: string } {
  if (pct === null || pct === undefined) {
    return { text: 'text-ink-faint', bar: 'bg-surface-3', glow: '' };
  }
  if (pct >= 85) return { text: 'text-accent-danger', bar: 'bg-accent-danger', glow: 'shadow-[0_0_12px_-2px] shadow-accent-danger/50' };
  if (pct >= 60) return { text: 'text-accent-warning', bar: 'bg-accent-warning', glow: 'shadow-[0_0_12px_-2px] shadow-accent-warning/40' };
  return { text: 'text-accent-success', bar: 'bg-accent-success', glow: '' };
}

/** 百分比指标卡 */
function MeterCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | null | undefined;
  detail?: string;
}) {
  const pct = value === null || value === undefined ? null : Math.max(0, Math.min(100, value));
  const tone = toneOf(pct);
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-3.5 transition-colors hover:border-border-strong">
      <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {label}
      </div>
      <div className={`mt-1.5 text-2xl font-semibold tabular-nums leading-none ${tone.text}`}>
        {pct === null ? '—' : `${pct.toFixed(1)}`}
        {pct !== null && <span className="ml-0.5 text-sm font-normal text-ink-faint">%</span>}
      </div>
      <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-surface-3">
        {pct !== null && (
          <div
            className={`h-full rounded-full transition-[width] duration-500 ${tone.bar} ${tone.glow}`}
            style={{ width: `${Math.max(pct, 1)}%` }}
          />
        )}
      </div>
      {detail && <div className="mt-1.5 truncate text-[10px] text-ink-faint" title={detail}>{detail}</div>}
    </div>
  );
}

/** 双行速率卡（网络 / 磁盘 IO） */
function RateCard({
  icon: Icon,
  label,
  downLabel,
  upLabel,
  down,
  up,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  downLabel: string;
  upLabel: string;
  down: number | null | undefined;
  up: number | null | undefined;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-3.5 transition-colors hover:border-border-strong">
      <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {label}
      </div>
      <div className="mt-2 flex flex-col gap-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1 text-[11px] text-ink-faint">
            <ArrowDown className="h-3 w-3 text-accent-info" aria-hidden />
            {downLabel}
          </span>
          <span className="tabular-nums text-sm font-medium text-ink">{fmtRate(down)}</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1 text-[11px] text-ink-faint">
            <ArrowUp className="h-3 w-3 text-accent-secondary" aria-hidden />
            {upLabel}
          </span>
          <span className="tabular-nums text-sm font-medium text-ink">{fmtRate(up)}</span>
        </div>
      </div>
    </div>
  );
}

/** 资源占用卡片组：CPU / 内存 / 磁盘 / 网络 / 磁盘 IO */
export default function ResourceCards({ metric }: { metric: MetricPoint | null }) {
  const memDetail =
    metric?.mem_total && metric?.mem_used
      ? `${fmtBytes(metric.mem_used)} / ${fmtBytes(metric.mem_total)}`
      : undefined;
  const diskDetail =
    metric?.disk_total && metric?.disk_used
      ? `${fmtBytes(metric.disk_used)} / ${fmtBytes(metric.disk_total)}`
      : undefined;
  const loadDetail = metric?.load_avg
    ? `负载 ${metric.load_avg.map((x) => x.toFixed(2)).join(' / ')}`
    : undefined;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      <MeterCard icon={Cpu} label="CPU 使用率" value={metric?.cpu_percent} detail={loadDetail} />
      <MeterCard icon={MemoryStick} label="内存使用率" value={metric?.mem_percent} detail={memDetail} />
      <MeterCard icon={HardDrive} label="磁盘使用率" value={metric?.disk_percent} detail={diskDetail} />
      <RateCard
        icon={Network}
        label="网络速率"
        downLabel="下行"
        upLabel="上行"
        down={metric?.net_recv_rate}
        up={metric?.net_sent_rate}
      />
      <RateCard
        icon={Activity}
        label="磁盘 IO"
        downLabel="读取"
        upLabel="写入"
        down={metric?.disk_read_rate}
        up={metric?.disk_write_rate}
      />
    </div>
  );
}

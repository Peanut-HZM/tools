// frontend/src/components/Tools/SystemMonitor/components/ResourceCards.tsx
import type { MetricPoint } from '../../../../api/monitorApi';
import { Card } from '@/components/ui/Card';

function fmtBytes(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  // 0 是正常业务值（空闲网卡/无磁盘 IO），直接短路避免 Math.log(0) = -Infinity 产生 NaN
  if (v === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
  return `${(v / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function fmtRate(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  return `${fmtBytes(v)}/s`;
}

function Meter({ label, value, color }: { label: string; value: number | null | undefined; color: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <Card className="p-3">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-ink-faint">{label}</span>
        <span className="text-ink font-medium">{value === null || value === undefined ? '-' : `${v.toFixed(1)}%`}</span>
      </div>
      <div className="h-1.5 rounded-full bg-surface-1 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${v}%` }} />
      </div>
    </Card>
  );
}

/** 资源占用卡片：CPU/内存/磁盘/网络/磁盘IO */
export default function ResourceCards({ metric }: { metric: MetricPoint | null }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
      <Meter label="CPU 使用率" value={metric?.cpu_percent} color="bg-success" />
      <Meter label="内存使用率" value={metric?.mem_percent} color="bg-accent" />
      <Meter label="磁盘使用率" value={metric?.disk_percent} color="bg-warning" />
      <Card className="p-3">
        <div className="text-xs text-ink-faint mb-1.5">网络速率</div>
        <div className="text-ink text-sm font-medium">↓ {fmtRate(metric?.net_recv_rate)}</div>
        <div className="text-ink text-sm font-medium mt-0.5">↑ {fmtRate(metric?.net_sent_rate)}</div>
      </Card>
      <Card className="p-3">
        <div className="text-xs text-ink-faint mb-1.5">磁盘 IO 速率</div>
        <div className="text-ink text-sm font-medium">读 {fmtRate(metric?.disk_read_rate)}</div>
        <div className="text-ink text-sm font-medium mt-0.5">写 {fmtRate(metric?.disk_write_rate)}</div>
      </Card>
    </div>
  );
}

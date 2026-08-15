// frontend/src/components/Tools/SystemMonitor/components/ResourceCards.tsx
import type { MetricPoint } from '../../../../api/monitorApi';

function fmtBytes(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
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
    <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-slate-500">{label}</span>
        <span className="text-white font-medium">{value === null || value === undefined ? '-' : `${v.toFixed(1)}%`}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

/** 资源占用卡片：CPU/内存/磁盘/网络/磁盘IO */
export default function ResourceCards({ metric }: { metric: MetricPoint | null }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
      <Meter label="CPU 使用率" value={metric?.cpu_percent} color="bg-emerald-500" />
      <Meter label="内存使用率" value={metric?.mem_percent} color="bg-blue-500" />
      <Meter label="磁盘使用率" value={metric?.disk_percent} color="bg-amber-500" />
      <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
        <div className="text-xs text-slate-500 mb-1.5">网络速率</div>
        <div className="text-white text-sm font-medium">↓ {fmtRate(metric?.net_recv_rate)}</div>
        <div className="text-white text-sm font-medium mt-0.5">↑ {fmtRate(metric?.net_sent_rate)}</div>
      </div>
      <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
        <div className="text-xs text-slate-500 mb-1.5">磁盘 IO 速率</div>
        <div className="text-white text-sm font-medium">读 {fmtRate(metric?.disk_read_rate)}</div>
        <div className="text-white text-sm font-medium mt-0.5">写 {fmtRate(metric?.disk_write_rate)}</div>
      </div>
    </div>
  );
}

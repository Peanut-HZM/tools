// frontend/src/components/Tools/SystemMonitor/History.tsx
/**
 * 页签③历史趋势
 *
 * 设计参考 awesome-design-md / Linear：
 * - 顶部一行：服务器选择 + 时间范围分段控件（segmented control）
 * - 指标组用 pill 切换，选中态才上色
 * - 主图上方给四个速览统计（当前 / 平均 / 峰值 / 样本数），让用户不点图也能读数
 * - 图表容器统一 surface-1 + hairline 边框，与其它卡片一致
 */
import { useEffect, useMemo, useState } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { MetricPoint } from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import MetricChart, { type ChartPoint, type ChartLine } from './components/MetricChart';
import { Activity, ArrowDown, ArrowUp, Gauge, Minus } from 'lucide-react';

const RANGES = [
  { key: '1h', label: '1 小时' },
  { key: '6h', label: '6 小时' },
  { key: '24h', label: '24 小时' },
  { key: '7d', label: '7 天' },
];

const GROUPS = [
  {
    key: 'cpu',
    label: 'CPU',
    lines: [{ key: 'cpu_percent', name: 'CPU 使用率', color: '#10b981' }],
    yUnit: '%',
    primary: 'cpu_percent',
  },
  {
    key: 'memory',
    label: '内存',
    lines: [{ key: 'mem_percent', name: '内存使用率', color: '#3b82f6' }],
    yUnit: '%',
    primary: 'mem_percent',
  },
  {
    key: 'load',
    label: '负载',
    lines: [{ key: 'load1', name: '负载（1 分钟）', color: '#f59e0b' }],
    yUnit: '',
    primary: 'load1',
  },
  {
    key: 'net',
    label: '网络',
    lines: [
      { key: 'net_recv_rate', name: '接收', color: '#10b981' },
      { key: 'net_sent_rate', name: '发送', color: '#f59e0b' },
    ],
    yUnit: 'B/s',
    primary: 'net_recv_rate',
  },
  {
    key: 'diskio',
    label: '磁盘 IO',
    lines: [
      { key: 'disk_read_rate', name: '读取', color: '#10b981' },
      { key: 'disk_write_rate', name: '写入', color: '#f59e0b' },
    ],
    yUnit: 'B/s',
    primary: 'disk_read_rate',
  },
] as const;

function fmtBytes(v: number): string {
  if (!v) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
  return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function toChartPoints(points: MetricPoint[], group: string): ChartPoint[] {
  return points.map((p) => {
    const t = new Date(p.collected_at);
    const time = t.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
    const point: ChartPoint = { time };
    if (group === 'cpu') point.cpu_percent = p.cpu_percent ?? null;
    if (group === 'memory') point.mem_percent = p.mem_percent ?? null;
    if (group === 'load') point.load1 = p.load_avg?.[0] ?? null;
    if (group === 'net') {
      point.net_recv_rate = p.net_recv_rate ?? null;
      point.net_sent_rate = p.net_sent_rate ?? null;
    }
    if (group === 'diskio') {
      point.disk_read_rate = p.disk_read_rate ?? null;
      point.disk_write_rate = p.disk_write_rate ?? null;
    }
    return point;
  });
}

/** 速览统计卡 */
function StatCard({
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
    <div className="rounded-xl border border-border bg-surface-1 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {label}
      </div>
      <div className={`mt-1 text-base font-semibold tabular-nums leading-tight ${tone}`}>{value}</div>
    </div>
  );
}

/** 页签③历史趋势：时间范围 + 指标组切换 + 趋势图 + 速览统计 */
export default function History() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [range, setRange] = useState('1h');
  const [group, setGroup] = useState('cpu');
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!selectedServerId) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    monitorApi
      .getMetrics(selectedServerId, range)
      .then((data) => {
        if (!cancelled) setPoints(toChartPoints(data.points, group));
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '加载失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedServerId, range, group]);

  const groupConfig = GROUPS.find((g) => g.key === group)!;
  const lines: ChartLine[] = [...groupConfig.lines];

  // 速览统计：取主指标列（多线时用第一条）
  const stats = useMemo(() => {
    const values = points
      .map((p) => p[groupConfig.primary])
      .filter((v): v is number => typeof v === 'number');
    if (values.length === 0) return null;
    const sum = values.reduce((a, b) => a + b, 0);
    const current = values[values.length - 1];
    const prev = values.length > 1 ? values[values.length - 2] : current;
    const isRate = groupConfig.yUnit === 'B/s';
    const fmt = (v: number) => (isRate ? fmtBytes(v) : `${v.toFixed(groupConfig.yUnit === '%' ? 1 : 2)}${groupConfig.yUnit}`);
    return {
      current: fmt(current),
      average: fmt(sum / values.length),
      peak: fmt(Math.max(...values)),
      samples: values.length,
      delta: current - prev,
      deltaText: isRate ? fmtBytes(Math.abs(current - prev)) : Math.abs(current - prev).toFixed(2),
      isRate,
    };
  }, [points, groupConfig]);

  return (
    <div className="flex flex-col gap-4">
      {/* ---------- 顶部：服务器 + 时间范围 ---------- */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <div className="inline-flex rounded-lg border border-border bg-surface-1 p-0.5">
          {RANGES.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => setRange(r.key)}
              aria-pressed={range === r.key}
              className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
                range === r.key
                  ? 'bg-accent text-white'
                  : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}

      {/* ---------- 指标组切换 ---------- */}
      <div className="flex flex-wrap items-center gap-1">
        {GROUPS.map((g) => (
          <button
            key={g.key}
            type="button"
            onClick={() => setGroup(g.key)}
            aria-pressed={group === g.key}
            className={`rounded-lg px-3 py-1.5 text-xs transition-colors ${
              group === g.key
                ? 'bg-surface-3 text-ink'
                : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
            }`}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* ---------- 速览统计 ---------- */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard icon={Activity} label="当前" value={stats.current} />
          <StatCard icon={Minus} label="平均" value={stats.average} />
          <StatCard icon={Gauge} label="峰值" value={stats.peak} tone="text-accent-warning" />
          <StatCard
            icon={stats.delta >= 0 ? ArrowUp : ArrowDown}
            label={`较上一采样（${stats.samples} 点）`}
            value={`${stats.delta >= 0 ? '+' : '−'}${stats.deltaText}`}
            tone={stats.delta >= 0 ? 'text-accent-danger' : 'text-accent-success'}
          />
        </div>
      )}

      {/* ---------- 趋势图 ---------- */}
      {loading ? (
        <div className="flex items-center justify-center rounded-xl border border-border bg-surface-1 py-20 text-sm text-ink-muted">
          正在加载…
        </div>
      ) : points.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border py-20 text-center">
          <Gauge className="h-8 w-8 text-ink-faint" aria-hidden />
          <p className="text-sm text-ink-muted">该时间范围内暂无数据</p>
          <p className="text-[11px] text-ink-faint">后端每 30 秒采集一次，稍等一会再刷新</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-surface-1 p-3 sm:p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-medium text-ink">{groupConfig.label} 趋势</h3>
            <span className="text-[11px] text-ink-faint">
              {RANGES.find((r) => r.key === range)?.label} · {points.length} 个采样点
            </span>
          </div>
          <MetricChart data={points} lines={lines} yUnit={groupConfig.yUnit} />
        </div>
      )}
    </div>
  );
}

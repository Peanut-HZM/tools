import { useEffect, useState } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { MetricPoint } from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import MetricChart, { type ChartPoint, type ChartLine } from './components/MetricChart';
import { Card, CardContent } from '@/components/ui/Card';

const RANGES = [
  { key: '1h', label: '近 1 小时' },
  { key: '6h', label: '近 6 小时' },
  { key: '24h', label: '近 24 小时' },
  { key: '7d', label: '近 7 天' },
];

const GROUPS = [
  {
    key: 'cpu', label: 'CPU',
    lines: [{ key: 'cpu_percent', name: 'CPU 使用率', color: '#10b981' }],
    yUnit: '%',
  },
  {
    key: 'memory', label: '内存',
    lines: [{ key: 'mem_percent', name: '内存使用率', color: '#3b82f6' }],
    yUnit: '%',
  },
  {
    key: 'load', label: '负载',
    lines: [{ key: 'load1', name: '负载(1分钟)', color: '#f59e0b' }],
    yUnit: '',
  },
  {
    key: 'net', label: '网络 IO',
    lines: [
      { key: 'net_recv_rate', name: '接收', color: '#10b981' },
      { key: 'net_sent_rate', name: '发送', color: '#f59e0b' },
    ],
    yUnit: 'B/s',
  },
  {
    key: 'diskio', label: '磁盘 IO',
    lines: [
      { key: 'disk_read_rate', name: '读', color: '#10b981' },
      { key: 'disk_write_rate', name: '写', color: '#f59e0b' },
    ],
    yUnit: 'B/s',
  },
];

function toChartPoints(points: MetricPoint[], group: string): ChartPoint[] {
  return points.map((p) => {
    const t = new Date(p.collected_at);
    const time = t.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
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

/** 页签③历史趋势：时间范围 + 指标组切换 */
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
    monitorApi.getMetrics(selectedServerId, range)
      .then((data) => { if (!cancelled) setPoints(toChartPoints(data.points, group)); })
      .catch((e: any) => { if (!cancelled) setError(e.message || '加载失败'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedServerId, range, group]);

  const groupConfig = GROUPS.find((g) => g.key === group)!;
  const lines: ChartLine[] = groupConfig.lines;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <div className="flex items-center gap-1 flex-wrap">
          {RANGES.map((r) => (
            <button
              key={r.key}
              className={`px-3 py-1.5 rounded-lg text-xs ${range === r.key ? 'bg-success/20 text-success' : 'text-ink-muted hover:text-ink hover:bg-surface-1'}`}
              onClick={() => setRange(r.key)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-1">
        {GROUPS.map((g) => (
          <button
            key={g.key}
            className={`px-3 py-1.5 rounded-lg text-xs ${group === g.key ? 'bg-success/20 text-success' : 'text-ink-muted hover:text-ink hover:bg-surface-1'}`}
            onClick={() => setGroup(g.key)}
          >
            {g.label}
          </button>
        ))}
      </div>
      {error && <div className="text-sm text-danger">{error}</div>}
      {loading ? (
        <div className="text-center text-ink-faint py-16">加载中...</div>
      ) : points.length === 0 ? (
        <div className="text-center text-ink-faint py-16">暂无数据（采集后约 1 分钟可见）</div>
      ) : (
        <Card className="p-4 bg-canvas">
          <CardContent className="p-0">
            <MetricChart data={points} lines={lines} yUnit={groupConfig.yUnit} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { MetricPoint } from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import ResourceCards from './components/ResourceCards';
import SystemInfoCards from './components/SystemInfoCards';


/** 页签②总览：系统信息 + 资源卡片，5s 轮询 */
export default function Overview() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [metric, setMetric] = useState<MetricPoint | null>(null);
  const [info, setInfo] = useState<Record<string, string | number> | null>(null);
  const [partitions, setPartitions] = useState<Array<{ device: string; mountpoint: string; total: number; used: number; percent: number }>>([]);
  const [error, setError] = useState('');

  const server = servers.find((s) => s.id === selectedServerId) || null;

  // 切换服务器时加载系统信息与分区
  useEffect(() => {
    if (!server) return;
    let cancelled = false;
    setInfo(null);
    setPartitions([]);
    monitorApi.getSystemInfo(server.id).then((i) => { if (!cancelled) setInfo(i); }).catch(() => {});
    monitorApi.getPartitions(server.id)
      .then((r) => { if (!cancelled) setPartitions(r.partitions); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [server?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // 5s 轮询实时指标
  useEffect(() => {
    if (!server) return;
    let cancelled = false;
    const load = async () => {
      try {
        const data = await monitorApi.getOverview(server.id);
        if (!cancelled) setMetric(data.metric);
      } catch (e: any) {
        if (!cancelled) setError(e.message || '加载失败');
      }
    };
    load();
    const timer = setInterval(load, 5000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [server?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!server) {
    return <div className="text-center text-ink-faint py-16">请先在「服务器列表」添加或选择服务器</div>;
  }

  const fmtBytes = (v: number) => {
    // 防御：分区 total/used 理论非 0，但保持与 ResourceCards 一致的短路，避免 Math.log(0) = -Infinity 产生 NaN
    if (v === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
    return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* ---------- 页头：服务器选择 + 刷新节奏说明 ---------- */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent-success" />
          每 5 秒刷新 · 后端每 30 秒采集
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}

      <SystemInfoCards info={info} server={server} />
      <ResourceCards metric={metric} />

      {/* ---------- 磁盘分区 ---------- */}
      <div className="overflow-hidden rounded-xl border border-border bg-surface-1">
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <h3 className="text-xs font-medium text-ink">磁盘分区</h3>
          <span className="text-[11px] text-ink-faint">{partitions.length} 个挂载点</span>
        </div>
        {/* 窄屏横向滚动，避免列被压成竖排 */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-xs">
            <thead>
              <tr className="border-b border-border text-ink-faint">
                <th className="px-4 py-2 text-left font-normal">设备</th>
                <th className="px-4 py-2 text-left font-normal">挂载点</th>
                <th className="px-4 py-2 text-right font-normal">总量</th>
                <th className="px-4 py-2 text-right font-normal">已用</th>
                <th className="px-4 py-2 text-right font-normal">使用率</th>
              </tr>
            </thead>
            <tbody>
              {partitions.map((p, i) => {
                const tone =
                  p.percent >= 90
                    ? 'text-accent-danger'
                    : p.percent >= 75
                      ? 'text-accent-warning'
                      : 'text-ink-muted';
                const bar =
                  p.percent >= 90
                    ? 'bg-accent-danger'
                    : p.percent >= 75
                      ? 'bg-accent-warning'
                      : 'bg-accent-success';
                return (
                  <tr key={i} className="border-b border-border/60 last:border-0 hover:bg-surface-2/60">
                    <td className="px-4 py-2 font-mono text-[11px] text-ink-muted">{p.device}</td>
                    <td className="px-4 py-2 font-mono text-[11px] text-ink-muted">{p.mountpoint}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-ink-muted">{fmtBytes(p.total)}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-ink-muted">{fmtBytes(p.used)}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center justify-end gap-2">
                        <div className="h-1 w-16 overflow-hidden rounded-full bg-surface-3">
                          <div
                            className={`h-full rounded-full ${bar}`}
                            style={{ width: `${Math.max(0, Math.min(100, p.percent))}%` }}
                          />
                        </div>
                        <span className={`w-11 text-right tabular-nums ${tone}`}>
                          {p.percent.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {partitions.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-ink-faint">
                    暂无分区数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

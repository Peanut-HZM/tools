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
    return <div className="text-center text-slate-500 py-16">请先在「服务器列表」添加或选择服务器</div>;
  }

  const fmtBytes = (v: number) => {
    // 防御：分区 total/used 理论非 0，但保持与 ResourceCards 一致的短路，避免 Math.log(0) = -Infinity 产生 NaN
    if (v === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
    return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <div className="text-xs text-slate-500">每 5 秒自动刷新 · 数据每 30 秒采集一次</div>
      </div>
      {error && <div className="text-sm text-red-400">{error}</div>}
      <SystemInfoCards info={info} server={server} />
      <ResourceCards metric={metric} />
      {/* 分区表格 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="px-4 py-2.5 text-sm text-white font-medium border-b border-slate-800">磁盘分区</div>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-800">
              <th className="text-left px-4 py-2">设备</th>
              <th className="text-left px-4 py-2">挂载点</th>
              <th className="text-right px-4 py-2">总量</th>
              <th className="text-right px-4 py-2">已用</th>
              <th className="text-right px-4 py-2">使用率</th>
            </tr>
          </thead>
          <tbody>
            {partitions.map((p, i) => (
              <tr key={i} className="border-b border-slate-800/50 last:border-0">
                <td className="px-4 py-2 text-slate-300">{p.device}</td>
                <td className="px-4 py-2 text-slate-400">{p.mountpoint}</td>
                <td className="px-4 py-2 text-right text-slate-400">{fmtBytes(p.total)}</td>
                <td className="px-4 py-2 text-right text-slate-400">{fmtBytes(p.used)}</td>
                <td className="px-4 py-2 text-right">
                  <span className={p.percent > 90 ? 'text-red-400' : 'text-slate-300'}>{p.percent.toFixed(1)}%</span>
                </td>
              </tr>
            ))}
            {partitions.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-600">暂无分区数据</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

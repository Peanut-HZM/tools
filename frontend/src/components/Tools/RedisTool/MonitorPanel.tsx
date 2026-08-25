import React, { useState, useEffect } from 'react';
import { getMonitorInfo, getSlowLog } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
}

export const MonitorPanel: React.FC<Props> = ({ configId }) => {
  const { addToast } = useToast();
  const [monitor, setMonitor] = useState<any>(null);
  const [slowLog, setSlowLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [m, s] = await Promise.all([
        getMonitorInfo(configId),
        getSlowLog(configId, 50)
      ]);
      setMonitor(m);
      setSlowLog(s.entries || []);
    } catch (e) {
      addToast('Failed to load monitor data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [configId]);

  if (loading) return <div className="flex justify-center items-center h-full text-ink-muted">Loading...</div>;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface-1 rounded-lg p-4 border border-border">
          <div className="text-xs text-ink-muted">内存使用</div>
          <div className="text-xl font-mono text-ink-inverse mt-1">{monitor?.used_memory_human || '0B'}</div>
        </div>
        <div className="bg-surface-1 rounded-lg p-4 border border-border">
          <div className="text-xs text-ink-muted">连接数</div>
          <div className="text-xl font-mono text-ink-inverse mt-1">{monitor?.connected_clients || 0} <span className="text-xs text-ink-faint">/ {monitor?.maxclients || 0}</span></div>
        </div>
        <div className="bg-surface-1 rounded-lg p-4 border border-border">
          <div className="text-xs text-ink-muted">命中率</div>
          <div className="text-xl font-mono text-ink-inverse mt-1">{monitor?.hit_rate?.toFixed(2) || 0}%</div>
        </div>
        <div className="bg-surface-1 rounded-lg p-4 border border-border">
          <div className="text-xs text-ink-muted">OPS</div>
          <div className="text-xl font-mono text-ink-inverse mt-1">{monitor?.ops_per_sec || 0}</div>
        </div>
      </div>

      {monitor?.db_keyspace && Object.keys(monitor.db_keyspace).length > 0 && (
        <div className="bg-surface-1 rounded-lg p-4 border border-border">
          <div className="text-sm font-medium text-ink-muted mb-3">数据库 Key 分布</div>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(monitor.db_keyspace).map(([db, data]: [string, any]) => (
              <div key={db} className="bg-canvas rounded p-2">
                <div className="text-xs text-ink-muted">{db}</div>
                <div className="text-sm text-ink-inverse">{data.keys} keys</div>
                <div className="text-xs text-ink-faint">{data.expires} expires</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-surface-1 rounded-lg border border-border overflow-hidden">
        <div className="px-4 py-3 border-b border-border text-sm font-medium text-ink-muted">慢查询日志（最近 50 条）</div>
        <table className="w-full text-sm">
          <thead className="bg-canvas text-ink-muted">
            <tr><th className="px-4 py-2 text-left">ID</th><th className="px-4 py-2 text-left">命令</th><th className="px-4 py-2 text-right">耗时 (ms)</th></tr>
          </thead>
          <tbody>
            {slowLog.map((entry) => (
              <tr key={entry.id} className="border-t border-border hover:bg-surface-1/50">
                <td className="px-4 py-2 font-mono text-xs text-ink-muted">{entry.id}</td>
                <td className="px-4 py-2 text-ink-muted font-mono text-xs">{entry.command}</td>
                <td className="px-4 py-2 text-right text-ink-muted">{entry.duration_ms}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

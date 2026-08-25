// frontend/src/components/Tools/SystemMonitor/Processes.tsx
import { useEffect, useState, useCallback } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { MonitorProcess } from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import ConfirmModal from './components/ConfirmModal';

const KNOWN_TYPES = ['all', 'FastAPI', 'Django', 'Flask', 'Celery', 'Gunicorn', 'Python',
  'Java', 'Node.js', 'Nginx', 'MySQL', 'PostgreSQL', 'Redis', 'Docker', 'Other'];

function fmtBytes(v: number): string {
  if (!v) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(v) / Math.log(1024));
  return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/** 页签④进程管理：列表/搜索/排序/分页/结束 */
export default function Processes() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [processes, setProcesses] = useState<MonitorProcess[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [projectType, setProjectType] = useState('all');
  const [sortBy, setSortBy] = useState('cpu_percent');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [loading, setLoading] = useState(false);
  const [killing, setKilling] = useState<MonitorProcess | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!selectedServerId) return;
    setLoading(true);
    try {
      const data = await monitorApi.getProcesses(selectedServerId, {
        sort_by: sortBy, sort_order: sortOrder, search: search || undefined,
        project_type: projectType, page, page_size: pageSize,
      });
      setProcesses(data.processes);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedServerId, sortBy, sortOrder, search, projectType, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(key);
      setSortOrder('desc');
    }
  };

  const handleKill = async () => {
    if (!killing || !selectedServerId) return;
    try {
      await monitorApi.killProcess(selectedServerId, killing.pid);
      setKilling(null);
      await load();
    } catch (e: any) {
      setError(e.message || '结束进程失败');
      setKilling(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <input
          className="flex-1 min-w-[180px] bg-canvas border border-border rounded-lg px-3 py-1.5 text-sm text-ink-inverse placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          placeholder="搜索进程名或命令行"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          className="bg-canvas border border-border rounded-lg px-3 py-1.5 text-sm text-ink-inverse focus:outline-none"
          value={projectType}
          onChange={(e) => { setProjectType(e.target.value); setPage(1); }}
        >
          {KNOWN_TYPES.map((t) => <option key={t} value={t}>{t === 'all' ? '全部类型' : t}</option>)}
        </select>
        <button className="px-3 py-1.5 rounded-lg text-sm bg-surface-1 hover:bg-surface-2 text-ink-muted" onClick={load}>
          <i className="fas fa-sync mr-1.5" />刷新
        </button>
      </div>
      {error && <div className="text-sm text-danger">{error}</div>}
      <div className="bg-canvas rounded-xl border border-border overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-ink-faint border-b border-border">
              <th className="text-left px-3 py-2 cursor-pointer hover:text-ink-muted" onClick={() => handleSort('pid')}>PID</th>
              <th className="text-left px-3 py-2 cursor-pointer hover:text-ink-muted" onClick={() => handleSort('name')}>进程名</th>
              <th className="text-left px-3 py-2 hidden md:table-cell">用户</th>
              <th className="text-right px-3 py-2 cursor-pointer hover:text-ink-muted" onClick={() => handleSort('cpu_percent')}>CPU%</th>
              <th className="text-right px-3 py-2 cursor-pointer hover:text-ink-muted" onClick={() => handleSort('memory_percent')}>内存%</th>
              <th className="text-right px-3 py-2 hidden lg:table-cell cursor-pointer hover:text-ink-muted" onClick={() => handleSort('memory_rss')}>内存</th>
              <th className="text-left px-3 py-2 hidden xl:table-cell">运行时间</th>
              <th className="text-left px-3 py-2">类型</th>
              <th className="text-right px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {processes.map((p) => (
              <tr key={p.pid} className="border-b border-border/50 last:border-0 hover:bg-surface-1/30">
                <td className="px-3 py-2 text-ink-muted">{p.pid}</td>
                <td className="px-3 py-2 text-ink-inverse max-w-[240px] truncate" title={p.command_line}>{p.name}</td>
                <td className="px-3 py-2 text-ink-faint hidden md:table-cell">{p.username}</td>
                <td className="px-3 py-2 text-right text-ink-muted">{p.cpu_percent.toFixed(1)}</td>
                <td className="px-3 py-2 text-right text-ink-muted">{p.memory_percent.toFixed(1)}</td>
                <td className="px-3 py-2 text-right text-ink-muted hidden lg:table-cell">{fmtBytes(p.memory_rss)}</td>
                <td className="px-3 py-2 text-ink-faint hidden xl:table-cell">{p.create_time}</td>
                <td className="px-3 py-2">
                  <span className="px-1.5 py-0.5 rounded bg-surface-1 text-[10px] text-success">{p.project_type}</span>
                </td>
                <td className="px-3 py-2 text-right">
                  <button className="text-danger/80 hover:text-red-300 text-[11px]" onClick={() => setKilling(p)}>结束</button>
                </td>
              </tr>
            ))}
            {processes.length === 0 && !loading && (
              <tr><td colSpan={9} className="px-3 py-10 text-center text-ink-faint">暂无进程</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-ink-faint">
          <span>共 {total} 个进程</span>
          <div className="flex items-center gap-2">
            <button className="px-2 py-1 rounded bg-surface-1 hover:bg-surface-2 disabled:opacity-40"
              disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
            <span>{page} / {totalPages}</span>
            <button className="px-2 py-1 rounded bg-surface-1 hover:bg-surface-2 disabled:opacity-40"
              disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button>
          </div>
        </div>
      )}
      <ConfirmModal
        open={!!killing}
        title="结束进程"
        message={`确定结束进程 ${killing?.pid}（${killing?.name}）？该操作不可撤销。`}
        onConfirm={handleKill}
        onCancel={() => setKilling(null)}
        danger
      />
    </div>
  );
}

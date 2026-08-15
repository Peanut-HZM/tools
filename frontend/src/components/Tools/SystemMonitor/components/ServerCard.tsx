// frontend/src/components/Tools/SystemMonitor/components/ServerCard.tsx
import type { MonitorServer } from '../../../../api/monitorApi';

interface ServerCardProps {
  server: MonitorServer;
  onSelect: (id: string) => void;
  onEdit?: (server: MonitorServer) => void;
  onDelete?: (server: MonitorServer) => void;
  onRetry?: (server: MonitorServer) => void;
}

function fmtRate(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  if (v < 1024) return `${v.toFixed(0)} B/s`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB/s`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB/s`;
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'online' ? 'bg-emerald-500' : status === 'offline' ? 'bg-red-500' : status === 'error' ? 'bg-orange-500' : 'bg-slate-600';
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

/** 服务器状态卡片：名称/状态/资源小指标/错误信息 */
export function ServerCard({ server, onSelect, onEdit, onDelete, onRetry }: ServerCardProps) {
  const metric = server.metric;
  const offline = server.status !== 'online';
  return (
    <div
      className="bg-slate-900 rounded-xl p-4 border border-slate-800 hover:border-slate-700 cursor-pointer transition-colors"
      onClick={() => onSelect(server.id)}
      data-testid={`server-card-${server.id}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <StatusDot status={server.status} />
          <span className="text-white text-sm font-medium truncate">{server.name}</span>
        </div>
        <span className="text-xs text-slate-500 shrink-0">{server.server_type === 'local' ? '本机' : server.host}</span>
      </div>
      {server.group_name && <div className="text-xs text-slate-600 mt-0.5">{server.group_name}</div>}
      {offline ? (
        <div className="mt-2">
          <div className="text-xs text-red-400/80 break-words">{server.last_error || '服务器离线'}</div>
          {server.status === 'error' && onRetry && (
            <button
              className="mt-2 text-xs text-emerald-400 hover:text-emerald-300"
              onClick={(e) => { e.stopPropagation(); onRetry(server); }}
            >
              重试采集
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-1.5 mt-2 text-xs">
          <div className="text-slate-400">CPU <span className="text-white">{metric?.cpu_percent ?? '-'}%</span></div>
          <div className="text-slate-400">内存 <span className="text-white">{metric?.mem_percent ?? '-'}%</span></div>
          <div className="text-slate-400">磁盘 <span className="text-white">{metric?.disk_percent ?? '-'}%</span></div>
          <div className="text-slate-400">网络 <span className="text-white">{fmtRate(metric?.net_recv_rate)}</span></div>
        </div>
      )}
      {!offline && server.last_seen_at && (
        <div className="text-[11px] text-slate-600 mt-2">最近采集 {server.last_seen_at.replace('T', ' ').slice(0, 19)}</div>
      )}
      {(onEdit || onDelete) && (
        <div className="flex gap-2 mt-2" onClick={(e) => e.stopPropagation()}>
          {onEdit && <button className="text-xs text-slate-400 hover:text-white" onClick={() => onEdit(server)}>编辑</button>}
          {onDelete && server.server_type !== 'local' && (
            <button className="text-xs text-slate-400 hover:text-red-400" onClick={() => onDelete(server)}>删除</button>
          )}
        </div>
      )}
    </div>
  );
}

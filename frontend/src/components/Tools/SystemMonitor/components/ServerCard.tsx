// frontend/src/components/Tools/SystemMonitor/components/ServerCard.tsx
import type { MonitorServer } from '../../../../api/monitorApi';
import { Card } from '@/components/ui/Card';

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
  const color = status === 'online' ? 'bg-success' : status === 'offline' ? 'bg-danger' : status === 'error' ? 'bg-accent-warm' : 'bg-surface-3';
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

/** 服务器状态卡片：名称/状态/资源小指标/错误信息 */
export function ServerCard({ server, onSelect, onEdit, onDelete, onRetry }: ServerCardProps) {
  const metric = server.metric;
  const offline = server.status !== 'online';
  return (
    <Card
      className="bg-canvas p-4 hover:border-border cursor-pointer transition-colors"
      onClick={() => onSelect(server.id)}
      data-testid={`server-card-${server.id}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <StatusDot status={server.status} />
          <span className="text-ink text-sm font-medium truncate">{server.name}</span>
        </div>
        <span className="text-xs text-ink-faint shrink-0">{server.server_type === 'local' ? '本机' : server.host}</span>
      </div>
      {server.group_name && <div className="text-xs text-ink-faint mt-0.5">{server.group_name}</div>}
      {offline ? (
        <div className="mt-2">
          <div className="text-xs text-danger/80 break-words">{server.last_error || '服务器离线'}</div>
          {server.status === 'error' && onRetry && (
            <button
              className="mt-2 text-xs text-success hover:text-success"
              onClick={(e) => { e.stopPropagation(); onRetry(server); }}
            >
              重试采集
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-1.5 mt-2 text-xs">
          <div className="text-ink-muted">CPU <span className="text-ink">{metric?.cpu_percent ?? '-'}%</span></div>
          <div className="text-ink-muted">内存 <span className="text-ink">{metric?.mem_percent ?? '-'}%</span></div>
          <div className="text-ink-muted">磁盘 <span className="text-ink">{metric?.disk_percent ?? '-'}%</span></div>
          <div className="text-ink-muted">网络 <span className="text-ink">{fmtRate(metric?.net_recv_rate)}</span></div>
        </div>
      )}
      {!offline && server.last_seen_at && (
        <div className="text-[11px] text-ink-faint mt-2">最近采集 {server.last_seen_at.replace('T', ' ').slice(0, 19)}</div>
      )}
      {(onEdit || onDelete) && (
        <div className="flex gap-2 mt-2" onClick={(e) => e.stopPropagation()}>
          {onEdit && <button className="text-xs text-ink-muted hover:text-ink" onClick={() => onEdit(server)}>编辑</button>}
          {onDelete && server.server_type !== 'local' && (
            <button className="text-xs text-ink-muted hover:text-danger" onClick={() => onDelete(server)}>删除</button>
          )}
        </div>
      )}
    </Card>
  );
}

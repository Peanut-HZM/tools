/**
 * 请求历史面板
 */

import { RequestHistory } from '../../../../services/httpClientApi';
import { Loader2, History, Trash2, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface HistoryPanelProps {
  history: RequestHistory[];
  loading: boolean;
  onReplay: (item: RequestHistory) => void;
  onClear: () => void;
}

export default function HistoryPanel({ history, loading, onReplay, onClear }: HistoryPanelProps) {
  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 300 && status < 400) return 'text-accent-warning';
    if (status >= 400 && status < 500) return 'text-orange-400';
    if (status >= 500) return 'text-danger';
    return 'text-ink-muted';
  };

  const getMethodBadgeVariant = (method: string): 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
      GET: 'success',
      POST: 'default',
      PUT: 'warning',
      DELETE: 'destructive',
      PATCH: 'secondary',
    };
    return variants[method] || 'secondary';
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    return date.toLocaleDateString('zh-CN');
  };

  if (loading) {
    return (
      <div className="text-center py-8 text-ink-faint text-sm">
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        加载历史中...
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="text-center py-12 text-ink-faint">
        <History className="w-10 h-10 mb-3 opacity-30" />
        <p className="text-sm">暂无请求历史</p>
        <p className="text-xs mt-1 text-ink-faint">发送的请求将自动记录在这里</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-ink-muted">共 {history.length} 条记录</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          className="text-xs text-danger hover:text-red-300"
        >
          <Trash2 className="w-4 h-4 mr-1" />
          清空历史
        </Button>
      </div>

      <div className="max-h-[60vh] overflow-y-auto space-y-1">
        {history.map(item => (
          <div
            key={item.id}
            onClick={() => onReplay(item)}
            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer
                       hover:bg-surface-2/50 transition-colors text-sm group"
          >
            {/* 状态码 */}
            <span className={`font-mono font-bold text-xs w-10 text-center ${getStatusColor(item.status_code)}`}>
              {item.status_code || '-'}
            </span>

            {/* 方法 */}
            <Badge variant={getMethodBadgeVariant(item.method)} className="font-mono">
              {item.method}
            </Badge>

            {/* URL */}
            <span className="flex-1 text-ink-muted truncate text-xs font-mono" title={item.url}>
              {item.url}
            </span>

            {/* 响应时间 */}
            <span className="text-xs text-ink-faint font-mono w-16 text-right">
              {item.response_time}ms
            </span>

            {/* 时间 */}
            <span className="text-xs text-ink-faint w-20 text-right">
              {formatTime(item.timestamp)}
            </span>

            {/* 重放按钮 */}
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                onReplay(item);
              }}
              className="h-6 w-6 text-ink-faint group-hover:text-accent-secondary opacity-0 group-hover:opacity-100"
              title="重放"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

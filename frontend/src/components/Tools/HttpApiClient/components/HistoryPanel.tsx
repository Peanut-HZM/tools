/**
 * 请求历史面板
 */

import { useMemo, useState } from 'react';
import { RequestHistory } from '../../../../services/httpClientApi';
import { Loader2, History, Trash2, RotateCw, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';

interface HistoryPanelProps {
  history: RequestHistory[];
  loading: boolean;
  onReplay: (item: RequestHistory) => void;
  onClear: () => void;
  onDeleteItem?: (id: string) => void;
}

export default function HistoryPanel({ history, loading, onReplay, onClear, onDeleteItem }: HistoryPanelProps) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return history;
    const kw = search.trim().toLowerCase();
    return history.filter(item =>
      item.url.toLowerCase().includes(kw) || item.method.toLowerCase().includes(kw)
    );
  }, [history, search]);

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-success';
    if (status >= 300 && status < 400) return 'text-accent-warning';
    if (status >= 400 && status < 500) return 'text-warning';
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
      <div className="flex items-center gap-2 mb-3">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-ink-faint absolute left-3 top-1/2 -translate-y-1/2" />
          <Input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="按 URL 或方法过滤..."
            className="h-8 text-xs pl-8 pr-7"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          className="text-xs text-danger hover:text-danger h-8"
        >
          <Trash2 className="w-3.5 h-3.5 mr-1" />
          清空
        </Button>
      </div>

      <div className="text-xs text-ink-faint mb-1">
        共 {filtered.length} 条记录{search && `（筛选自 ${history.length} 条）`}
      </div>

      <div className="max-h-[55vh] overflow-y-auto space-y-1">
        {filtered.length === 0 ? (
          <div className="text-center py-8 text-ink-faint text-sm">无匹配的历史记录</div>
        ) : (
          filtered.map(item => (
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
                title="重放到新标签页"
              >
                <RotateCw className="w-4 h-4" />
              </Button>

              {/* 单条删除按钮 */}
              {onDeleteItem && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteItem(item.id);
                  }}
                  className="h-6 w-6 text-ink-faint group-hover:text-danger opacity-0 group-hover:opacity-100"
                  title="删除此记录"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/**
 * 请求历史面板
 */

import { RequestHistory } from '../../../../services/httpClientApi';

interface HistoryPanelProps {
  history: RequestHistory[];
  loading: boolean;
  onReplay: (item: RequestHistory) => void;
  onClear: () => void;
}

export default function HistoryPanel({ history, loading, onReplay, onClear }: HistoryPanelProps) {
  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 300 && status < 400) return 'text-yellow-400';
    if (status >= 400 && status < 500) return 'text-orange-400';
    if (status >= 500) return 'text-red-400';
    return 'text-slate-400';
  };

  const getMethodBadge = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'bg-green-500/20 text-green-400',
      POST: 'bg-blue-500/20 text-blue-400',
      PUT: 'bg-yellow-500/20 text-yellow-400',
      DELETE: 'bg-red-500/20 text-red-400',
      PATCH: 'bg-purple-500/20 text-purple-400',
    };
    return colors[method] || 'bg-slate-500/20 text-slate-400';
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
      <div className="text-center py-8 text-slate-500 text-sm">
        <i className="fas fa-spinner fa-spin mr-2"></i>
        加载历史中...
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <i className="fas fa-clock-rotate-left text-4xl mb-3 opacity-30"></i>
        <p className="text-sm">暂无请求历史</p>
        <p className="text-xs mt-1 text-slate-600">发送的请求将自动记录在这里</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-slate-400">共 {history.length} 条记录</span>
        <button
          onClick={onClear}
          className="text-xs text-red-400 hover:text-red-300 transition-colors"
        >
          <i className="fas fa-trash mr-1"></i>
          清空历史
        </button>
      </div>

      <div className="max-h-[60vh] overflow-y-auto space-y-1">
        {history.map(item => (
          <div
            key={item.id}
            onClick={() => onReplay(item)}
            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer
                       hover:bg-slate-700/50 transition-colors text-sm group"
          >
            {/* 状态码 */}
            <span className={`font-mono font-bold text-xs w-10 text-center ${getStatusColor(item.status_code)}`}>
              {item.status_code || '-'}
            </span>

            {/* 方法 */}
            <span className={`px-1.5 py-0.5 rounded text-xs font-mono font-bold ${getMethodBadge(item.method)}`}>
              {item.method}
            </span>

            {/* URL */}
            <span className="flex-1 text-slate-300 truncate text-xs font-mono" title={item.url}>
              {item.url}
            </span>

            {/* 响应时间 */}
            <span className="text-xs text-slate-500 font-mono w-16 text-right">
              {item.response_time}ms
            </span>

            {/* 时间 */}
            <span className="text-xs text-slate-600 w-20 text-right">
              {formatTime(item.timestamp)}
            </span>

            {/* 重放按钮 */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onReplay(item);
              }}
              className="text-slate-600 group-hover:text-purple-400 transition-colors opacity-0 group-hover:opacity-100"
              title="重放"
            >
              <i className="fas fa-rotate-right"></i>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

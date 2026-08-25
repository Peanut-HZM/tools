import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../../../api/databaseToolApi';
import { ExecutionHistory } from '../../../../types/databaseTool';
import { useToast } from '../../../../hooks/useToast';
import { useI18n } from '../../../../i18n';

interface SQLHistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onReuseSql: (sql: string) => void;
}

const SQLHistoryPanel: React.FC<SQLHistoryPanelProps> = ({ isOpen, onClose, onReuseSql }) => {
  const { t } = useI18n();
  const toast = useToast();
  const [history, setHistory] = useState<ExecutionHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getHistory(100, 0);
      setHistory(data);
    } catch (error: any) {
      toast.error(`加载历史记录失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, fetchHistory]);

  const handleReuse = (item: ExecutionHistory) => {
    onReuseSql(item.sql_statement);
  };

  const getStatusIcon = (status: string) => {
    if (status === 'success') return <i className="fas fa-check-circle text-green-400"></i>;
    if (status === 'failed') return <i className="fas fa-times-circle text-danger"></i>;
    return <i className="fas fa-clock text-accent-warning"></i>;
  };

  const getSqlTypeColor = (type?: string) => {
    if (!type) return 'text-ink-muted';
    const t = type.toUpperCase();
    if (t === 'SELECT') return 'text-accent-info';
    if (t === 'INSERT') return 'text-green-400';
    if (t === 'UPDATE') return 'text-accent-warning';
    if (t === 'DELETE') return 'text-danger';
    return 'text-ink-muted';
  };

  const filteredHistory = history.filter(item => {
    const matchesSearch = !searchTerm || 
      item.sql_statement.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.db_alias && item.db_alias.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesType = filterType === 'all' || item.sql_type?.toUpperCase() === filterType;
    
    return matchesSearch && matchesType;
  });

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  if (!isOpen) return null;

  return (
    <div className="flex flex-col h-full bg-surface-1 border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-1">
        <div className="flex items-center gap-2">
          <i className="fas fa-history text-ink-muted"></i>
          <span className="text-sm font-medium text-ink">SQL 历史记录</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-surface-2 rounded text-ink-muted hover:text-ink transition-colors"
        >
          <i className="fas fa-times text-xs"></i>
        </button>
      </div>

      {/* Search and Filter */}
      <div className="px-4 py-2 border-b border-border space-y-2 bg-surface-1">
        <div className="relative">
          <i className="fas fa-search absolute left-2 top-1/2 -translate-y-1/2 text-ink-faint text-xs"></i>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索 SQL 或连接..."
            className="w-full bg-canvas border border-border rounded pl-7 pr-2 py-1.5 text-xs text-ink focus:outline-none focus:border-accent"
          />
        </div>
        <div className="flex gap-1">
          {['all', 'SELECT', 'INSERT', 'UPDATE', 'DELETE'].map(type => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-2 py-1 text-[10px] rounded transition-colors ${
                filterType === type 
                  ? 'bg-accent text-ink-inverse' 
                  : 'bg-surface-2 text-ink-muted hover:text-ink'
              }`}
            >
              {type === 'all' ? '全部' : type}
            </button>
          ))}
        </div>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full text-ink-faint">
            <i className="fas fa-spinner fa-spin mr-2"></i>
            加载中...
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-ink-faint py-8">
            <i className="fas fa-history text-3xl mb-2 opacity-30"></i>
            <p className="text-xs">暂无历史记录</p>
          </div>
        ) : (
          <div className="py-2">
            {filteredHistory.map(item => (
              <div
                key={item.id}
                className="group px-4 py-2.5 hover:bg-surface-2/50 cursor-pointer border-b border-border/50 last:border-0 transition-colors"
                onClick={() => handleReuse(item)}
              >
                {/* Header Row */}
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    {getStatusIcon(item.execution_status)}
                    <span className={`text-[10px] font-medium ${getSqlTypeColor(item.sql_type)}`}>
                      {item.sql_type || 'UNKNOWN'}
                    </span>
                    {item.db_alias && (
                      <span className="text-[10px] text-ink-faint">@ {item.db_alias}</span>
                    )}
                  </div>
                  <span className="text-[10px] text-ink-faint">{formatTime(item.created_at)}</span>
                </div>
                
                {/* SQL Preview */}
                <div className="text-[11px] text-ink-muted font-mono truncate">
                  {item.sql_statement}
                </div>
                
                {/* Meta Info */}
                <div className="flex items-center gap-3 mt-1 text-[10px] text-ink-faint">
                  {item.affected_rows !== null && item.affected_rows !== undefined && (
                    <span>{item.affected_rows} 行</span>
                  )}
                  {item.execution_time_ms && (
                    <span>{item.execution_time_ms}ms</span>
                  )}
                  {item.error_message && (
                    <span className="text-danger truncate">{item.error_message}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SQLHistoryPanel;

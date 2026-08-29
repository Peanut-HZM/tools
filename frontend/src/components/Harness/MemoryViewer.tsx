/**
 * MemoryViewer — Agent 长期记忆查看器
 *
 * Phase 3-Plan-1B / Task 7
 * 功能：
 *  - 列出当前用户对指定 Agent 的所有记忆
 *  - 向量搜索记忆（后端自动降级为关键词）
 *  - 删除指定记忆
 *  - 显示每条记忆的重要度、访问次数、是否已向量化
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  harnessMemoriesApi,
  MemoryEntry,
  MemorySearchResult,
} from '../../api/harnessMemoriesApi';

interface MemoryViewerProps {
  agentId: string;
}

export const MemoryViewer: React.FC<MemoryViewerProps> = ({ agentId }) => {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState('');

  const loadMemories = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const result = await harnessMemoriesApi.list(agentId);
      setMemories(result.records);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '加载记忆失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (agentId) {
      loadMemories();
    }
  }, [loadMemories, agentId]);

  const handleDelete = async (key: string) => {
    if (!window.confirm(`确定要删除记忆 "${key}" 吗？此操作不可恢复。`)) return;
    try {
      setError('');
      await harnessMemoriesApi.delete(agentId, key);
      setMemories((prev) => prev.filter((m) => m.key !== key));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '删除失败';
      setError(message);
    }
  };

  const handleSearch = async () => {
    const trimmedQuery = searchQuery.trim();
    if (!trimmedQuery) {
      setIsSearching(false);
      loadMemories();
      return;
    }
    try {
      setLoading(true);
      setIsSearching(true);
      setError('');
      const result = await harnessMemoriesApi.search(agentId, trimmedQuery);
      // 将搜索结果转换为 MemoryEntry 格式以复用渲染逻辑
      const mapped: MemoryEntry[] = result.records.map((r: MemorySearchResult) => ({
        key: r.key,
        value: r.value,
        importance: 0.5,
        access_count: 0,
        summary: r.summary,
        has_embedding: true,
      }));
      setMemories(mapped);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '搜索失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSearchQuery('');
    setIsSearching(false);
    loadMemories();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  };

  return (
    <div className="space-y-4">
      {/* 搜索栏 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="搜索记忆（支持自然语言描述或关键词）"
          className="flex-1 px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
          aria-label="搜索记忆"
        />
        <button
          type="button"
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          搜索
        </button>
        <button
          type="button"
          onClick={handleReset}
          disabled={loading || !isSearching}
          className="px-4 py-2 bg-surface-2 hover:bg-surface-3 text-ink rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          重置
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="text-danger text-sm bg-danger/10 border border-danger/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-accent"></div>
          <span className="text-ink-muted ml-2">加载中...</span>
        </div>
      )}

      {/* 空状态 */}
      {!loading && memories.length === 0 && (
        <div className="bg-surface-2 rounded-lg p-8 text-center border border-border">
          <div className="text-4xl mb-2">🧠</div>
          <div className="text-ink-muted">
            {isSearching ? '未找到匹配的记忆' : '暂无记忆'}
          </div>
        </div>
      )}

      {/* 记忆列表 */}
      {!loading && memories.length > 0 && (
        <div className="space-y-2">
          {isSearching && (
            <div className="text-xs text-ink-faint mb-2">
              找到 {memories.length} 条相关记忆
            </div>
          )}
          {memories.map((m) => (
            <div
              key={m.key}
              className="border border-border rounded-lg p-3 flex justify-between items-start gap-3 hover:bg-surface-2/50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-ink truncate">
                  {m.key}
                </div>
                <div className="text-sm text-ink-muted mt-1 break-words whitespace-pre-wrap">
                  {formatValue(m.value)}
                </div>
                {m.summary && (
                  <div className="text-xs text-ink-faint mt-1 italic">
                    {m.summary}
                  </div>
                )}
                <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs text-ink-faint">
                  <span>重要度: {m.importance.toFixed(2)}</span>
                  <span>访问 {m.access_count} 次</span>
                  <span>
                    {m.has_embedding ? (
                      <span className="text-success">✅ 已向量化</span>
                    ) : (
                      <span className="text-warning">⏳ 待向量化</span>
                    )}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(m.key)}
                disabled={loading}
                className="shrink-0 px-3 py-1 text-xs text-danger border border-danger/30 rounded hover:bg-danger/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label={`删除记忆 ${m.key}`}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

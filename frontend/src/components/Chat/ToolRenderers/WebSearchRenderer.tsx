/**
 * WebSearch 工具渲染器
 *
 * 显示搜索 query 和结果列表（标题 + 链接 + 摘要）。
 * - call.arguments.query: 搜索关键词
 * - result.content: 兼容两种格式：
 *     1. 字符串（直接展示）
 *     2. { results: Array<{ title, url, snippet }> }
 */
import React from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';

interface WebSearchResult {
  title?: string;
  url?: string;
  snippet?: string;
}

interface WebSearchContent {
  results?: WebSearchResult[];
}

export const WebSearchRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const query = (call.arguments?.query as string | undefined) ?? '';

  // 解析 result.content（兼容字符串和对象两种形态）
  const results = React.useMemo<WebSearchResult[]>(() => {
    if (!result) return [];
    const content = result.content;
    if (typeof content === 'string') {
      // 字符串形式：尝试解析为 JSON，否则作为单条结果
      try {
        const parsed = JSON.parse(content) as WebSearchContent;
        return parsed.results ?? [];
      } catch {
        return [{ snippet: content }];
      }
    }
    if (content && typeof content === 'object') {
      const obj = content as WebSearchContent;
      if (Array.isArray(obj.results)) return obj.results;
    }
    return [];
  }, [result]);

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部：工具名 + query */}
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-info/10 text-accent-info">
          web_search
        </span>
        <span className="text-ink-faint dark:text-ink-muted">搜索：</span>
        <span className="font-medium text-ink dark:text-ink-inverse truncate">
          {query || '（无 query）'}
        </span>
      </div>

      {/* 状态：执行中 */}
      {pending && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          正在执行搜索...
        </div>
      )}

      {/* 状态：失败 */}
      {result && !result.success && (
        <div className="text-danger text-xs py-2">
          搜索失败：{result.error ?? '未知错误'}
        </div>
      )}

      {/* 状态：成功 + 结果列表 */}
      {result?.success && results.length > 0 && (
        <ul className="space-y-2 mt-1">
          {results.map((item, idx) => (
            <li
              key={idx}
              className="border-l-2 border-surface-2 pl-3 py-1"
            >
              {item.title && (
                <div className="font-medium text-ink dark:text-ink-inverse">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline"
                    >
                      {item.title}
                    </a>
                  ) : (
                    item.title
                  )}
                </div>
              )}
              {item.url && !item.title && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-info hover:underline text-xs break-all"
                >
                  {item.url}
                </a>
              )}
              {item.snippet && (
                <div className="text-ink-faint dark:text-ink-muted text-xs mt-0.5">
                  {item.snippet}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* 成功但无结果 */}
      {result?.success && results.length === 0 && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          未返回结果
        </div>
      )}
    </div>
  );
};

export default WebSearchRenderer;

/**
 * DbQuery 工具渲染器
 *
 * 显示 SQL + 可展开的结果表。
 * - call.arguments.sql / call.arguments.query: SQL 语句
 * - result.content: 兼容两种格式：
 *     1. 字符串：作为简化文本结果展示
 *     2. { columns: string[], rows: any[][] }：表格展示
 */
import React from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';

interface DbQueryContent {
  columns?: string[];
  rows?: Array<Array<unknown>>;
}

export const DbQueryRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const sql =
    (call.arguments?.sql as string | undefined) ??
    (call.arguments?.query as string | undefined) ??
    '';

  const [expanded, setExpanded] = React.useState(false);

  // 解析 result.content
  const parsed = React.useMemo<DbQueryContent>(() => {
    if (!result) return {};
    const content = result.content;
    if (typeof content === 'string') {
      try {
        return JSON.parse(content) as DbQueryContent;
      } catch {
        return {};
      }
    }
    if (content && typeof content === 'object') {
      return content as DbQueryContent;
    }
    return {};
  }, [result]);

  const hasTable = Array.isArray(parsed.columns) && Array.isArray(parsed.rows);

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部：工具名 + SQL */}
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-info/10 text-accent-info">
          db_query
        </span>
        <span className="text-ink-faint dark:text-ink-muted">SQL：</span>
      </div>

      {/* SQL 代码块 */}
      {sql && (
        <pre className="bg-surface-2 dark:bg-surface-1 text-ink dark:text-ink-inverse text-xs p-2 rounded overflow-x-auto mb-2 whitespace-pre-wrap break-words">
          {sql}
        </pre>
      )}

      {/* 状态：执行中 */}
      {pending && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          正在执行查询...
        </div>
      )}

      {/* 状态：失败 */}
      {result && !result.success && (
        <div className="text-danger text-xs py-2">
          查询失败：{result.error ?? '未知错误'}
        </div>
      )}

      {/* 状态：成功 + 可展开结果 */}
      {result?.success && hasTable && (
        <div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-accent-info hover:underline mb-2"
          >
            {expanded ? '收起结果' : `展开结果（共 ${parsed.rows!.length} 行）`}
          </button>
          {expanded && (
            <div className="overflow-x-auto max-h-80 overflow-y-auto border border-surface-2 rounded">
              <table className="w-full text-xs">
                <thead className="bg-surface-2 dark:bg-surface-1 sticky top-0">
                  <tr>
                    {parsed.columns!.map((col, idx) => (
                      <th
                        key={idx}
                        className="text-left px-2 py-1 font-medium text-ink dark:text-ink-inverse border-b border-surface-2"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {parsed.rows!.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="even:bg-surface-1/50 dark:even:bg-surface-1/30"
                    >
                      {parsed.columns!.map((_col, cIdx) => (
                        <td
                          key={cIdx}
                          className="px-2 py-1 border-b border-surface-2/50 text-ink dark:text-ink-inverse break-words"
                        >
                          {formatCell(row[cIdx])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 成功但无可表格化结果 */}
      {result?.success && !hasTable && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          {typeof result.content === 'string' && result.content
            ? result.content
            : '查询成功'}
        </div>
      )}
    </div>
  );
};

/** 单元格格式化（null/undefined/object 都用可读字符串） */
function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

export default DbQueryRenderer;

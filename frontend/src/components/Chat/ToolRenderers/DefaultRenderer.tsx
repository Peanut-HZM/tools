/**
 * DefaultRenderer — 未知工具的回退渲染
 *
 * 显示工具名 + arguments + 可展开的 result JSON。
 */
import React from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';

export const DefaultRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const [expanded, setExpanded] = React.useState(false);

  const argsText = React.useMemo(() => {
    try {
      return JSON.stringify(call.arguments ?? {}, null, 2);
    } catch {
      return String(call.arguments ?? '');
    }
  }, [call.arguments]);

  const resultText = React.useMemo(() => {
    if (!result) return '';
    try {
      return JSON.stringify(
        {
          success: result.success,
          content_type: result.content_type,
          content: result.content,
          error: result.error,
          attachments: result.attachments,
        },
        null,
        2
      );
    } catch {
      return String(result.content ?? '');
    }
  }, [result]);

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部：工具名 + 状态徽标 */}
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-2 text-ink-faint dark:text-ink-muted">
          {call.name || 'unknown'}
        </span>
        <StatusBadge result={result} pending={pending} />
      </div>

      {/* arguments 摘要 */}
      <div className="mb-2">
        <div className="text-xs text-ink-faint dark:text-ink-muted mb-1">参数：</div>
        <pre className="bg-surface-2 dark:bg-surface-1 text-ink dark:text-ink-inverse text-xs p-2 rounded overflow-x-auto max-h-40 whitespace-pre-wrap break-words">
          {argsText}
        </pre>
      </div>

      {/* result（可展开） */}
      {result && (
        <div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-accent-info hover:underline mb-1"
          >
            {expanded ? '收起结果' : '展开结果'}
          </button>
          {expanded && (
            <pre className="bg-surface-2 dark:bg-surface-1 text-ink dark:text-ink-inverse text-xs p-2 rounded overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap break-words">
              {resultText}
            </pre>
          )}
        </div>
      )}

      {/* 无 result + pending */}
      {!result && pending && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          正在执行...
        </div>
      )}
    </div>
  );
};

/** 状态徽标：成功 / 失败 / 执行中 */
const StatusBadge: React.FC<{ result?: ToolRendererProps['result']; pending?: boolean }> = ({
  result,
  pending,
}) => {
  if (pending && !result) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-accent-warn/10 text-accent-warn">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-warn animate-pulse" />
        执行中
      </span>
    );
  }
  if (!result) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-2 text-ink-faint">
        等待
      </span>
    );
  }
  if (!result.success) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-danger/10 text-danger">
        失败
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-success/10 text-accent-success">
      成功
    </span>
  );
};

export default DefaultRenderer;

/**
 * Memory 工具渲染器
 *
 * 同时处理 memory_read / memory_write 两个工具。
 *
 * memory_read：
 * - 单条读取（call.arguments.key 存在）：
 *   - result.content 是 dict 且 value 非 null：显示 key + value JSON + summary + updated_at
 *   - result.content 是 dict 且 value 为 null：「未找到该记忆条目」
 * - 列表读取（call.arguments.key 不存在）：
 *   - result.content.records 为空数组：「暂无记忆」
 *   - result.content.records 非空：「共 N 条记忆」+ 列表（前 20 条 + 「...还有 N 条」）
 * - 失败：显示 error message
 *
 * memory_write：
 * - result.content.action 为 "created" → 显示「新建」badge + key
 * - result.content.action 为 "updated" → 显示「更新」badge + key
 * - 失败：显示 error message
 *
 * 共用：
 * - 顶部：工具名 badge + 执行中提示
 * - pending 状态：「正在读取/写入记忆...」
 * - 失败状态：错误信息
 *
 * 安全：纯文本渲染，不引入 URL 渲染（无需 safeHref）。
 */
import React from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';

/** action -> 中文标签 */
const ACTION_LABELS: Record<string, string> = {
  created: '新建',
  updated: '更新',
};

/** 单条记忆记录 */
interface MemoryRecord {
  key?: string;
  value?: unknown;
  summary?: string | null;
  updated_at?: string | null;
}

/** memory_read 单条结果 */
interface MemoryReadSingleContent extends MemoryRecord {
  key?: string;
  value?: unknown;
}

/** memory_read 列表结果 */
interface MemoryReadListContent {
  records?: MemoryRecord[];
  count?: number;
}

/** memory_write 结果 */
interface MemoryWriteContent {
  action?: string;
  key?: string;
}

/** 解析 result.content（兼容 string / object） */
function parseContent(raw: unknown): unknown {
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  }
  return raw;
}

export const MemoryRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const isWrite = call.name === 'memory_write';
  const parsed = React.useMemo(() => parseContent(result?.content), [result]);

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部：工具名 badge */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-info/10 text-accent-info">
          {call.name}
        </span>
      </div>

      {/* 执行中（pending 且尚无 result 时显示，已有 result 时由 StatusLine 接管） */}
      {pending && !result && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-3">
          {isWrite ? '正在写入记忆...' : '正在读取记忆...'}
        </div>
      )}

      {/* 失败 */}
      {result && !result.success && (
        <div className="text-danger text-xs py-2">
          {isWrite ? '写入失败' : '读取失败'}：{result.error ?? '未知错误'}
        </div>
      )}

      {/* 成功：按工具分派渲染 */}
      {result?.success && (isWrite ? renderWrite(parsed) : renderRead(call, parsed))}
    </div>
  );
};

/**
 * memory_read 渲染分派
 */
function renderRead(
  call: { arguments?: Record<string, unknown> },
  parsed: unknown
): React.ReactNode {
  const hasKeyArg = typeof call.arguments?.key === 'string' && (call.arguments.key as string).length > 0;

  // 列表读取模式：call.arguments.key 不存在 → 期望 parsed 是 {records, count}
  if (!hasKeyArg) {
    return renderReadList(parsed as MemoryReadListContent | null);
  }

  // 单条读取模式
  return renderReadSingle(parsed as MemoryReadSingleContent | null);
}

/**
 * memory_read 单条记录渲染
 */
function renderReadSingle(parsed: MemoryReadSingleContent | null): React.ReactNode {
  if (!parsed || typeof parsed !== 'object') {
    return (
      <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
        暂无数据
      </div>
    );
  }

  const { key, value, summary, updated_at } = parsed;
  const isMissing = value === null || value === undefined;

  // value 为 null → 未找到
  if (isMissing) {
    return (
      <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
        未找到该记忆条目{key ? `（key: ${key}）` : ''}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* key 行 */}
      {key && (
        <div className="flex items-center gap-2 text-xs">
          <span className="text-ink-faint dark:text-ink-muted">key：</span>
          <code className="px-1.5 py-0.5 rounded bg-surface-2 text-ink dark:text-ink-inverse break-all">
            {key}
          </code>
        </div>
      )}

      {/* value JSON */}
      <pre className="bg-surface-2 dark:bg-surface-1 text-ink dark:text-ink-inverse text-xs p-2 rounded overflow-x-auto whitespace-pre-wrap break-words">
        {JSON.stringify(value, null, 2)}
      </pre>

      {/* summary + updated_at */}
      {(summary || updated_at) && (
        <div className="text-xs text-ink-faint dark:text-ink-muted space-y-0.5">
          {summary && <div>摘要：{summary}</div>}
          {updated_at && <div>更新时间：{updated_at}</div>}
        </div>
      )}
    </div>
  );
}

/**
 * memory_read 列表渲染
 */
function renderReadList(parsed: MemoryReadListContent | null): React.ReactNode {
  const records = parsed?.records;
  const count = parsed?.count ?? (Array.isArray(records) ? records.length : 0);

  // 空列表
  if (!Array.isArray(records) || records.length === 0) {
    return (
      <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
        暂无记忆
      </div>
    );
  }

  const MAX_DISPLAY = 20;
  const displayRecords = records.slice(0, MAX_DISPLAY);
  const remaining = records.length - displayRecords.length;

  return (
    <div className="space-y-2">
      <div className="text-xs text-ink-faint dark:text-ink-muted">
        共 {count} 条记忆
      </div>

      <ul className="space-y-1.5">
        {displayRecords.map((rec, idx) => (
          <li
            key={idx}
            className="border-l-2 border-surface-2 pl-2 py-1 text-xs"
          >
            <div className="flex items-center gap-2 flex-wrap">
              {rec.key && (
                <code className="px-1.5 py-0.5 rounded bg-surface-2 text-ink dark:text-ink-inverse">
                  {rec.key}
                </code>
              )}
              {rec.updated_at && (
                <span className="text-ink-faint dark:text-ink-muted">
                  {rec.updated_at}
                </span>
              )}
            </div>
            {rec.summary && (
              <div className="text-ink-faint dark:text-ink-muted mt-0.5">
                {rec.summary}
              </div>
            )}
          </li>
        ))}
      </ul>

      {remaining > 0 && (
        <div className="text-xs text-ink-faint dark:text-ink-muted italic">
          ...还有 {remaining} 条
        </div>
      )}
    </div>
  );
}

/**
 * memory_write 渲染
 */
function renderWrite(parsed: unknown): React.ReactNode {
  if (!parsed || typeof parsed !== 'object') {
    return (
      <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
        写入成功
      </div>
    );
  }

  const { action, key } = parsed as MemoryWriteContent;
  const actionLabel = action ? ACTION_LABELS[action] ?? action : '成功';

  // action badge 颜色：created 蓝/绿，updated 黄
  const badgeClass =
    action === 'created'
      ? 'bg-accent-success/10 text-accent-success'
      : action === 'updated'
        ? 'bg-accent-warn/10 text-accent-warn'
        : 'bg-surface-2 text-ink-faint';

  return (
    <div className="flex items-center gap-2 flex-wrap text-xs">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded font-medium ${badgeClass}`}
      >
        {actionLabel}
      </span>
      {key && (
        <>
          <span className="text-ink-faint dark:text-ink-muted">key：</span>
          <code className="px-1.5 py-0.5 rounded bg-surface-2 text-ink dark:text-ink-inverse break-all">
            {key}
          </code>
        </>
      )}
    </div>
  );
}

export default MemoryRenderer;

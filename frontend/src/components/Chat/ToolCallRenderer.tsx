/**
 * ToolCallRenderer — 工具调用渲染分发组件
 *
 * 优先级：
 *   1. registry.getRenderer(call.name) — 通过 useToolRegistryStore 注册的自定义渲染器
 *   2. builtinRenderers[call.name]    — 内置渲染器（web_search、db_query）
 *   3. DefaultRenderer                — 最终回退
 *
 * 状态显示：
 *   - result 为空且 pending=true：执行中
 *   - result.success=false：失败（红色徽标）
 *   - result.success=true：成功
 */
import React from 'react';
import { useToolRegistryStore } from '@/stores/useToolRegistry';
import type { ToolRendererProps } from '@/stores/useToolRegistry';
import type { ToolCall, ToolResult } from '@/types/tool';
import { WebSearchRenderer } from './ToolRenderers/WebSearchRenderer';
import { DbQueryRenderer } from './ToolRenderers/DbQueryRenderer';
import { ImageGenRenderer } from './ToolRenderers/ImageGenRenderer';
import { DefaultRenderer } from './ToolRenderers/DefaultRenderer';

export interface ToolCallRendererProps {
  call: ToolCall;
  /** 当前调用是否仍在执行（call 已发出但 result 尚未到达） */
  pending?: boolean;
  result?: ToolResult;
  /** 自定义 builtin 渲染器覆盖（测试 / 业务定制用） */
  builtinRenderers?: Record<string, React.ComponentType<ToolRendererProps>>;
}

/** 默认 builtin 渲染器映射表 */
const DEFAULT_BUILTINS: Record<string, React.ComponentType<ToolRendererProps>> = {
  web_search: WebSearchRenderer,
  db_query: DbQueryRenderer,
  image_gen: ImageGenRenderer,
};

export const ToolCallRenderer: React.FC<ToolCallRendererProps> = ({
  call,
  pending,
  result,
  builtinRenderers,
}) => {
  const getRenderer = useToolRegistryStore((s) => s.getRenderer);

  const CustomRenderer = getRenderer(call.name);
  const builtins = builtinRenderers ?? DEFAULT_BUILTINS;
  const BuiltinRenderer = builtins[call.name];
  const Renderer: React.ComponentType<ToolRendererProps> =
    CustomRenderer ?? BuiltinRenderer ?? DefaultRenderer;

  return (
    <div className="my-2" data-tool-name={call.name} data-tool-id={call.id}>
      {/* 顶部状态行（仅当无 result 或失败时显示默认状态徽标） */}
      <StatusLine call={call} result={result} pending={pending} />
      <Renderer call={call} result={result} pending={pending} />
    </div>
  );
};

/** 顶部状态行：tool_name + 状态徽标 */
const StatusLine: React.FC<{
  call: ToolCall;
  result?: ToolResult;
  pending?: boolean;
}> = ({ call, result, pending }) => {
  return (
    <div className="flex items-center gap-2 mb-1 text-xs">
      <span className="text-ink-faint dark:text-ink-muted">工具调用：</span>
      <code className="px-1.5 py-0.5 rounded bg-surface-2 text-ink dark:text-ink-inverse">
        {call.name}
      </code>
      <StatusBadge result={result} pending={pending} />
    </div>
  );
};

const StatusBadge: React.FC<{ result?: ToolResult; pending?: boolean }> = ({
  result,
  pending,
}) => {
  if (pending && !result) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-medium bg-accent-warn/10 text-accent-warn">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-warn animate-pulse" />
        执行中
      </span>
    );
  }
  if (!result) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded font-medium bg-surface-2 text-ink-faint">
        等待
      </span>
    );
  }
  if (!result.success) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded font-medium bg-danger/10 text-danger">
        失败
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded font-medium bg-accent-success/10 text-accent-success">
      成功
    </span>
  );
};

export default ToolCallRenderer;

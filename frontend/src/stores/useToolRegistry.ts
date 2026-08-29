/**
 * 工具渲染器注册表（Zustand）
 *
 * 用于前端 Chat 区域根据 toolCall.name 选择对应渲染器。
 * - registerRenderer: 注册一个 toolName -> React 组件的映射
 * - getRenderer:      查询 toolName 对应的组件；未注册返回 undefined
 * - builtinRenderers:  内置工具渲染器（web_search、db_query 等）由各渲染器模块在加载时自动注册
 *
 * 设计：
 * - 不在 store 中存 builtinRenderers（避免循环依赖），仅由 ToolCallRenderer 查询时合并
 * - 业务模块可在 useEffect 中调用 registerRenderer 注册自定义渲染器
 */
import { create } from 'zustand';
import type { ComponentType } from 'react';
import type { ToolCall, ToolResult } from '@/types/tool';

/** 所有工具渲染器的统一 props */
export interface ToolRendererProps {
  call: ToolCall;
  result?: ToolResult;
  /** 执行中（call 已发出但 result 尚未到达） */
  pending?: boolean;
}

/** 渲染器组件类型 */
export type ToolRendererComponent = ComponentType<ToolRendererProps>;

interface ToolRegistryState {
  /** 已注册的渲染器映射表 */
  renderers: Record<string, ToolRendererComponent>;
  /** 注册渲染器（同名覆盖） */
  registerRenderer: (toolName: string, component: ToolRendererComponent) => void;
  /** 批量注册 */
  registerRenderers: (
    entries: Record<string, ToolRendererComponent>
  ) => void;
  /** 注销单个渲染器 */
  unregisterRenderer: (toolName: string) => void;
  /** 清空所有渲染器 */
  clearRenderers: () => void;
  /** 查询渲染器（未注册返回 undefined） */
  getRenderer: (toolName: string) => ToolRendererComponent | undefined;
}

export const useToolRegistryStore = create<ToolRegistryState>((set, get) => ({
  renderers: {},

  registerRenderer: (toolName, component) =>
    set((state) => ({
      renderers: { ...state.renderers, [toolName]: component },
    })),

  registerRenderers: (entries) =>
    set((state) => ({
      renderers: { ...state.renderers, ...entries },
    })),

  unregisterRenderer: (toolName) =>
    set((state) => {
      if (!(toolName in state.renderers)) return state;
      const next = { ...state.renderers };
      delete next[toolName];
      return { renderers: next };
    }),

  clearRenderers: () => set({ renderers: {} }),

  getRenderer: (toolName) => get().renderers[toolName],
}));

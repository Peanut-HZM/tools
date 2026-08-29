/**
 * useToolRegistryStore 单元测试 — 渲染器注册 / 查询 / 注销
 */
import { describe, it, expect, beforeEach } from 'vitest';
import React from 'react';
import { useToolRegistryStore } from '../useToolRegistry';
import type { ToolRendererComponent } from '../useToolRegistry';

describe('useToolRegistryStore', () => {
  beforeEach(() => {
    // 每个用例前清空渲染器，保证测试独立
    useToolRegistryStore.getState().clearRenderers();
  });

  it('初始 renderers 为空对象', () => {
    expect(useToolRegistryStore.getState().renderers).toEqual({});
  });

  it('registerRenderer 注册后可通过 getRenderer 获取', () => {
    const Cmp: ToolRendererComponent = () => React.createElement('div', null, 'mock');

    useToolRegistryStore.getState().registerRenderer('web_search', Cmp);

    expect(useToolRegistryStore.getState().renderers['web_search']).toBe(Cmp);
    expect(useToolRegistryStore.getState().getRenderer('web_search')).toBe(Cmp);
  });

  it('getRenderer 未注册时返回 undefined', () => {
    expect(useToolRegistryStore.getState().getRenderer('unknown_tool')).toBeUndefined();
  });

  it('registerRenderer 同名覆盖', () => {
    const A: ToolRendererComponent = () => React.createElement('div', null, 'A');
    const B: ToolRendererComponent = () => React.createElement('div', null, 'B');

    useToolRegistryStore.getState().registerRenderer('web_search', A);
    useToolRegistryStore.getState().registerRenderer('web_search', B);

    expect(useToolRegistryStore.getState().getRenderer('web_search')).toBe(B);
  });

  it('registerRenderers 批量注册（保留已存在的 key）', () => {
    const A: ToolRendererComponent = () => React.createElement('div', null, 'A');
    const B: ToolRendererComponent = () => React.createElement('div', null, 'B');
    const C: ToolRendererComponent = () => React.createElement('div', null, 'C');

    useToolRegistryStore.getState().registerRenderer('web_search', A);
    useToolRegistryStore.getState().registerRenderers({
      web_search: A, // 保留
      db_query: B,
      custom_tool: C,
    });

    const state = useToolRegistryStore.getState();
    expect(state.getRenderer('web_search')).toBe(A);
    expect(state.getRenderer('db_query')).toBe(B);
    expect(state.getRenderer('custom_tool')).toBe(C);
  });

  it('unregisterRenderer 删除单个渲染器（不影响其他 key）', () => {
    const A: ToolRendererComponent = () => React.createElement('div', null, 'A');
    const B: ToolRendererComponent = () => React.createElement('div', null, 'B');

    useToolRegistryStore.getState().registerRenderers({
      web_search: A,
      db_query: B,
    });

    useToolRegistryStore.getState().unregisterRenderer('web_search');

    expect(useToolRegistryStore.getState().getRenderer('web_search')).toBeUndefined();
    expect(useToolRegistryStore.getState().getRenderer('db_query')).toBe(B);
  });

  it('unregisterRenderer 不存在的 key 是 no-op', () => {
    const A: ToolRendererComponent = () => React.createElement('div', null, 'A');
    useToolRegistryStore.getState().registerRenderer('web_search', A);

    // 不应抛错或破坏状态
    useToolRegistryStore.getState().unregisterRenderer('not_exist');

    expect(useToolRegistryStore.getState().getRenderer('web_search')).toBe(A);
  });

  it('clearRenderers 清空所有渲染器', () => {
    const A: ToolRendererComponent = () => React.createElement('div', null, 'A');
    const B: ToolRendererComponent = () => React.createElement('div', null, 'B');

    useToolRegistryStore.getState().registerRenderers({
      web_search: A,
      db_query: B,
    });

    useToolRegistryStore.getState().clearRenderers();

    expect(useToolRegistryStore.getState().renderers).toEqual({});
    expect(useToolRegistryStore.getState().getRenderer('web_search')).toBeUndefined();
    expect(useToolRegistryStore.getState().getRenderer('db_query')).toBeUndefined();
  });
});

/**
 * ModelsTab 单元测试 — 覆盖 sortModelsByPriority 纯函数
 */
import { describe, expect, it } from 'vitest';
import { sortModelsByPriority } from '../ModelsTab';

describe('sortModelsByPriority', () => {
  it('按 priority 升序排', () => {
    const models = [
      { id: 'a', priority: 50 },
      { id: 'b', priority: 10 },
      { id: 'c', priority: 100 },
    ];
    const sorted = sortModelsByPriority(models as any);
    expect(sorted.map((m) => m.id)).toEqual(['b', 'a', 'c']);
  });

  it('priority 相同时按 id 稳定排序', () => {
    const models = [
      { id: 'c', priority: 100 },
      { id: 'a', priority: 100 },
      { id: 'b', priority: 100 },
    ];
    const sorted = sortModelsByPriority(models as any);
    expect(sorted.map((m) => m.id)).toEqual(['a', 'b', 'c']);
  });

  it('priority 为 undefined 时兜底为 100', () => {
    const models = [
      { id: 'a', priority: undefined },
      { id: 'b', priority: 50 },
      { id: 'c' },
    ];
    const sorted = sortModelsByPriority(models as any);
    // b(50) 最优先，a 和 c 兜底都是 100，按 id 排序 -> a, c
    expect(sorted.map((m) => m.id)).toEqual(['b', 'a', 'c']);
  });

  it('不修改原数组（纯函数）', () => {
    const models = [
      { id: 'a', priority: 50 },
      { id: 'b', priority: 10 },
    ];
    const original = [...models];
    sortModelsByPriority(models as any);
    expect(models).toEqual(original);
  });
});

/**
 * useConnectionListWidth 钩子测试
 *
 * 验证「让连接名称完整显示所需的侧栏宽度」计算：
 * - 名称被截断时，缺口 = 自然宽度 - 实际占用宽度
 * - 所需宽度 = 当前侧栏宽度 + 最大缺口
 * - 名称完整显示后不再更新（只增不减，避免与用户拖拽互相打架）
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useConnectionListWidth,
  MIN_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH,
} from './useConnectionListWidth';

/** 构造一个名称元素：自然宽度 natural，实际占用宽度 visible。 */
function makeNameEl(natural: number, visible: number) {
  const el = document.createElement('span');
  el.className = 'truncate';
  el.style.width = `${visible}px`;
  el.style.flexShrink = '1';
  Object.defineProperty(el, 'scrollWidth', { value: natural, configurable: true });
  Object.defineProperty(el, 'clientWidth', { value: visible, configurable: true });
  el.getBoundingClientRect = () => {
    const width = el.style.width === 'max-content' ? natural : visible;
    return {
      width,
      height: 16,
      top: 0,
      left: 0,
      right: width,
      bottom: 16,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect;
  };
  return el;
}

/** 构造模拟的列表容器（含 space-y-1 与左右内边距）。 */
function buildList(clientWidth: number) {
  const list = document.createElement('div');
  list.className = 'flex-1 overflow-y-auto p-2 space-y-1';
  list.style.paddingLeft = '8px';
  list.style.paddingRight = '8px';
  Object.defineProperty(list, 'clientWidth', { value: clientWidth, configurable: true });
  return list;
}

/** jsdom 不实现 ResizeObserver，补一个最小可用实现。 */
class ResizeObserverStub {
  callback: () => void;
  constructor(cb: () => void) {
    this.callback = cb;
  }
  observe() {}
  unobserve() {}
  disconnect() {}
  trigger() {
    this.callback();
  }
}

/** 等待钩子内部 requestAnimationFrame 里的测量执行完毕。 */
async function flushMeasurement() {
  await act(async () => {
    await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));
    await Promise.resolve();
  });
}

describe('useConnectionListWidth', () => {
  let originalResizeObserver: typeof globalThis.ResizeObserver;

  beforeEach(() => {
    originalResizeObserver = globalThis.ResizeObserver;
    globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof globalThis.ResizeObserver;
  });

  afterEach(() => {
    globalThis.ResizeObserver = originalResizeObserver;
  });

  it('名称被截断时，所需宽度 = 当前宽度 + 缺口', async () => {
    const list = buildList(280);
    const el = makeNameEl(300, 200); // 缺口 100
    const ref = { current: list };
    const { result } = renderHook(() => useConnectionListWidth(ref));

    act(() => {
      result.current.registerName(0)(el);
    });
    await flushMeasurement();

    // 280 + 100 + NAME_GAP(4)
    expect(result.current.requiredWidth).toBe(384);
  });

  it('名称已完整显示时不更新所需宽度', async () => {
    const list = buildList(280);
    const el = makeNameEl(200, 200); // 无缺口
    const ref = { current: list };
    const { result } = renderHook(() => useConnectionListWidth(ref));

    act(() => {
      result.current.registerName(0)(el);
    });
    await flushMeasurement();

    expect(result.current.requiredWidth).toBe(0);
  });

  it('所需宽度只增不减（名称补齐后不回落）', async () => {
    const list = buildList(280);
    const el = makeNameEl(300, 200);
    const ref = { current: list };
    const { result } = renderHook(() => useConnectionListWidth(ref));

    act(() => {
      result.current.registerName(0)(el);
    });
    await flushMeasurement();
    const first = result.current.requiredWidth;
    expect(first).toBeGreaterThan(280);

    // 侧栏变宽后名称完整显示（缺口 0），所需宽度不应回落
    el.style.width = '300px';
    act(() => {
      result.current.registerName(0)(el);
    });
    await flushMeasurement();
    expect(result.current.requiredWidth).toBe(first);
  });

  it('所需宽度被夹在最小 / 最大区间内', async () => {
    // 超长名称 → 撞上限
    const listLong = buildList(280);
    const elLong = makeNameEl(5000, 200);
    const refLong = { current: listLong };
    const { result: rl } = renderHook(() => useConnectionListWidth(refLong));
    act(() => {
      rl.current.registerName(0)(elLong);
    });
    await flushMeasurement();
    expect(rl.current.requiredWidth).toBe(MAX_SIDEBAR_WIDTH);

    // 极窄列表 + 极小缺口 → 撞下限
    const listShort = buildList(20);
    const elShort = makeNameEl(30, 20);
    const refShort = { current: listShort };
    const { result: rs } = renderHook(() => useConnectionListWidth(refShort));
    act(() => {
      rs.current.registerName(0)(elShort);
    });
    await flushMeasurement();
    expect(rs.current.requiredWidth).toBe(MIN_SIDEBAR_WIDTH);
  });
});

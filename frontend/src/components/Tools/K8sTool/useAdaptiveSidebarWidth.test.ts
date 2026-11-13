/**
 * useNameFitWidth 钩子测试
 *
 * 验证"连接名称完整显示所需的侧栏宽度"计算：
 * - 固定装饰宽度（拖动把手 + 操作按钮 + 名称行内徽章）被正确计入
 * - 最长名称的完整宽度（scrollWidth）被正确计入
 * - 结果与当前侧栏宽度**无关**（否则加宽后截断消失会震荡回缩）
 * - 宽度被夹在 [MIN, MAX] 区间内
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useNameFitWidth,
  MIN_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH,
} from './useAdaptiveSidebarWidth';

/** 构造一个模拟的名称元素，参数为「完整文本宽度」与「可见宽度」。 */
function makeNameEl(fullWidth: number, visibleWidth: number) {
  const el = document.createElement('span');
  el.className = 'truncate';
  Object.defineProperty(el, 'scrollWidth', { value: fullWidth, configurable: true });
  Object.defineProperty(el, 'clientWidth', { value: visibleWidth, configurable: true });
  return el;
}

/** 构造模拟的侧栏 + 名称行结构。 */
function buildDom(options: {
  sidebarWidth: number;
  listPadding: number;
  rowWidth: number;
  buttonWidth: number;
  insideChrome: number;
  names: { full: number; visible: number }[];
}) {
  const sidebar = document.createElement('div');
  sidebar.style.paddingLeft = '0px';
  sidebar.style.paddingRight = '0px';
  Object.defineProperty(sidebar, 'getBoundingClientRect', {
    value: () => ({ width: options.sidebarWidth }),
    configurable: true,
  });

  const list = document.createElement('div');
  list.className = 'space-y-1';
  list.style.paddingLeft = `${options.listPadding}px`;
  list.style.paddingRight = `${options.listPadding}px`;
  sidebar.appendChild(list);

  const nameEls = options.names.map((n) => {
    const nameRow = document.createElement('div');
    // 名称行内的兄弟元素（健康点 / 来源图标 / 徽章）—— 固定装饰
    for (let i = 0; i < 2; i++) {
      const sib = document.createElement('span');
      Object.defineProperty(sib, 'getBoundingClientRect', {
        value: () => ({ width: options.insideChrome / 2 }),
        configurable: true,
      });
      sib.style.marginLeft = '0px';
      sib.style.marginRight = '0px';
      nameRow.appendChild(sib);
    }

    const nameEl = makeNameEl(n.full, n.visible);
    nameRow.appendChild(nameEl);

    const button = document.createElement('button');
    Object.defineProperty(button, 'getBoundingClientRect', {
      value: () => ({ width: options.buttonWidth }),
      configurable: true,
    });
    button.appendChild(nameRow);

    const row = document.createElement('div');
    row.className = 'group';
    Object.defineProperty(row, 'getBoundingClientRect', {
      value: () => ({ width: options.rowWidth }),
      configurable: true,
    });
    row.appendChild(button);
    list.appendChild(row);

    return nameEl;
  });

  return { sidebar, list, nameEls };
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
  /** 手动触发一次回调 */
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

describe('useNameFitWidth', () => {
  let originalResizeObserver: typeof globalThis.ResizeObserver;

  beforeEach(() => {
    originalResizeObserver = globalThis.ResizeObserver;
    globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
  });

  afterEach(() => {
    globalThis.ResizeObserver = originalResizeObserver;
  });

  it('算出让最长名称完整显示所需的宽度', async () => {
    const { sidebar, nameEls } = buildDom({
      sidebarWidth: 256,
      listPadding: 8,
      rowWidth: 483,
      buttonWidth: 349,
      insideChrome: 56,
      names: [
        { full: 68, visible: 49 },
        { full: 79, visible: 49 }, // 最长
        { full: 43, visible: 43 },
      ],
    });

    const ref = { current: sidebar };
    const { result } = renderHook(() => useNameFitWidth(ref));

    // 注册名称元素
    act(() => {
      nameEls.forEach((el, i) => {
        result.current.registerName(i)(el);
      });
    });

    await flushMeasurement();

    // 期望：内边距(16) + 行外装饰(483-349=134) + 按钮内装饰(56) + 最长名称(79) + 呼吸(4)
    expect(result.current.requiredWidth).toBe(16 + 134 + 56 + 79 + 4);
  });

  it('所需宽度与当前侧栏宽度无关（避免加宽后回缩震荡）', async () => {
    // 关键不变式：侧栏加宽时，**行宽与按钮宽同步变大**（按钮是 flex-1，
    // 吸收全部富余空间），所以固定装饰宽度（行宽 - 按钮宽）保持不变，
    // 算出的所需宽度也就与当前宽度无关。
    const narrow = buildDom({
      sidebarWidth: 200,
      listPadding: 8,
      rowWidth: 200,
      buttonWidth: 120, // 装饰 = 200 - 120 = 80
      insideChrome: 56,
      names: [{ full: 100, visible: 40 }],
    });
    const wide = buildDom({
      sidebarWidth: 500,
      listPadding: 8,
      rowWidth: 500,
      buttonWidth: 420, // 装饰 = 500 - 420 = 80（与上面一致）
      insideChrome: 56,
      names: [{ full: 100, visible: 80 }],
    });

    const refNarrow = { current: narrow.sidebar };
    const { result: r1 } = renderHook(() => useNameFitWidth(refNarrow));
    act(() => { r1.current.registerName(0)(narrow.nameEls[0]); });
    await flushMeasurement();

    const refWide = { current: wide.sidebar };
    const { result: r2 } = renderHook(() => useNameFitWidth(refWide));
    act(() => { r2.current.registerName(0)(wide.nameEls[0]); });
    await flushMeasurement();

    // 两种当前宽度下算出的所需宽度必须一致（否则会震荡）
    expect(r1.current.requiredWidth).toBe(r2.current.requiredWidth);
  });

  it('宽度被夹在最小 / 最大区间内', async () => {
    // 超长名称 → 撞上限
    const long = buildDom({
      sidebarWidth: 256,
      listPadding: 8,
      rowWidth: 483,
      buttonWidth: 349,
      insideChrome: 56,
      names: [{ full: 5000, visible: 49 }],
    });
    const refLong = { current: long.sidebar };
    const { result: rl } = renderHook(() => useNameFitWidth(refLong));
    act(() => { rl.current.registerName(0)(long.nameEls[0]); });
    await flushMeasurement();
    expect(rl.current.requiredWidth).toBe(MAX_SIDEBAR_WIDTH);

    // 极短名称 + 极窄装饰 → 撞下限
    const short = buildDom({
      sidebarWidth: 256,
      listPadding: 8,
      rowWidth: 60,
      buttonWidth: 40,
      insideChrome: 4,
      names: [{ full: 10, visible: 10 }],
    });
    const refShort = { current: short.sidebar };
    const { result: rs } = renderHook(() => useNameFitWidth(refShort));
    act(() => { rs.current.registerName(0)(short.nameEls[0]); });
    await flushMeasurement();
    expect(rs.current.requiredWidth).toBe(MIN_SIDEBAR_WIDTH);
  });

  it('没有名称元素时所需宽度为 0', async () => {
    const { sidebar } = buildDom({
      sidebarWidth: 256,
      listPadding: 8,
      rowWidth: 483,
      buttonWidth: 349,
      insideChrome: 56,
      names: [],
    });
    const ref = { current: sidebar };
    const { result } = renderHook(() => useNameFitWidth(ref));
    await flushMeasurement();
    expect(result.current.requiredWidth).toBe(0);
  });
});

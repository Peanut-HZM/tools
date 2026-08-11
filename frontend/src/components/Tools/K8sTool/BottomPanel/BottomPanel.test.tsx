/**
 * BottomPanel 组件单元测试
 *
 * 覆盖：
 * - 空标签时不渲染
 * - 有标签时渲染 TabBar 和 PodDetail
 * - 默认高度正确
 * - 拖动调整高度（mousedown → mousemove → mouseup）
 * - 高度限制（最小 300px / 最大 70vh）
 * - 拖动时的光标 / 样式变化
 */
import React from 'react';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { BottomPanel } from './BottomPanel';

// Mock PodDetail（避免引入复杂的 react-query / i18n 依赖）
vi.mock('../ResourceDetail/PodDetail', () => ({
  PodDetail: () => <div data-testid="pod-detail">PodDetail Mock</div>,
}));

// 可控的 store mock 状态
const mockStoreState = {
  openedTabs: [] as Array<{ id: string; type: string; namespace: string; name: string }>,
  activeTabId: null as string | null,
  setActiveTab: vi.fn(),
  closeResourceTab: vi.fn(),
};

vi.mock('../../../../stores/k8sStore', () => ({
  useK8sStore: () => mockStoreState,
}));

/** 模拟窗口高度 */
const WINDOW_HEIGHT = 1000;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  // 每个用例前重置为默认空状态
  mockStoreState.openedTabs = [];
  mockStoreState.activeTabId = null;

  // 模拟 window.innerHeight
  Object.defineProperty(window, 'innerHeight', {
    value: WINDOW_HEIGHT,
    writable: true,
    configurable: true,
  });
});

/** 准备一个已打开标签页的渲染 */
function renderWithTabs() {
  mockStoreState.openedTabs = [
    { id: 'pod-default-nginx', type: 'pod', namespace: 'default', name: 'nginx' },
  ];
  mockStoreState.activeTabId = 'pod-default-nginx';
  return render(<BottomPanel />);
}

/** 获取面板容器（absolute positioned 的根 div） */
function getPanelContainer(container: HTMLElement): HTMLElement | null {
  return container.firstElementChild as HTMLElement | null;
}

/** 获取可拖动分隔条 */
function getSeparator(container: HTMLElement): HTMLElement | null {
  const bars = container.querySelectorAll('.h-1');
  return (bars[0] as HTMLElement) ?? null;
}

/**
 * 通过 testing-library fireEvent 触发 document 级别的 mousemove
 *
 * React 18 使用根级事件委托，fireEvent 会通过 act 包裹
 * 确保 React 的合成事件机制能正确捕获该事件
 */
function fireDocumentMouseMove(clientY: number) {
  fireEvent.mouseMove(document, { clientY });
}

/** 通过 testing-library fireEvent 触发 document 级别的 mouseup */
function fireDocumentMouseUp() {
  fireEvent.mouseUp(document);
}

describe('BottomPanel', () => {
  // ── 基础渲染 ──

  it('当 openedTabs 为空时，不渲染任何内容', () => {
    const { container } = render(<BottomPanel />);
    expect(container.innerHTML).toBe('');
  });

  it('当有标签页打开时，渲染 TabBar 和 PodDetail', () => {
    renderWithTabs();
    expect(screen.getByText('nginx')).toBeTruthy();
    expect(screen.getByTestId('pod-detail')).toBeTruthy();
  });

  it('当 activeTabId 为 null 时，不渲染 PodDetail', () => {
    mockStoreState.openedTabs = [
      { id: 'pod-default-nginx', type: 'pod', namespace: 'default', name: 'nginx' },
    ];
    mockStoreState.activeTabId = null;
    render(<BottomPanel />);
    expect(screen.getByText('nginx')).toBeTruthy();
    expect(screen.queryByTestId('pod-detail')).toBeNull();
  });

  // ── 默认高度 ──

  it('面板以默认高度 50vh 渲染', () => {
    const { container } = renderWithTabs();
    const panel = getPanelContainer(container);
    expect(panel).not.toBeNull();
    expect(panel!.style.height).toBe('50vh');
  });

  // ── 分隔条样式 ──

  it('分隔条存在且带有 cursor-grab 样式', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container);
    expect(separator).not.toBeNull();
    expect(separator!.className).toContain('cursor-grab');
  });

  // ── 拖动调整高度 ──

  it('拖动分隔条向上移动时，面板高度增加', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    // 使用 act 包裹 mouseDown，确保 useEffect 同步运行并注册 document 监听器
    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // useEffect 已执行，document mousemove 监听器已注册
    // 向上拖动：y=500 → y=400，deltaY=100，新高度=500+100=600px
    fireDocumentMouseMove(400);

    const panel = getPanelContainer(container)!;
    expect(panel.style.height).toBe('600px');
  });

  it('拖动分隔条向下移动时，面板高度减小', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // 向下拖动：y=500 → y=600，deltaY=-100，新高度=500-100=400px
    fireDocumentMouseMove(600);

    const panel = getPanelContainer(container)!;
    expect(panel.style.height).toBe('400px');
  });

  it('mouseup 后停止拖动，后续 mousemove 不再改变高度', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // 拖动到 600px
    fireDocumentMouseMove(400);
    expect(getPanelContainer(container)!.style.height).toBe('600px');

    // 松开鼠标
    act(() => {
      fireDocumentMouseUp();
    });

    // 后续移动不应改变高度
    fireDocumentMouseMove(200);
    expect(getPanelContainer(container)!.style.height).toBe('600px');
  });

  // ── 高度限制 ──

  it('高度不会小于 MIN_HEIGHT (300px)', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // 大幅向下拖动：y=500 → y=1200，deltaY=-700，目标=-200px
    fireDocumentMouseMove(1200);

    const panel = getPanelContainer(container)!;
    // 应被限制为 300px
    expect(panel.style.height).toBe('300px');
  });

  it('高度不会超过 MAX_HEIGHT_PERCENT (70vh = 700px)', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // 大幅向上拖动：y=500 → y=-500，deltaY=1000，目标=1500px
    fireDocumentMouseMove(-500);

    const panel = getPanelContainer(container)!;
    // 70% of 1000 = 700px
    expect(panel.style.height).toBe('700px');
  });

  // ── 拖动时样式变化 ──

  it('拖动中分隔条添加 cursor-grabbing 和蓝色高亮', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // 拖动中应包含 cursor-grabbing 和蓝色高亮
    const draggingSeparator = getSeparator(container)!;
    expect(draggingSeparator.className).toContain('cursor-grabbing');
    expect(draggingSeparator.className).toContain('bg-blue-500');

    // 结束拖动
    act(() => {
      fireDocumentMouseUp();
    });

    // 恢复后应回到 cursor-grab
    const restoredSeparator = getSeparator(container)!;
    expect(restoredSeparator.className).toContain('cursor-grab');
  });

  it('拖动期间禁止文本选中，松开后恢复', () => {
    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    // 记录初始 userSelect（jsdom 中默认为 ''）
    const originalUserSelect = document.body.style.userSelect;

    act(() => {
      fireEvent.mouseDown(separator, { clientY: 500 });
    });

    // 拖动中 body.userSelect 应为 'none'
    expect(document.body.style.userSelect).toBe('none');

    // 结束拖动
    act(() => {
      fireDocumentMouseUp();
    });

    // 应恢复原始值
    expect(document.body.style.userSelect).toBe(originalUserSelect);
  });

  // ── vh 初始高度的解析 ──

  it('能正确解析 vh 单位的初始高度', () => {
    // 设置窗口高度为 800，50vh 应解析为 400px
    Object.defineProperty(window, 'innerHeight', {
      value: 800,
      writable: true,
      configurable: true,
    });

    const { container } = renderWithTabs();
    const separator = getSeparator(container)!;

    // 在 y=400 处按下（默认高度 50vh = 400px）
    act(() => {
      fireEvent.mouseDown(separator, { clientY: 400 });
    });

    // 向上拖动：y=400 → y=300，deltaY=100，新高度=400+100=500px
    fireDocumentMouseMove(300);

    const panel = getPanelContainer(container)!;
    expect(panel.style.height).toBe('500px');
  });
});

/**
 * BottomPanel 组件单元测试
 *
 * 覆盖：
 * - 空标签时不渲染
 * - 有标签时渲染 TabBar 和 PodDetail
 */
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
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

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  // 每个用例前重置为默认空状态
  mockStoreState.openedTabs = [];
  mockStoreState.activeTabId = null;
});

describe('BottomPanel', () => {
  it('当 openedTabs 为空时，不渲染任何内容', () => {
    const { container } = render(<BottomPanel />);
    // 没有可见元素
    expect(container.innerHTML).toBe('');
  });

  it('当有标签页打开时，渲染 TabBar 和 PodDetail', () => {
    mockStoreState.openedTabs = [
      { id: 'pod-default-nginx', type: 'pod', namespace: 'default', name: 'nginx' },
    ];
    mockStoreState.activeTabId = 'pod-default-nginx';

    render(<BottomPanel />);

    // TabBar 应渲染出标签名
    expect(screen.getByText('nginx')).toBeTruthy();
    // PodDetail 应渲染
    expect(screen.getByTestId('pod-detail')).toBeTruthy();
  });

  it('当 activeTabId 为 null 时，不渲染 PodDetail', () => {
    mockStoreState.openedTabs = [
      { id: 'pod-default-nginx', type: 'pod', namespace: 'default', name: 'nginx' },
    ];
    mockStoreState.activeTabId = null;

    render(<BottomPanel />);

    // TabBar 仍渲染
    expect(screen.getByText('nginx')).toBeTruthy();
    // PodDetail 不渲染
    expect(screen.queryByTestId('pod-detail')).toBeNull();
  });
});

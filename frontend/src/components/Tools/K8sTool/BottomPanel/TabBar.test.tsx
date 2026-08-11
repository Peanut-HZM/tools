/**
 * TabBar 组件单元测试
 *
 * 覆盖：
 * - 每个打开的标签页渲染一个 tab
 * - 点击标签触发 setActiveTab
 * - 点击关闭按钮触发 closeResourceTab
 * - 无标签时显示占位提示文案
 * - 每个标签渲染状态指示图标
 * - 激活标签和非激活标签样式差异
 * - 关闭按钮激活态与非激活态颜色差异
 */
import React from 'react';
import { render, fireEvent, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { TabBar } from './TabBar';

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
  mockStoreState.openedTabs = [];
  mockStoreState.activeTabId = null;
  mockStoreState.setActiveTab.mockClear();
  mockStoreState.closeResourceTab.mockClear();
});

describe('TabBar', () => {
  it('每个打开的标签渲染一个 tab', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
      { id: 'tab-2', type: 'pod', namespace: 'kube-system', name: 'coredns' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    render(<TabBar />);

    expect(screen.getByText('nginx')).toBeTruthy();
    expect(screen.getByText('coredns')).toBeTruthy();
    expect(screen.getByText('default')).toBeTruthy();
    expect(screen.getByText('kube-system')).toBeTruthy();
  });

  it('点击标签触发 setActiveTab', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
      { id: 'tab-2', type: 'pod', namespace: 'default', name: 'redis' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    render(<TabBar />);

    // 点击第二个标签
    fireEvent.click(screen.getByText('redis'));
    expect(mockStoreState.setActiveTab).toHaveBeenCalledWith('tab-2');
  });

  it('点击关闭按钮触发 closeResourceTab，且阻止事件冒泡', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    render(<TabBar />);

    // 点击关闭按钮（title 为"关闭标签"）
    const closeButton = screen.getByTitle('关闭标签');
    fireEvent.click(closeButton);

    expect(mockStoreState.closeResourceTab).toHaveBeenCalledWith('tab-1');
    // setActiveTab 不应被触发（事件冒泡被阻止）
    expect(mockStoreState.setActiveTab).not.toHaveBeenCalled();
  });

  it('无标签时显示"点击 Pod 行打开详情"提示', () => {
    mockStoreState.openedTabs = [];

    render(<TabBar />);

    expect(screen.getByText('点击 Pod 行打开详情')).toBeTruthy();
  });

  it('激活标签显示激活态样式，非激活标签显示非激活态样式', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
      { id: 'tab-2', type: 'pod', namespace: 'default', name: 'redis' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    render(<TabBar />);

    // 激活标签的父元素应包含蓝色样式类
    const activeTab = screen.getByText('nginx').closest('div');
    expect(activeTab?.className).toContain('bg-blue-600/20');
    expect(activeTab?.className).toContain('text-blue-300');
    expect(activeTab?.className).toContain('border-blue-500/40');

    // 非激活标签应包含 slate 样式类
    const inactiveTab = screen.getByText('redis').closest('div');
    expect(inactiveTab?.className).toContain('bg-slate-700/50');
    expect(inactiveTab?.className).toContain('text-slate-400');
  });

  it('每个标签渲染状态指示图标（fas fa-cube）', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
      { id: 'tab-2', type: 'deployment', namespace: 'default', name: 'api-server' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    const { container } = render(<TabBar />);

    // 应渲染 2 个状态图标
    const icons = container.querySelectorAll('i.fas.fa-cube');
    expect(icons.length).toBe(2);
  });

  it('激活标签的关闭按钮为蓝色，非激活标签的关闭按钮为灰色', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
      { id: 'tab-2', type: 'pod', namespace: 'default', name: 'redis' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    render(<TabBar />);

    // 所有关闭按钮
    const closeButtons = screen.getAllByTitle('关闭标签');
    expect(closeButtons.length).toBe(2);

    // 激活标签的关闭按钮应为蓝色
    expect(closeButtons[0].className).toContain('text-blue-400');
    // 非激活标签的关闭按钮应为灰色
    expect(closeButtons[1].className).toContain('text-slate-500');
  });

  it('标签具有 min-w 和 max-w 约束', () => {
    mockStoreState.openedTabs = [
      { id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' },
    ];
    mockStoreState.activeTabId = 'tab-1';

    render(<TabBar />);

    const tab = screen.getByText('nginx').closest('div');
    expect(tab?.className).toContain('min-w-[120px]');
    expect(tab?.className).toContain('max-w-[200px]');
  });
});

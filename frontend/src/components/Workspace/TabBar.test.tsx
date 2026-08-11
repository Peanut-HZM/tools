import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { TabBar } from './TabBar';
import { useWorkspaceStore } from '../../stores/workspaceStore';

describe('TabBar', () => {
  afterEach(() => {
    // 清理 DOM，防止测试间残留元素
    cleanup();
  });

  beforeEach(() => {
    // 清除 persist 中间件的 localStorage 数据，防止测试间状态累积
    localStorage.clear();
    // 重置 store 到初始状态
    act(() => {
      useWorkspaceStore.setState({ tabs: [], activeTabId: null });
    });
  });

  it('should render nothing when no tabs', () => {
    const { container } = render(<TabBar />);
    expect(container.firstChild).toBeNull();
  });

  it('should render tabs', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    useWorkspaceStore.getState().addTab({ id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' });

    render(<TabBar />);
    expect(screen.getByText('K8s')).toBeTruthy();
    expect(screen.getByText('SSH')).toBeTruthy();
  });

  it('should highlight active tab', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    useWorkspaceStore.getState().addTab({ id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' });
    // addTab 会将最后添加的标签设为活跃，这里显式切换回 K8s
    useWorkspaceStore.getState().setActiveTab(useWorkspaceStore.getState().tabs[0].id);

    render(<TabBar />);
    const k8sTab = screen.getByText('K8s').closest('[data-tab-id]');
    expect(k8sTab?.getAttribute('data-active')).toBe('true');
  });

  it('should switch tab on click', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    useWorkspaceStore.getState().addTab({ id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' });

    render(<TabBar />);
    const k8sTab = screen.getByText('K8s').closest('[data-tab-id]');
    fireEvent.click(k8sTab!);

    expect(useWorkspaceStore.getState().activeTabId).toBe(
      useWorkspaceStore.getState().tabs[0].id
    );
  });

  it('should remove tab on close click', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });

    render(<TabBar />);
    const closeBtn = screen.getByText('×');
    fireEvent.click(closeBtn);

    expect(useWorkspaceStore.getState().tabs).toHaveLength(0);
  });
});

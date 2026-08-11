import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { useWorkspaceStore } from '../../stores/workspaceStore';

// Mock useNavigate
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

describe('WorkspaceSidebar', () => {
  const mockTools = [
    { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server', description: '', rating: 0, usageCount: '0', category: 'dev', iconColor: '' },
    { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key', description: '', rating: 0, usageCount: '0', category: 'dev', iconColor: '' },
  ];

  afterEach(() => {
    // 清理 DOM，防止测试间残留元素
    cleanup();
  });

  beforeEach(() => {
    // 清除 localStorage（包括 persist 中间件和 sidebar collapsed 状态）
    localStorage.clear();
    // 重置 store 到初始状态
    act(() => {
      useWorkspaceStore.setState({ tabs: [], activeTabId: null });
    });
  });

  it('should render home button', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    expect(screen.getByText('返回首页')).toBeTruthy();
  });

  it('should render tool list', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    expect(screen.getByText('K8s')).toBeTruthy();
    expect(screen.getByText('SSH')).toBeTruthy();
  });

  it('should highlight opened tools', () => {
    act(() => {
      useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    });
    render(<WorkspaceSidebar tools={mockTools} />);

    const k8sItem = screen.getByText('K8s').closest('[data-tool-id]');
    expect(k8sItem?.getAttribute('data-active')).toBe('true');
  });

  it('should add tab when clicking tool', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    fireEvent.click(screen.getByText('K8s'));

    expect(useWorkspaceStore.getState().tabs).toHaveLength(1);
    expect(useWorkspaceStore.getState().tabs[0].toolId).toBe('k8s-tool');
  });

  it('should be collapsible', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    const toggle = screen.getByTitle('折叠侧边栏');
    fireEvent.click(toggle);
    // After collapse, tool names should be hidden
    expect(screen.queryByText('K8s')).toBeNull();
  });
});

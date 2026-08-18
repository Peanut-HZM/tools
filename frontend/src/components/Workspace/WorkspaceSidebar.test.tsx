import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { useWorkspaceStore } from '../../stores/workspaceStore';

// Mock useNavigate
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock('../../i18n', () => ({
  useI18n: () => ({
    t: {
      workspace: {
        home: '返回首页',
        toolList: '工具列表',
        collapseSidebar: '折叠侧边栏',
        expandSidebar: '展开侧边栏',
        searchPlaceholder: '搜索工具...',
      },
    },
    language: 'zh-CN',
    setLanguage: vi.fn(),
    toggleLanguage: vi.fn(),
  }),
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
    localStorage.clear();
    act(() => {
      useWorkspaceStore.setState({ tabs: [], activeTabId: null, isToolSidebarVisible: true });
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

  it('should render search input', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    const searchInput = screen.getByPlaceholderText('搜索工具...');
    expect(searchInput).toBeTruthy();
  });

  it('should filter tools by search query', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    const searchInput = screen.getByPlaceholderText('搜索工具...');
    fireEvent.change(searchInput, { target: { value: 'K8s' } });

    // Only K8s should be visible
    expect(screen.queryByText('SSH')).toBeNull();
  });

  it('should show all tools when search is cleared', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    const searchInput = screen.getByPlaceholderText('搜索工具...');
    fireEvent.change(searchInput, { target: { value: 'K8s' } });
    fireEvent.change(searchInput, { target: { value: '' } });

    expect(screen.getByText('K8s')).toBeTruthy();
    expect(screen.getByText('SSH')).toBeTruthy();
  });
});

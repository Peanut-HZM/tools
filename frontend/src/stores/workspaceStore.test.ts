import { describe, it, expect, beforeEach, vi } from 'vitest';

// mock 必须在导入 store 之前声明（vi.mock 会被提升到文件顶部）
vi.mock('../api/adminApi', () => ({
  recordToolVisit: vi.fn().mockResolvedValue(true),
}));

import { useWorkspaceStore } from './workspaceStore';
import { recordToolVisit } from '../api/adminApi';

describe('workspaceStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useWorkspaceStore.setState({
      tabs: [],
      activeTabId: null,
    });
    // 清空 mock 调用记录，避免测试间互相污染
    vi.mocked(recordToolVisit).mockClear();
  });

  it('should start with empty tabs', () => {
    const state = useWorkspaceStore.getState();
    expect(state.tabs).toEqual([]);
    expect(state.activeTabId).toBeNull();
  });

  it('should add a tab', () => {
    const tool = {
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'fas fa-server',
    };
    useWorkspaceStore.getState().addTab(tool);

    const state = useWorkspaceStore.getState();
    expect(state.tabs).toHaveLength(1);
    expect(state.tabs[0].toolId).toBe('k8s-tool');
    expect(state.tabs[0].toolName).toBe('K8s 控制台');
    expect(state.activeTabId).toBe(state.tabs[0].id);
  });

  it('should reuse existing tab when adding same tool', () => {
    const tool = {
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'fas fa-server',
    };
    useWorkspaceStore.getState().addTab(tool);
    const firstTabId = useWorkspaceStore.getState().tabs[0].id;

    useWorkspaceStore.getState().addTab(tool);

    const state = useWorkspaceStore.getState();
    expect(state.tabs).toHaveLength(1);
    expect(state.activeTabId).toBe(firstTabId);
  });

  it('should remove a tab', () => {
    const tool = {
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'fas fa-server',
    };
    useWorkspaceStore.getState().addTab(tool);
    const tabId = useWorkspaceStore.getState().tabs[0].id;

    useWorkspaceStore.getState().removeTab(tabId);

    const state = useWorkspaceStore.getState();
    expect(state.tabs).toHaveLength(0);
    expect(state.activeTabId).toBeNull();
  });

  it('should switch to adjacent tab when removing active tab', () => {
    const tool1 = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    const tool2 = { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' };
    const tool3 = { id: 'db-tool', title: 'DB', icon: 'fas fa-database' };

    useWorkspaceStore.getState().addTab(tool1);
    useWorkspaceStore.getState().addTab(tool2);
    useWorkspaceStore.getState().addTab(tool3);

    const tabs = useWorkspaceStore.getState().tabs;
    // Active is tool3 (last added)
    expect(useWorkspaceStore.getState().activeTabId).toBe(tabs[2].id);

    // Remove active tab (tool3)
    useWorkspaceStore.getState().removeTab(tabs[2].id);

    // Should switch to tool2 (previous)
    expect(useWorkspaceStore.getState().activeTabId).toBe(tabs[1].id);
  });

  it('should set active tab', () => {
    const tool1 = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    const tool2 = { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' };

    useWorkspaceStore.getState().addTab(tool1);
    useWorkspaceStore.getState().addTab(tool2);

    const tabs = useWorkspaceStore.getState().tabs;
    useWorkspaceStore.getState().setActiveTab(tabs[0].id);

    expect(useWorkspaceStore.getState().activeTabId).toBe(tabs[0].id);
  });

  it('should record usage when adding a new tab', () => {
    const tool = { id: 'k8s-tool', title: 'K8s 控制台', icon: 'fas fa-server' };
    useWorkspaceStore.getState().addTab(tool);

    expect(recordToolVisit).toHaveBeenCalledTimes(1);
    expect(recordToolVisit).toHaveBeenCalledWith('k8s-tool', 'K8s 控制台');
  });

  it('should record usage when activating an existing tab via addTab', () => {
    const tool = { id: 'k8s-tool', title: 'K8s 控制台', icon: 'fas fa-server' };
    useWorkspaceStore.getState().addTab(tool);
    vi.mocked(recordToolVisit).mockClear();

    // 第二次 addTab 同一工具：走 existing 分支（激活已打开 tab），也应计一次
    useWorkspaceStore.getState().addTab(tool);

    expect(useWorkspaceStore.getState().tabs).toHaveLength(1);
    expect(recordToolVisit).toHaveBeenCalledTimes(1);
    expect(recordToolVisit).toHaveBeenCalledWith('k8s-tool', 'K8s 控制台');
  });

  it('should record usage when switching tabs via setActiveTab', () => {
    const tool1 = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    const tool2 = { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' };
    useWorkspaceStore.getState().addTab(tool1);
    useWorkspaceStore.getState().addTab(tool2);
    vi.mocked(recordToolVisit).mockClear();

    const tabs = useWorkspaceStore.getState().tabs;
    useWorkspaceStore.getState().setActiveTab(tabs[0].id);

    expect(recordToolVisit).toHaveBeenCalledTimes(1);
    expect(recordToolVisit).toHaveBeenCalledWith('k8s-tool', 'K8s');
  });

  it('should not record usage when setActiveTab gets unknown tabId', () => {
    const tool = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    useWorkspaceStore.getState().addTab(tool);
    vi.mocked(recordToolVisit).mockClear();

    useWorkspaceStore.getState().setActiveTab('nonexistent-tab-id');

    expect(recordToolVisit).not.toHaveBeenCalled();
  });

  it('should still add tab when recordToolVisit rejects', async () => {
    vi.mocked(recordToolVisit).mockRejectedValueOnce(new Error('network down'));

    const tool = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    useWorkspaceStore.getState().addTab(tool);

    // 上报失败静默，store 行为不受影响
    expect(useWorkspaceStore.getState().tabs).toHaveLength(1);
    // 等待微任务队列排空，确保没有未处理的 Promise 拒绝
    await Promise.resolve();
  });
});

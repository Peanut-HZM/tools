import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore } from './workspaceStore';

describe('workspaceStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useWorkspaceStore.setState({
      tabs: [],
      activeTabId: null,
    });
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
});

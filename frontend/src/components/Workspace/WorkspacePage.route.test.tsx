/**
 * 工作区地址栏路由测试
 *
 * 需求：
 * 1. 地址栏只保留 `/workspace/<工具编码>`，**不携带**工具内部参数
 *    （集群 cluster / 资源类型 resource / 命名空间 namespaces 等）
 * 2. 刷新页面后，仍能恢复上次打开的工具
 *
 * 本测试覆盖：
 * - 打开工具时 URL 变为 /workspace/<toolId>，且不带任何 query
 * - 访问 /workspace/<toolId> 时能打开对应工具
 * - K8s 工具内部上下文（集群/命名空间/资源类型）由 store 持久化，不进 URL
 */
import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';

const navigateMock = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('./toolComponents', () => ({
  toolComponentMap: {
    'k8s-tool': () => <div>K8s 工具内容</div>,
    'ssh-tool': () => <div>SSH 工具内容</div>,
  },
}));

vi.mock('./WorkspaceSidebar', () => ({ WorkspaceSidebar: () => <div>侧栏</div> }));
vi.mock('./TabBar', () => ({ TabBar: () => <div>页签栏</div> }));
vi.mock('./TabPanels', () => ({ TabPanels: () => <div>内容区</div> }));
vi.mock('./EmptyWorkspace', () => ({ EmptyWorkspace: () => <div>空工作区</div> }));
vi.mock('../../services/api', () => ({
  fetchTools: () => Promise.resolve([
    { id: 'k8s-tool', title: 'K8s 控制台', icon: 'k' },
    { id: 'ssh-tool', title: 'SSH 管理', icon: 's' },
  ]),
}));

import { WorkspacePage } from './WorkspacePage';
import { useWorkspaceStore } from '../../stores/workspaceStore';

/** 记录当前 pathname，便于断言地址栏内容 */
function PathProbe() {
  const location = useLocation();
  return <div data-testid="pathname">{location.pathname}</div>;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/workspace" element={<><WorkspacePage /><PathProbe /></>} />
        <Route path="/workspace/:toolId" element={<><WorkspacePage /><PathProbe /></>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('工作区地址栏路由', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    useWorkspaceStore.setState({
      tabs: [],
      activeTabId: null,
      isToolSidebarVisible: true,
    });
  });

  afterEach(cleanup);

  it('访问 /workspace/<toolId> 能打开对应工具', async () => {
    renderAt('/workspace/k8s-tool');
    await waitFor(() => {
      expect(useWorkspaceStore.getState().tabs.some((t) => t.toolId === 'k8s-tool')).toBe(true);
    });
  });

  it('打开工具后地址栏只保留 /workspace/<工具编码>，不带任何 query', async () => {
    renderAt('/workspace');
    // 模拟用户从首页跳进来打开 K8s 工具
    useWorkspaceStore.getState().addTab({
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'k',
    });

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalled();
    });

    const call = navigateMock.mock.calls.find(
      (c) => typeof c[0] === 'string' && c[0].startsWith('/workspace'),
    );
    expect(call).toBeDefined();
    const target = call![0] as string;
    // 只应是 /workspace/<toolId>
    expect(target).toBe('/workspace/k8s-tool');
    // 关键断言：不含任何 query 参数
    expect(target).not.toContain('?');
    expect(target).not.toContain('cluster');
    expect(target).not.toContain('resource');
    expect(target).not.toContain('namespaces');
  });

  it('K8s 内部上下文（集群/命名空间/资源类型）不进 URL', async () => {
    // 这些参数曾经被写进地址栏，现在由 k8sStore 持久化
    const k8sStore = await import('../../stores/k8sStore');
    k8sStore.useK8sStore.setState({
      activeConnectionId: 'cluster-abc',
      selectedNamespaces: ['hrcost-pd'],
      resourceType: 'pods',
    });

    renderAt('/workspace/k8s-tool');
    await waitFor(() => {
      expect(useWorkspaceStore.getState().tabs.some((t) => t.toolId === 'k8s-tool')).toBe(true);
    });

    // 地址栏里不应出现任何 K8s 内部参数
    const pathCalls = navigateMock.mock.calls.filter(
      (c) => typeof c[0] === 'string' && c[0].includes('cluster'),
    );
    expect(pathCalls).toHaveLength(0);

    const anyQuery = navigateMock.mock.calls.filter(
      (c) => typeof c[0] === 'string' && c[0].includes('?'),
    );
    expect(anyQuery).toHaveLength(0);
  });

  it('切换页签时地址栏同步为对应工具编码', async () => {
    renderAt('/workspace/k8s-tool');
    await waitFor(() => {
      expect(useWorkspaceStore.getState().tabs.length).toBeGreaterThan(0);
    });

    // 再打开另一个工具
    useWorkspaceStore.getState().addTab({
      id: 'ssh-tool',
      title: 'SSH 管理',
      icon: 's',
    });

    await waitFor(() => {
      const calls = navigateMock.mock.calls.filter(
        (c) => typeof c[0] === 'string' && c[0] === '/workspace/ssh-tool',
      );
      expect(calls.length).toBeGreaterThan(0);
    });
  });
});

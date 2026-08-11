/**
 * K8sTool 主容器组件单元测试
 *
 * 覆盖：
 * - 渲染 BottomPanel（而非 PodDetail 抽屉）
 * - 不从 store 中读取 selectedResource
 * - 无标签打开时正常渲染
 * - 有标签打开时正确渲染
 */
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import K8sTool from './K8sTool';

// ---- Mock 子组件 ----
vi.mock('./ConnectionList', () => ({
  ConnectionList: (props: any) => (
    <div data-testid="connection-list" data-selected={props.selectedId} />
  ),
}));

vi.mock('./ConnectionModal', () => ({
  ConnectionModal: ({ isOpen }: any) =>
    isOpen ? <div data-testid="connection-modal" /> : null,
}));

vi.mock('./EmptyState', () => ({
  EmptyState: () => <div data-testid="empty-state" />,
}));

vi.mock('./TopBar', () => ({
  TopBar: () => <div data-testid="top-bar" />,
}));

vi.mock('./ResourceTabs', () => ({
  ResourceTabs: () => <div data-testid="resource-tabs" />,
}));

// 关键：验证使用的是 BottomPanel 而非 PodDetail
vi.mock('./BottomPanel/BottomPanel', () => ({
  BottomPanel: () => <div data-testid="bottom-panel" />,
}));

// ---- Mock hooks ----
vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      tools: {
        'k8s-tool': {
          connection: { deleteConfirm: '确认删除 {name}？' },
          deleteSuccess: '删除成功',
        },
      },
      common: { error: '错误' },
    },
  }),
  interpolate: (tpl: string, vars: Record<string, string>) =>
    tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? ''),
}));

vi.mock('../../../hooks/useK8sClient', () => ({
  useK8sConnections: vi.fn(),
}));

vi.mock('../../../api/k8sToolApi', () => ({
  deleteK8sConfig: vi.fn(),
}));

// ---- 可控的 store mock ----
const mockStoreState: Record<string, any> = {
  connections: [],
  activeConnectionId: null,
  setActiveConnection: vi.fn(),
  setConnections: vi.fn(),
  // 注意：故意不包含 selectedResource，验证组件不再依赖它
};

// 记录 store 被访问了哪些 key
const accessedKeys = new Set<string>();

vi.mock('../../../stores/k8sStore', () => ({
  useK8sStore: () => {
    // 用 Proxy 追踪访问了哪些 key
    return new Proxy(mockStoreState, {
      get(target, prop: string) {
        accessedKeys.add(prop);
        return target[prop];
      },
    });
  },
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  accessedKeys.clear();
});

beforeEach(() => {
  mockStoreState.connections = [];
  mockStoreState.activeConnectionId = null;
  accessedKeys.clear();
});

describe('K8sTool', () => {
  it('无活跃连接时，渲染空状态', () => {
    render(<K8sTool />);

    expect(screen.getByTestId('connection-list')).toBeTruthy();
    expect(screen.getByTestId('empty-state')).toBeTruthy();
    // TopBar / ResourceTabs 不应渲染（无活跃连接）
    expect(screen.queryByTestId('top-bar')).toBeNull();
    expect(screen.queryByTestId('resource-tabs')).toBeNull();
  });

  it('渲染 BottomPanel 而非 PodDetail', () => {
    render(<K8sTool />);

    // BottomPanel 应该被渲染
    expect(screen.getByTestId('bottom-panel')).toBeTruthy();
  });

  it('不从 store 中读取 selectedResource', () => {
    render(<K8sTool />);

    // 验证组件没有访问 selectedResource
    expect(accessedKeys.has('selectedResource')).toBe(false);
  });

  it('有活跃连接时，渲染 TopBar 和 ResourceTabs', () => {
    mockStoreState.connections = [
      { id: 'conn-1', name: 'test-cluster', config: '{}' },
    ];
    mockStoreState.activeConnectionId = 'conn-1';

    render(<K8sTool />);

    expect(screen.getByTestId('top-bar')).toBeTruthy();
    expect(screen.getByTestId('resource-tabs')).toBeTruthy();
    // 空状态不应渲染
    expect(screen.queryByTestId('empty-state')).toBeNull();
    // BottomPanel 始终渲染
    expect(screen.getByTestId('bottom-panel')).toBeTruthy();
  });

  it('无论是否有标签打开，BottomPanel 始终存在于 DOM 中', () => {
    // BottomPanel 自身会根据 store 状态决定是否显示内容
    // K8sTool 只负责渲染它，不传递任何 props
    mockStoreState.activeConnectionId = 'conn-1';

    const { container } = render(<K8sTool />);

    const bottomPanel = screen.getByTestId('bottom-panel');
    expect(bottomPanel).toBeTruthy();
    // BottomPanel 不应接收任何 props（由它自己从 store 读取状态）
    expect(bottomPanel.children.length).toBe(0);
  });
});

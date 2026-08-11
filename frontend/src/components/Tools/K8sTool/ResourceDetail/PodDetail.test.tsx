/**
 * PodDetail 组件单元测试
 *
 * 测试重点：
 * - currentTab 为 null 时不渲染
 * - currentTab 存在时正确渲染 Pod 名称、命名空间
 * - 使用 currentTab 的 name 和 namespace 发起查询
 * - 子 Tab 切换正常
 */
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { PodDetail } from './PodDetail';

// ---------- Mock 子模块 ----------

// 直接使用真实的 k8sStore，避免 mock 引发的 React 重渲染问题
import { useK8sStore } from '../../../../stores/k8sStore';

/** 模拟 useI18n */
vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    t: {
      common: { loading: '加载中...' },
      'tools': {
        'k8s-tool': {
          errors: { NOT_FOUND: '资源未找到' },
          resourceDetail: {
            tabs: {
              overview: '概览',
              containers: '容器',
              logs: '日志',
              terminal: '终端',
              yaml: 'YAML',
              events: '事件',
              metrics: '指标',
              related: '关联',
            },
          },
        },
      },
    },
  }),
}));

/** 模拟 api.getPodDetail */
const mockGetPodDetail = vi.fn();
vi.mock('../../../../api/k8sToolApi', () => ({
  getPodDetail: (...args: unknown[]) => mockGetPodDetail(...args),
}));

/** 模拟 useQuery — 默认返回正在加载 */
let mockQueryResult: Record<string, unknown> = {
  data: undefined,
  isLoading: true,
  isError: false,
};

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
  return {
    ...actual,
    useQuery: () => mockQueryResult,
  };
});

// 模拟子面板组件，避免深层渲染
vi.mock('./OverviewPanel', () => ({
  OverviewPanel: (props: { pod: { name: string } }) => (
    <div data-testid="overview-panel">{props.pod.name}</div>
  ),
}));
vi.mock('./ContainersPanel', () => ({
  ContainersPanel: () => <div data-testid="containers-panel">containers</div>,
}));
vi.mock('./YamlPanel', () => ({
  YamlPanel: () => <div data-testid="yaml-panel">yaml</div>,
}));
vi.mock('./EventsPanel', () => ({
  EventsPanel: () => <div data-testid="events-panel">events</div>,
}));
vi.mock('./MetricsPanel', () => ({
  MetricsPanel: () => <div data-testid="metrics-panel">metrics</div>,
}));
vi.mock('./RelatedPanel', () => ({
  RelatedPanel: () => <div data-testid="related-panel">related</div>,
}));
vi.mock('../LogsViewer/LogsViewer', () => ({
  LogsViewer: () => <div data-testid="logs-viewer">logs</div>,
}));
vi.mock('../TerminalPanel/K8sTerminalPanel', () => ({
  K8sTerminalPanel: () => <div data-testid="terminal-panel">terminal</div>,
}));

/** 构建测试用的 QueryClient */
const createQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

/** 包装组件渲染 */
const renderWithProviders = (ui: React.ReactElement) => {
  const qc = createQueryClient();
  return render(
    <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
  );
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  // 重置真实 store 状态
  const store = useK8sStore.getState();
  store.clearAllTabs();
  useK8sStore.setState({ activeConnectionId: 'conn-1' });
  // 重置 query mock
  mockQueryResult = { data: undefined, isLoading: true, isError: false };
});

// ---------- 测试用例 ----------

describe('PodDetail', () => {
  /**
   * 工具函数：向 store 中注入测试用的打开标签
   */
  const setupOpenTab = (tabs: Array<{ id: string; type: string; namespace: string; name: string }>, activeId: string | null = tabs[0]?.id ?? null) => {
    useK8sStore.setState((state) => ({
      ...state,
      openedTabs: tabs,
      activeTabId: activeId,
    }));
  };

  it('当 currentTab 为 null 时不渲染任何内容', () => {
    setupOpenTab([]);

    const { container } = renderWithProviders(<PodDetail />);
    // 容器应为空
    expect(container.firstChild).toBeNull();
  });

  it('当传入不存在的 tabId 时不渲染任何内容', () => {
    setupOpenTab([{ id: 'tab-1', type: 'pod', namespace: 'default', name: 'nginx' }], 'tab-1');

    const { container } = renderWithProviders(
      <PodDetail tabId="non-existent-id" />
    );
    expect(container.firstChild).toBeNull();
  });

  it('当 currentTab 存在时正确渲染 Pod 名称和命名空间', () => {
    setupOpenTab([{ id: 'tab-1', type: 'pod', namespace: 'production', name: 'my-app-pod' }]);
    mockQueryResult = { data: undefined, isLoading: true, isError: false };

    renderWithProviders(<PodDetail />);

    expect(screen.getByText('my-app-pod')).toBeTruthy();
    expect(screen.getByText('production')).toBeTruthy();
  });

  it('使用 tabId prop 而非 activeTabId 查找标签', () => {
    setupOpenTab([
      { id: 'tab-1', type: 'pod', namespace: 'ns-a', name: 'pod-a' },
      { id: 'tab-2', type: 'pod', namespace: 'ns-b', name: 'pod-b' },
    ], 'tab-1');
    mockQueryResult = { data: undefined, isLoading: true, isError: false };

    // 传入 tab-2，应显示 pod-b/ns-b
    renderWithProviders(<PodDetail tabId="tab-2" />);

    expect(screen.getByText('pod-b')).toBeTruthy();
    expect(screen.getByText('ns-b')).toBeTruthy();
    // 不应显示 tab-1 的内容
    expect(screen.queryByText('pod-a')).toBeNull();
  });

  it('Pod 加载完成后显示 phase 状态', () => {
    setupOpenTab([{ id: 'tab-1', type: 'pod', namespace: 'default', name: 'running-pod' }]);
    mockQueryResult = {
      data: {
        name: 'running-pod',
        namespace: 'default',
        phase: 'Running',
        containers: [],
        init_containers: [],
        node_name: 'node-1',
        ip: '10.0.0.1',
        created_at: '2024-01-01',
      },
      isLoading: false,
      isError: false,
    };

    renderWithProviders(<PodDetail />);

    expect(screen.getByText('Running')).toBeTruthy();
  });

  it('非 pod 类型显示暂未实现提示', () => {
    setupOpenTab([{ id: 'tab-1', type: 'deployment', namespace: 'default', name: 'my-deploy' }]);
    mockQueryResult = { data: undefined, isLoading: false, isError: false };

    renderWithProviders(<PodDetail />);

    expect(screen.getByText(/暂未实现/)).toBeTruthy();
  });

  it('子 Tab 切换功能正常', () => {
    setupOpenTab([{ id: 'tab-1', type: 'pod', namespace: 'default', name: 'test-pod' }]);
    mockQueryResult = {
      data: {
        name: 'test-pod',
        namespace: 'default',
        phase: 'Running',
        containers: [],
        init_containers: [],
        node_name: 'node-1',
        ip: '10.0.0.1',
        created_at: '2024-01-01',
      },
      isLoading: false,
      isError: false,
    };

    renderWithProviders(<PodDetail />);

    // 默认显示概览面板
    expect(screen.getByTestId('overview-panel')).toBeTruthy();

    // 点击 YAML tab
    fireEvent.click(screen.getByText('YAML'));
    // 验证 store 中的 activeSubTabs 已更新为 yaml
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBe('yaml');
    expect(screen.getByTestId('yaml-panel')).toBeTruthy();

    // 点击事件 tab
    fireEvent.click(screen.getByText('事件'));
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBe('events');
    expect(screen.getByTestId('events-panel')).toBeTruthy();
  });

  it('加载状态时显示加载中提示', () => {
    setupOpenTab([{ id: 'tab-1', type: 'pod', namespace: 'default', name: 'loading-pod' }]);
    mockQueryResult = { data: undefined, isLoading: true, isError: false };

    renderWithProviders(<PodDetail />);

    expect(screen.getByText('加载中...')).toBeTruthy();
  });

  it('查询出错时显示资源未找到', () => {
    setupOpenTab([{ id: 'tab-1', type: 'pod', namespace: 'default', name: 'error-pod' }]);
    mockQueryResult = { data: undefined, isLoading: false, isError: true };

    renderWithProviders(<PodDetail />);

    expect(screen.getByText('资源未找到')).toBeTruthy();
  });
});

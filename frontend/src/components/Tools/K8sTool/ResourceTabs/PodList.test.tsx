/**
 * PodList 组件单元测试
 *
 * 测试重点：
 * - 点击 Pod 行调用 openResourceTab，传入正确的 id 格式 `pod-${namespace}-${name}`
 * - openResourceTab 接收到 type='pod' 以及 namespace、name 字段
 * - 多次点击同一个 Pod 仍能持续调用 openResourceTab（去重由 store 内部处理）
 */
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { PodList } from './PodList';

// ---------- Mock 子模块 ----------

/** 模拟 useK8sStore 行为（每个测试可覆盖） */
const mockOpenResourceTab = vi.fn();

const mockStoreState = {
  activeConnectionId: 'conn-1' as string | null,
  selectedNamespaces: ['default'] as string[],
  namespaces: ['default', 'production'] as string[],
};

vi.mock('../../../../stores/k8sStore', () => ({
  useK8sStore: () => ({
    ...mockStoreState,
    openResourceTab: (...args: unknown[]) => mockOpenResourceTab(...args),
  }),
}));

/** 模拟 useI18n */
vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    t: {
      common: {
        loading: '加载中...',
      },
      tools: {
        'k8s-tool': {
          errors: { CONNECTION_FAILED: '连接失败' },
          podList: {
            status: '状态',
            name: '名称',
            restarts: '重启',
            age: '运行时间',
            node: '节点',
            ip: 'IP',
            noPods: '暂无 Pod',
            searchPlaceholder: '搜索 Pod 名称...',
            noMatch: '未找到匹配的 Pod: "{text}"',
          },
        },
      },
    },
  }),
}));

/** 模拟 useK8sPods — 默认返回空列表 */
let mockPods: Array<{
  name: string;
  namespace: string;
  phase: string;
  status: string;
  restarts: number;
  created_at: string;
  node: string;
  pod_ip: string;
}> = [];

let mockIsLoading = false;
let mockError: Error | null = null;

vi.mock('../../../../hooks/useK8sClient', () => ({
  useK8sPods: () => ({
    data: mockPods,
    isLoading: mockIsLoading,
    error: mockError,
  }),
}));

/** 构建测试用的 QueryClient */
const createQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

/** 包装组件渲染 */
const renderWithProviders = (ui: React.ReactElement) => {
  const qc = createQueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
};

beforeEach(() => {
  mockOpenResourceTab.mockClear();
  mockPods = [];
  mockIsLoading = false;
  mockError = null;
  mockStoreState.activeConnectionId = 'conn-1';
  mockStoreState.selectedNamespaces = ['default'];
  mockStoreState.namespaces = ['default', 'production'];
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ---------- 测试用例 ----------

describe('PodList - 点击行打开标签页', () => {
  it('点击 Pod 行调用 openResourceTab，id 格式为 `pod-${namespace}-${name}`', () => {
    mockPods = [
      {
        name: 'nginx-abc',
        namespace: 'production',
        phase: 'Running',
        status: '',
        restarts: 0,
        created_at: '2024-01-01T00:00:00Z',
        node: 'node-1',
        pod_ip: '10.0.0.1',
      },
    ];

    renderWithProviders(<PodList />);

    // 找到 Pod 名称所在的行（通过 aria/name 定位不可行，采用查询所有行后点击）
    const podName = screen.getByText('nginx-abc');
    const row = podName.closest('tr');
    expect(row).not.toBeNull();

    fireEvent.click(row!);

    expect(mockOpenResourceTab).toHaveBeenCalledTimes(1);
    expect(mockOpenResourceTab).toHaveBeenCalledWith({
      id: 'pod-production-nginx-abc',
      type: 'pod',
      namespace: 'production',
      name: 'nginx-abc',
    });
  });

  it('openResourceTab 接收 type、namespace、name 字段', () => {
    mockPods = [
      {
        name: 'redis-1',
        namespace: 'cache',
        phase: 'Pending',
        status: '',
        restarts: 2,
        created_at: '2024-01-02T00:00:00Z',
        node: 'node-2',
        pod_ip: '10.0.0.2',
      },
    ];

    renderWithProviders(<PodList />);
    const podName = screen.getByText('redis-1');
    const row = podName.closest('tr');
    fireEvent.click(row!);

    // 验证所有字段都被正确传递
    const call = mockOpenResourceTab.mock.calls[0]?.[0] as {
      type: string;
      namespace: string;
      name: string;
      id: string;
    };
    expect(call.type).toBe('pod');
    expect(call.namespace).toBe('cache');
    expect(call.name).toBe('redis-1');
    expect(call.id).toBe('pod-cache-redis-1');
  });

  it('多次点击同一个 Pod 行，每次都调用 openResourceTab', () => {
    mockPods = [
      {
        name: 'api-server',
        namespace: 'backend',
        phase: 'Running',
        status: '',
        restarts: 0,
        created_at: '2024-01-01T00:00:00Z',
        node: 'node-3',
        pod_ip: '10.0.0.3',
      },
    ];

    renderWithProviders(<PodList />);
    const podName = screen.getByText('api-server');
    const row = podName.closest('tr');

    // 多次点击同一行
    fireEvent.click(row!);
    fireEvent.click(row!);
    fireEvent.click(row!);

    expect(mockOpenResourceTab).toHaveBeenCalledTimes(3);
    // 每次都传入相同的参数（去重逻辑由 store 内部处理）
    expect(mockOpenResourceTab).toHaveBeenNthCalledWith(1, {
      id: 'pod-backend-api-server',
      type: 'pod',
      namespace: 'backend',
      name: 'api-server',
    });
    expect(mockOpenResourceTab).toHaveBeenNthCalledWith(2, {
      id: 'pod-backend-api-server',
      type: 'pod',
      namespace: 'backend',
      name: 'api-server',
    });
    expect(mockOpenResourceTab).toHaveBeenNthCalledWith(3, {
      id: 'pod-backend-api-server',
      type: 'pod',
      namespace: 'backend',
      name: 'api-server',
    });
  });

  it('多个 Pod 时点击不同行能分别打开对应标签', () => {
    mockPods = [
      {
        name: 'pod-a',
        namespace: 'ns-a',
        phase: 'Running',
        status: '',
        restarts: 0,
        created_at: '2024-01-01',
        node: 'node-1',
        pod_ip: '10.0.0.1',
      },
      {
        name: 'pod-b',
        namespace: 'ns-b',
        phase: 'Pending',
        status: '',
        restarts: 1,
        created_at: '2024-01-02',
        node: 'node-2',
        pod_ip: '10.0.0.2',
      },
    ];

    renderWithProviders(<PodList />);

    const podAName = screen.getByText('pod-a');
    const rowA = podAName.closest('tr');
    fireEvent.click(rowA!);

    const podBName = screen.getByText('pod-b');
    const rowB = podBName.closest('tr');
    fireEvent.click(rowB!);

    expect(mockOpenResourceTab).toHaveBeenCalledTimes(2);
    expect(mockOpenResourceTab).toHaveBeenNthCalledWith(1, {
      id: 'pod-ns-a-pod-a',
      type: 'pod',
      namespace: 'ns-a',
      name: 'pod-a',
    });
    expect(mockOpenResourceTab).toHaveBeenNthCalledWith(2, {
      id: 'pod-ns-b-pod-b',
      type: 'pod',
      namespace: 'ns-b',
      name: 'pod-b',
    });
  });

  it('搜索过滤后点击过滤结果行', () => {
    mockPods = [
      {
        name: 'web-1',
        namespace: 'default',
        phase: 'Running',
        status: '',
        restarts: 0,
        created_at: '2024-01-01',
        node: 'node-1',
        pod_ip: '10.0.0.1',
      },
      {
        name: 'db-1',
        namespace: 'default',
        phase: 'Running',
        status: '',
        restarts: 0,
        created_at: '2024-01-01',
        node: 'node-1',
        pod_ip: '10.0.0.2',
      },
    ];

    renderWithProviders(<PodList />);

    // 搜索 "db"
    const searchInput = screen.getByPlaceholderText('搜索 Pod 名称...');
    fireEvent.change(searchInput, { target: { value: 'db' } });

    // db-1 应可见，web-1 应不可见
    expect(screen.getByText('db-1')).toBeTruthy();
    expect(screen.queryByText('web-1')).toBeNull();

    const dbName = screen.getByText('db-1');
    const row = dbName.closest('tr');
    fireEvent.click(row!);

    expect(mockOpenResourceTab).toHaveBeenCalledTimes(1);
    expect(mockOpenResourceTab).toHaveBeenCalledWith({
      id: 'pod-default-db-1',
      type: 'pod',
      namespace: 'default',
      name: 'db-1',
    });
  });
});
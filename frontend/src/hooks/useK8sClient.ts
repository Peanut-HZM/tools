/**
 * K8s 控制台工具 - React Query Hooks
 *
 * 封装各资源的查询 hooks，自动管理缓存、轮询刷新和命名空间多选合并
 */
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as api from '../api/k8sToolApi';
import { useK8sStore } from '../stores/k8sStore';
import { useAuth } from '../stores/authStore';
import type { K8sPodMetrics, K8sPodSummary } from '../components/Tools/K8sTool/types';

/**
 * 获取当前用户所有 K8s 连接配置列表
 * 30 秒轮询刷新，自动同步到 zustand store
 * 未登录时禁用（不发请求）；登录成功后 authVersion 变化触发重新请求
 */
export const useK8sConnections = () => {
  const { setConnections } = useK8sStore();
  const { isAuthenticated, authVersion } = useAuth();
  return useQuery({
    // authVersion 加入 queryKey：登录成功/401 后自动以新 key 重新请求
    queryKey: ['k8s', 'connections', authVersion],
    queryFn: async () => {
      const data = await api.getK8sConfigs();
      setConnections(data);
      return data;
    },
    enabled: isAuthenticated,
    refetchInterval: 30_000,
  });
};

/**
 * 获取指定连接的命名空间列表
 * 仅在 configId 存在时启用，自动同步到 store
 */
export const useK8sNamespaces = (configId: string | null) => {
  const { setNamespaces } = useK8sStore();
  const { isAuthenticated } = useAuth();
  const query = useQuery({
    queryKey: ['k8s', configId, 'namespaces'],
    queryFn: async () => {
      if (!configId) return [];
      return api.listNamespaces(configId);
    },
    enabled: isAuthenticated && !!configId,
    // 失败（无数据）时 5 秒快速重试自愈（后端热重载 / K8s API 瞬时抖动），
    // 成功后 60 秒低频刷新。namespaces 无自愈会导致 URL 工作区恢复误报错误。
    refetchInterval: (query) => (query.state.data ? 60_000 : 5_000),
  });

  useEffect(() => {
    if (!configId || !query.data) return;

    // 仅允许当前激活集群的响应更新工作区，避免旧请求完成后覆盖新集群命名空间。
    if (useK8sStore.getState().activeConnectionId !== configId) return;
    setNamespaces(query.data.map((namespace) => namespace.name));
  }, [configId, query.data, setNamespaces]);

  return query;
};

/**
 * 获取多命名空间下的 Pod 列表（合并结果，分页格式）
 * 10 秒轮询刷新
 */
export const useK8sPods = (configId: string | null, namespaces: string[]) => {
  return useQuery({
    queryKey: ['k8s', configId, 'pods', namespaces],
    queryFn: async () => {
      if (!configId || namespaces.length === 0) return { items: [] as K8sPodSummary[], total: 0 };
      // 多 namespace 并发请求后合并
      const results = await Promise.all(
        namespaces.map((ns) => api.listPods(configId, ns))
      );
      return {
        items: results.flatMap((r) => r.items),
        total: results.reduce((sum, r) => sum + r.total, 0),
      };
    },
    enabled: !!configId && namespaces.length > 0,
    refetchInterval: 10_000,
  });
};

/**
 * 获取集群所有 Node 列表
 * 30 秒轮询刷新
 */
export const useK8sNodes = (configId: string | null) => {
  return useQuery({
    queryKey: ['k8s', configId, 'nodes'],
    queryFn: () => (configId ? api.listNodes(configId) : []),
    enabled: !!configId,
    refetchInterval: 30_000,
  });
};

/**
 * 获取多命名空间下的 Deployment 列表（合并结果）
 * 10 秒轮询刷新
 */
export const useK8sDeployments = (configId: string | null, namespaces: string[]) => {
  return useQuery({
    queryKey: ['k8s', configId, 'deployments', namespaces],
    queryFn: async () => {
      if (!configId || namespaces.length === 0) return [];
      const results = await Promise.all(
        namespaces.map((ns) => api.listDeployments(configId, ns))
      );
      return results.flat();
    },
    enabled: !!configId && namespaces.length > 0,
    refetchInterval: 10_000,
  });
};

/**
 * 获取多命名空间下的事件列表（合并结果）
 * 15 秒轮询刷新
 */
export const useK8sEvents = (configId: string | null, namespaces: string[]) => {
  return useQuery({
    queryKey: ['k8s', configId, 'events', namespaces],
    queryFn: async () => {
      if (!configId || namespaces.length === 0) return [];
      const results = await Promise.all(
        namespaces.map((ns) => api.listEvents(configId, ns))
      );
      return results.flat();
    },
    enabled: !!configId && namespaces.length > 0,
    refetchInterval: 15_000,
  });
};

/**
 * 获取单个 Pod 的实时 Metrics 指标（CPU / 内存使用量）
 * 15 秒轮询刷新，仅在 configId 存在且 podName 有效时启用
 */
export const usePodMetrics = (
  configId: string | null,
  podName: string,
  namespace: string,
) => {
  return useQuery<K8sPodMetrics | null>({
    queryKey: ['k8s', configId, 'metrics', podName, namespace],
    // 后端尚未提供 Pod metrics REST 端点。禁用查询，避免向不存在的接口发请求，
    // 由指标面板明确呈现不可用状态，不用静态数据替代真实指标。
    queryFn: async () => {
      throw new Error('后端尚未提供 Pod 指标接口');
    },
    enabled: false,
    retry: false,
  });
};

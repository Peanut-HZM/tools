/**
 * K8s 控制台工具 - React Query Hooks
 *
 * 封装各资源的查询 hooks，自动管理缓存、轮询刷新和命名空间多选合并
 */
import { useQuery } from '@tanstack/react-query';
import * as api from '../api/k8sToolApi';
import { useK8sStore } from '../stores/k8sStore';
import { useAuth } from '../stores/authStore';
import type { K8sPodSummary } from '../components/Tools/K8sTool/types';

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
  return useQuery({
    queryKey: ['k8s', configId, 'namespaces'],
    queryFn: async () => {
      if (!configId) return [];
      const data = await api.listNamespaces(configId);
      const names = data.map((n) => n.name);
      setNamespaces(names);
      return data;
    },
    enabled: !!configId,
  });
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
  return useQuery({
    queryKey: ['k8s', configId, 'metrics', podName, namespace],
    queryFn: () =>
      configId ? api.getPodMetrics(configId, podName, namespace) : null,
    enabled: !!configId && !!podName && !!namespace,
    refetchInterval: 15_000,
    retry: false,
  });
};

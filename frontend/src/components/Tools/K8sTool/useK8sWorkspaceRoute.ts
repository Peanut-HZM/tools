import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useK8sStore } from '../../../stores/k8sStore';
import {
  parseK8sWorkspaceSearch,
  serializeK8sWorkspaceSearch,
} from './k8sWorkspaceUrl';

/**
 * 将可分享的 K8s 工作上下文映射到 URL，并在页面进入时恢复。
 * 仅保存非敏感的连接 ID、资源类型及命名空间；资源数据始终重新从 API 获取。
 *
 * 恢复策略：URL 中的筛选条件是用户上次真实使用过的状态，直接信任并应用，
 * 不经命名空间列表接口校验——校验会让瞬时恢复强依赖一个可失败的接口
 * （后端热重载 / K8s API 抖动即卡住或误报错误）。若某个命名空间确已不存在，
 * 资源查询自然返回空列表，用户调整筛选即可。
 */
export function useK8sWorkspaceRoute(
  onInvalidContext: (message: string) => void,
  connectionsReady: boolean,
): boolean {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentSearch = searchParams.toString();
  const reportedInvalidCluster = useRef<string | null>(null);
  const lastWrittenSearch = useRef<string | null>(null);
  const [pendingSearch, setPendingSearch] = useState<string | null>(currentSearch);

  const {
    connections,
    activeConnectionId,
    selectedNamespaces,
    resourceType,
    setActiveConnection,
    setSelectedNamespaces,
    setResourceType,
  } = useK8sStore();

  useEffect(() => {
    // 仅浏览器历史/外部链接变更触发恢复；由本 Hook 回写的 URL 不应再次覆盖用户操作。
    if (lastWrittenSearch.current === currentSearch) {
      lastWrittenSearch.current = null;
      return;
    }
    setPendingSearch(currentSearch);
  }, [currentSearch]);

  useEffect(() => {
    if (pendingSearch === null) return;
    const routeState = parseK8sWorkspaceSearch(pendingSearch);

    if (!routeState.connectionId) {
      if (resourceType !== routeState.resourceType) {
        setResourceType(routeState.resourceType);
        return;
      }
      setPendingSearch(null);
      return;
    }

    if (!connectionsReady) return;
    if (!connections.some((connection) => connection.id === routeState.connectionId)) {
      if (reportedInvalidCluster.current !== routeState.connectionId) {
        reportedInvalidCluster.current = routeState.connectionId;
        onInvalidContext('链接中的集群已不存在，已保留当前可用工作区。');
      }
      setPendingSearch(null);
      return;
    }

    if (activeConnectionId !== routeState.connectionId) {
      setActiveConnection(routeState.connectionId);
      return;
    }

    if (resourceType !== routeState.resourceType) {
      setResourceType(routeState.resourceType);
      return;
    }

    // 直接信任 URL 中的命名空间筛选（空数组明确代表"所有命名空间"，
    // 必须覆盖切换集群后的默认 default），不做服务端校验。
    const changed =
      selectedNamespaces.length !== routeState.namespaces.length ||
      selectedNamespaces.some((ns, i) => ns !== routeState.namespaces[i]);
    if (changed) {
      setSelectedNamespaces(routeState.namespaces);
    }
    setPendingSearch(null);
  }, [
    activeConnectionId,
    connections,
    connectionsReady,
    onInvalidContext,
    pendingSearch,
    resourceType,
    selectedNamespaces,
    setActiveConnection,
    setSelectedNamespaces,
    setResourceType,
  ]);

  useEffect(() => {
    if (pendingSearch !== null || !activeConnectionId) return;

    const nextSearch = serializeK8sWorkspaceSearch({
      connectionId: activeConnectionId,
      resourceType,
      namespaces: selectedNamespaces,
    }, currentSearch);
    const nextRawSearch = nextSearch.startsWith('?') ? nextSearch.slice(1) : nextSearch;
    if (nextRawSearch !== currentSearch) {
      lastWrittenSearch.current = nextRawSearch;
      setSearchParams(nextRawSearch, { replace: true });
    }
  }, [
    activeConnectionId,
    currentSearch,
    pendingSearch,
    resourceType,
    selectedNamespaces,
    setSearchParams,
  ]);

  return pendingSearch === null;
}

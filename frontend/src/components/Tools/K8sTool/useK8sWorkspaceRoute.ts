import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useK8sNamespaces } from '../../../hooks/useK8sClient';
import { useK8sStore } from '../../../stores/k8sStore';
import {
  parseK8sWorkspaceSearch,
  serializeK8sWorkspaceSearch,
} from './k8sWorkspaceUrl';

function equalValues(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

/**
 * 命名空间查询持续失败多久后放弃 URL 恢复并提示（毫秒）。
 * 瞬时失败（后端热重载 / K8s API 抖动）在此窗口内会自动自愈，
 * 自愈后恢复流程继续，用户完全无感；持续失败才提示"无法获取命名空间"。
 */
const NAMESPACE_ERROR_GIVE_UP_MS = 30_000;

/**
 * 将可分享的 K8s 工作上下文映射到 URL，并在连接/命名空间有效时恢复。
 * 仅保存非敏感的连接 ID、资源类型及命名空间；资源数据始终重新从 API 获取。
 */
export function useK8sWorkspaceRoute(
  onInvalidContext: (message: string) => void,
  connectionsReady: boolean,
): boolean {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentSearch = searchParams.toString();
  const reportedInvalidCluster = useRef<string | null>(null);
  const reportedInvalidNamespaces = useRef<string | null>(null);
  const namespaceErrorSince = useRef<number | null>(null);
  const namespaceErrorReported = useRef(false);
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
  const namespacesQuery = useK8sNamespaces(activeConnectionId);
  // 定时器回调中读取最新查询状态：5 秒重试周期内 isError 会短暂回 false（status 变 pending），
  // 若依赖 cleanup 清 timer 会被重试反复打断，30 秒放弃逻辑永远无法触发
  const namespacesQueryRef = useRef(namespacesQuery);
  namespacesQueryRef.current = namespacesQuery;

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

    if (namespacesQuery.isError) {
      // 瞬时失败（后端热重载 / K8s API 抖动）在此窗口内由 refetchInterval 快速重试自愈，
      // 自愈后 isError 恢复 false、本 effect 重新执行，恢复流程继续，用户无感。
      // 持续失败超过阈值才提示一次并放弃 URL 恢复（保留当前筛选条件）。
      if (namespaceErrorReported.current) return;
      if (namespaceErrorSince.current === null) {
        namespaceErrorSince.current = Date.now();
      }
      const remaining =
        NAMESPACE_ERROR_GIVE_UP_MS - (Date.now() - namespaceErrorSince.current);
      if (remaining <= 0) {
        namespaceErrorReported.current = true;
        onInvalidContext('无法获取命名空间，已保留当前筛选条件。');
        namespaceErrorSince.current = null;
        setPendingSearch(null);
        return;
      }
      // 注意：重试发起时 isError 会短暂回 false 并重跑本 effect，因此这里
      // 不能用 cleanup 清定时器（会被 5 秒重试反复打断）。定时器跨重试存活，
      // 到期时通过 ref 读取最新状态，仍处失败才放弃。
      setTimeout(() => {
        if (namespaceErrorReported.current) return;
        if (!namespacesQueryRef.current.isError) return;
        namespaceErrorReported.current = true;
        onInvalidContext('无法获取命名空间，已保留当前筛选条件。');
        namespaceErrorSince.current = null;
        setPendingSearch(null);
      }, remaining);
      return;
    }
    // 查询正常：重置错误跟踪，后续新的失败重新计时
    namespaceErrorSince.current = null;
    namespaceErrorReported.current = false;
    if (!namespacesQuery.isSuccess || !namespacesQuery.data) return;

    // 以本次查询数据校验，而不是等待其同步进 store，避免旧集群 namespace 短暂污染判断。
    const availableNamespaces = namespacesQuery.data.map((namespace) => namespace.name);
    const validNamespaces = routeState.namespaces.filter((namespace) =>
      availableNamespaces.includes(namespace)
    );
    if (!equalValues(validNamespaces, routeState.namespaces)) {
      const invalidKey = `${activeConnectionId}:${routeState.namespaces.join(',')}`;
      if (reportedInvalidNamespaces.current !== invalidKey) {
        reportedInvalidNamespaces.current = invalidKey;
        onInvalidContext('链接中的部分命名空间已不存在，已移除无效筛选条件。');
      }
    }
    // 空数组明确代表“所有命名空间”，必须覆盖切换集群后的默认 default。
    if (!equalValues(selectedNamespaces, validNamespaces)) {
      setSelectedNamespaces(validNamespaces);
    }
    setPendingSearch(null);
  }, [
    activeConnectionId,
    connections,
    connectionsReady,
    namespacesQuery.isSuccess,
    namespacesQuery.isError,
    namespacesQuery.data,
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

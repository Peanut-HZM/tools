import { useEffect, useRef } from 'react';
import { useK8sStore } from '../../../stores/k8sStore';

/**
 * K8s 工作上下文校验（恢复后确认仍有效）。
 *
 * ## 为什么不再使用 URL 参数
 *
 * 早期实现把 `cluster` / `resource` / `namespaces` 写进地址栏
 * （`/workspace?cluster=xxx&resource=pods&namespaces=yyy`）。这带来两个问题：
 *
 * 1. **地址栏被工具内部参数污染**：用户的需求是地址栏只保留
 *    `/workspace/<工具编码>`，工具内部的选择（集群、命名空间、资源类型）
 *    不应出现在 URL 里。
 * 2. **分享链接会带上易过期的上下文**：集群 ID、命名空间都属于易变状态，
 *    贴给同事后大概率指向不存在的集群。
 *
 * 现在改为：
 * - 工具内部上下文 → `k8sStore`（zustand persist，落在 localStorage），
 *   刷新页面后自动恢复，**不进入地址栏**；
 * - 地址栏 → 只由工作区页签路由 `/workspace/<工具编码>` 表达。
 *
 * ## 本 Hook 的职责
 *
 * persist 会在页面加载时自动恢复上次的集群 / 命名空间 / 资源类型，
 * 但持久化的集群 ID 可能已被删除（连接在别处被移除）。因此这里用
 * **已加载的连接列表**做一次校验：
 * - 连接列表尚未加载完成 → 等待
 * - 集群 ID 不存在 → 提示一次并清掉失效引用（不重复打扰）
 * - 集群 ID 有效 → 无需干预
 */
export function useK8sWorkspaceRoute(
  onInvalidContext: (message: string) => void,
  connectionsReady: boolean,
): boolean {
  const reportedInvalidCluster = useRef<string | null>(null);
  const { connections, activeConnectionId, setActiveConnection } = useK8sStore();

  useEffect(() => {
    if (!connectionsReady) return;
    if (!activeConnectionId) return;

    if (!connections.some((connection) => connection.id === activeConnectionId)) {
      // 持久化的集群已不存在：提示一次（不重复打扰），并清掉失效的集群引用
      if (reportedInvalidCluster.current !== activeConnectionId) {
        reportedInvalidCluster.current = activeConnectionId;
        onInvalidContext('上次使用的集群已不存在，已保留当前可用工作区。');
      }
      setActiveConnection('');
    }
  }, [activeConnectionId, connections, connectionsReady, onInvalidContext, setActiveConnection]);

  return true;
}

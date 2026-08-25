/**
 * K8s 控制台 - 集群切换器
 *
 * 顶部下拉菜单，按 last_test_at 排序（最近测试的在前）
 * 健康状态用绿/红/灰圆点指示
 */
import React, { useState, useRef, useEffect } from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useI18n } from '../../../../i18n';
import type { K8sConnection } from '../types';

/**
 * 根据测试结果返回健康状态圆点颜色类名
 */
function getHealthDotClass(conn: K8sConnection): string {
  if (conn.last_test_error) return 'bg-red-500';
  if (conn.last_test_at) return 'bg-green-500';
  return 'bg-surface-3';
}

/**
 * 按 last_test_at 降序排序连接
 * 有时间的排在前面，null 的排最后
 */
function sortByLastTest(connections: K8sConnection[]): K8sConnection[] {
  return [...connections].sort((a, b) => {
    if (!a.last_test_at && !b.last_test_at) return 0;
    if (!a.last_test_at) return 1;
    if (!b.last_test_at) return -1;
    return new Date(b.last_test_at).getTime() - new Date(a.last_test_at).getTime();
  });
}

export const ClusterSwitcher: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { connections, activeConnectionId, setActiveConnection } = useK8sStore();

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 当前活跃连接
  const activeConn = connections.find((c) => c.id === activeConnectionId);
  // 按 last_test_at 排序的连接列表
  const sortedConns = sortByLastTest(connections);

  return (
    <div ref={dropdownRef} className="relative">
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-surface-1 border border-border rounded-md text-sm text-ink hover:border-border hover:bg-surface-2 transition-colors min-w-[180px] max-w-[260px]"
      >
        {activeConn ? (
          <>
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getHealthDotClass(activeConn)}`}></span>
            <span className="truncate">{activeConn.name}</span>
          </>
        ) : (
          <span className="text-ink-faint">{k8sT.topBar.selectCluster}</span>
        )}
        <i className={`fas fa-chevron-down ml-auto text-xs text-ink-muted transition-transform ${isOpen ? 'rotate-180' : ''}`}></i>
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-72 max-h-80 overflow-y-auto bg-surface-1 border border-border rounded-md shadow-lg z-50">
          {sortedConns.length === 0 ? (
            <div className="px-3 py-4 text-sm text-ink-faint text-center">
              {k8sT.emptyConnections}
            </div>
          ) : (
            <ul>
              {sortedConns.map((conn) => {
                const isActive = conn.id === activeConnectionId;
                return (
                  <li
                    key={conn.id}
                    onClick={() => {
                      setActiveConnection(conn.id);
                      setIsOpen(false);
                    }}
                    className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                      isActive
                        ? 'bg-accent/20 text-accent-info'
                        : 'text-ink-muted hover:bg-surface-2 hover:text-ink-inverse'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getHealthDotClass(conn)}`}></span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{conn.name}</div>
                      <div className="text-xs text-ink-faint truncate">{conn.server || conn.cluster_name}</div>
                    </div>
                    {isActive && (
                      <i className="fas fa-check text-accent-info text-xs flex-shrink-0"></i>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

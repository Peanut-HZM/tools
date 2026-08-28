/**
 * K8s 控制台 - Pod 列表（分页 + 滚动修复）
 *
 * 表格展示：状态图标、名称、重启次数、运行时间、节点、IP
 * 点击行触发 openResourceTab 打开对应标签页
 * 支持分页查询，每页默认 20 条，可切换 10/20/50
 * 修复 BottomPanel 遮挡导致的滚动问题
 */
import React, { useState, useMemo, useCallback } from 'react';
import { Search, X, Loader2, AlertTriangle, Download } from 'lucide-react';
import { useK8sStore } from '../../../../stores/k8sStore';
import { useK8sPods } from '../../../../hooks/useK8sClient';
import { useI18n } from '../../../../i18n';
import { useToast } from '../../../../hooks/useToast';
import { downloadPodLogs } from '../../../../api/k8sToolApi';
import { formatAge, getStatusColor, getStatusIcon } from './utils';
import { Input } from '@/components/ui/Input';
import { Pagination } from '../Pagination';

/** 默认每页条数 */
const DEFAULT_PAGE_SIZE = 20;

export const PodList: React.FC = () => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const {
    activeConnectionId,
    selectedNamespaces,
    namespaces,
    openResourceTab,
    openedTabs,
  } = useK8sStore();
  const { addToast } = useToast();
  const [searchText, setSearchText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  // 有效命名空间：空数组表示"所有"，此时使用 store 中的全部 namespaces
  const effectiveNamespaces = selectedNamespaces.length === 0 ? namespaces : selectedNamespaces;
  const { data, isLoading, error } = useK8sPods(activeConnectionId, effectiveNamespaces);

  // 解构分页响应
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const isError = !!error;
  const errorMessage = error instanceof Error ? error.message : k8sT.errors.CONNECTION_FAILED;

  // 按名称过滤 + 分页切片
  const { filteredItems, totalPages, pageItems, pageStart, pageEnd } = useMemo(() => {
    const filtered = searchText
      ? items.filter((pod) => pod.name.toLowerCase().includes(searchText.toLowerCase()))
      : items;
    const tp = Math.max(1, Math.ceil(filtered.length / pageSize));
    // 当前页码越界时回退到最后一页
    const safePage = Math.min(currentPage, tp);
    const start = (safePage - 1) * pageSize;
    const end = Math.min(safePage * pageSize, filtered.length);
    const pageData = filtered.slice(start, end);
    return {
      filteredItems: filtered,
      totalPages: tp,
      pageItems: pageData,
      pageStart: filtered.length === 0 ? 0 : start + 1,
      pageEnd: end,
    };
  }, [items, searchText, pageSize, currentPage]);

  // 搜索文本变化时重置到第 1 页
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value);
    setCurrentPage(1);
  }, []);

  const handleClearSearch = useCallback(() => {
    setSearchText('');
    setCurrentPage(1);
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  }, []);

  /** 点击行，打开该 Pod 的资源标签页 */
  const handleRowClick = useCallback((pod: typeof items[0]) => {
    openResourceTab({
      id: `pod-${pod.namespace}-${pod.name}`,
      type: 'pod',
      namespace: pod.namespace,
      name: pod.name,
    });
  }, [openResourceTab]);

  /** 下载 Pod 完整日志 */
  const handleDownloadLogs = useCallback(async (podName: string, namespace: string) => {
    try {
      const text = await downloadPodLogs(activeConnectionId, podName, namespace);
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${podName}-logs.txt`;
      a.click();
      URL.revokeObjectURL(url);
      addToast('日志下载成功', 'success');
    } catch {
      addToast('下载日志失败', 'error');
    }
  }, [activeConnectionId, addToast]);

  // 当 BottomPanel 打开时加底部内边距，防止最后一行被遮挡
  const hasBottomPanel = openedTabs.length > 0;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 搜索框 */}
      <div className="px-3 py-2 border-b border-border bg-surface-1/50 shrink-0">
        <div className="flex items-center gap-2">
          <Search className="w-3 h-3 text-ink-faint" />
          <Input
            type="text"
            value={searchText}
            onChange={handleSearchChange}
            placeholder={k8sT.podList.searchPlaceholder}
            className="flex-1 h-7 px-2 text-xs"
          />
          {searchText && (
            <button
              onClick={handleClearSearch}
              className="text-ink-faint hover:text-ink-muted px-1"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* 表格 */}
      <div className={`flex-1 overflow-y-auto ${hasBottomPanel ? 'pb-4' : ''}`}>
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface-1 text-ink-muted border-b border-border z-10">
            <tr>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.status}</th>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.name}</th>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.restarts}</th>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.age}</th>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.node}</th>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.ip}</th>
              <th className="text-left px-3 py-2 font-medium">{k8sT.podList.actions}</th>
            </tr>
          </thead>
          <tbody>
            {/* 加载中 */}
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-ink-faint">
                  <Loader2 className="w-4 h-4 mr-2 animate-spin inline" />
                  {t.common.loading}
                </td>
              </tr>
            )}

            {/* 请求出错 */}
            {isError && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-danger">
                  <AlertTriangle className="w-4 h-4 mr-2 inline" />
                  {errorMessage}
                </td>
              </tr>
            )}

            {/* 空数据 */}
            {!isLoading && !isError && filteredItems.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-ink-faint">
                  {searchText
                    ? k8sT.podList.noMatch.replace('{text}', searchText)
                    : k8sT.podList.noPods}
                </td>
              </tr>
            )}

            {/* Pod 行 */}
            {pageItems.map((pod) => (
              <tr
                key={`${pod.namespace}/${pod.name}`}
                onClick={() => handleRowClick(pod)}
                className="border-b border-border hover:bg-surface-1/50 cursor-pointer transition-colors"
              >
                {/* 状态图标 */}
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    {(() => {
                      const StatusIcon = getStatusIcon(pod.phase, pod.status);
                      return <StatusIcon className={`w-4 h-4 ${getStatusColor(pod.phase, pod.status)}`} />;
                    })()}
                    <span className={`${getStatusColor(pod.phase, pod.status)} text-xs`}>
                      {pod.phase}
                    </span>
                  </div>
                </td>

                {/* 名称 + 命名空间 */}
                <td className="px-3 py-2">
                  <div className="text-ink font-medium truncate max-w-[240px]">{pod.name}</div>
                  <div className="text-xs text-ink-faint truncate">{pod.namespace}</div>
                </td>

                {/* 重启次数 */}
                <td className="px-3 py-2 text-ink-muted">
                  {pod.restarts > 0 ? (
                    <span className={pod.restarts > 5 ? 'text-danger' : 'text-accent-warning'}>
                      {pod.restarts}
                    </span>
                  ) : (
                    <span className="text-ink-faint">0</span>
                  )}
                </td>

                {/* 运行时间 */}
                <td className="px-3 py-2 text-ink-muted text-xs">
                  {formatAge(pod.created_at)}
                </td>

                {/* 节点 */}
                <td className="px-3 py-2 text-ink-muted truncate max-w-[140px]">
                  {pod.node || '-'}
                </td>

                {/* IP */}
                <td className="px-3 py-2 text-ink-muted font-mono text-xs">
                  {pod.pod_ip || '-'}
                </td>

                {/* 操作：下载日志 */}
                <td className="px-3 py-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownloadLogs(pod.name, pod.namespace);
                    }}
                    className="text-ink-muted hover:text-accent-info transition-colors"
                    title="下载日志"
                  >
                    <Download className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页器 */}
      <Pagination
        total={filteredItems.length}
        currentPage={currentPage}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
      />
    </div>
  );
};

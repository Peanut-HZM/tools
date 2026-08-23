/**
 * useImageGenHistory — 分页 + 刷新触发
 */
import { useEffect, useCallback, useState } from 'react';
import { useImageGenStore } from '../stores/imageGenerationStore';

const PAGE_SIZE = 20;

export function useImageGenHistory() {
  const history = useImageGenStore((s) => s.history);
  const historyTotal = useImageGenStore((s) => s.historyTotal);
  const historyLoading = useImageGenStore((s) => s.historyLoading);
  const loadHistory = useImageGenStore((s) => s.loadHistory);
  const deleteHistory = useImageGenStore((s) => s.deleteHistory);

  const [page, setPage] = useState(0);

  // 初始加载
  useEffect(() => {
    loadHistory(page * PAGE_SIZE, PAGE_SIZE);
  }, [page, loadHistory]);

  const refresh = useCallback(() => {
    loadHistory(page * PAGE_SIZE, PAGE_SIZE);
  }, [page, loadHistory]);

  const goNext = useCallback(() => {
    if ((page + 1) * PAGE_SIZE < historyTotal) {
      setPage((p) => p + 1);
    }
  }, [page, historyTotal]);

  const goPrev = useCallback(() => {
    if (page > 0) setPage((p) => p - 1);
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(historyTotal / PAGE_SIZE));

  return {
    history,
    historyTotal,
    historyLoading,
    refresh,
    deleteHistory,
    page,
    totalPages,
    goNext,
    goPrev,
  };
}

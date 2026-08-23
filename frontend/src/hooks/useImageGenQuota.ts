/**
 * useImageGenQuota — 自动加载配额，每 30 秒刷新
 */
import { useEffect, useCallback } from 'react';
import { useImageGenStore } from '../stores/imageGenerationStore';

const REFRESH_INTERVAL_MS = 30_000;

export function useImageGenQuota() {
  const quota = useImageGenStore((s) => s.quota);
  const loadQuota = useImageGenStore((s) => s.loadQuota);

  useEffect(() => {
    loadQuota();
    const timer = setInterval(loadQuota, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [loadQuota]);

  const refresh = useCallback(() => {
    loadQuota();
  }, [loadQuota]);

  return { quota, refresh };
}

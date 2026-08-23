import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getTokenUsageDetails,
  type TokenUsageDetailsParams,
  type TokenUsageDetailsResponse,
} from '../../../api/tokenUsageApi';

const EMPTY: TokenUsageDetailsResponse = {
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
  has_more: false,
  cached: false,
};

export interface UseTokenUsageDetailsResult {
  data: TokenUsageDetailsResponse;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTokenUsageDetails(
  params: TokenUsageDetailsParams,
  enabled: boolean = true
): UseTokenUsageDetailsResult {
  const [data, setData] = useState<TokenUsageDetailsResponse>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqIdRef = useRef(0);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const refresh = useCallback(async () => {
    if (!enabledRef.current) return;   // 未登录时不发请求
    const reqId = ++reqIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const result = await getTokenUsageDetails(params);
      if (reqId !== reqIdRef.current) return;
      setData(result);
    } catch (err: any) {
      if (reqId !== reqIdRef.current) return;
      setError(err.message || '明细加载失败');
    } finally {
      if (reqId === reqIdRef.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    params.type,
    params.days,
    params.group_by,
    params.source,
    params.device_id,
    params.tool_id,
    params.model,
    params.sort_by,
    params.sort_order,
    params.limit,
    params.offset,
  ]);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
  }, [refresh, enabled]);

  return { data, loading, error, refresh };
}

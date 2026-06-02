import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getTokenUsageSummary,
  type DbQueryParams,
  type TokenUsageSummaryResponse,
} from '../../../api/tokenUsageApi';

const EMPTY: TokenUsageSummaryResponse = {
  summary: {
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_cache_creation_tokens: 0,
    total_cache_read_tokens: 0,
    total_tokens: 0,
    total_cost: 0,
    days_count: 0,
    avg_daily_cost: 0,
  },
  dimension_summaries: { devices: [], tools: [], models: [] },
  model_summary: [],
  filter_options: { tools: [], devices: [], models: [] },
  sync_meta: {
    cache_ttl_seconds: 0,
    is_stale: false,
    refresh_lock: { locked: false, ttl_seconds: 0 },
    sources_status: [],
  },
  chart_series: [],
  cached: false,
  auto_expanded: false,
  actual_days: null,
  devices: [],
};

export interface UseTokenUsageSummaryResult {
  data: TokenUsageSummaryResponse;
  loading: boolean;
  silentLoading: boolean;
  error: string | null;
  refresh: (opts?: { silent?: boolean }) => Promise<void>;
}

export function useTokenUsageSummary(params: DbQueryParams): UseTokenUsageSummaryResult {
  const [data, setData] = useState<TokenUsageSummaryResponse>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [silentLoading, setSilentLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqIdRef = useRef(0);

  const refresh = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = Boolean(opts?.silent);
      const reqId = ++reqIdRef.current;
      if (!silent) {
        setLoading(true);
        setError(null);
      } else {
        setSilentLoading(true);
      }
      try {
        const result = await getTokenUsageSummary(params);
        if (reqId !== reqIdRef.current) return;
        setData(result);
        setError(null);
      } catch (err: any) {
        if (reqId !== reqIdRef.current) return;
        setError(err.message || '概览加载失败');
      } finally {
        if (reqId === reqIdRef.current) {
          if (!silent) setLoading(false);
          else setSilentLoading(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      params.source,
      params.type,
      params.days,
      params.group_by,
      params.device_id,
      params.tool_id,
      params.model,
    ]
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, silentLoading, error, refresh };
}

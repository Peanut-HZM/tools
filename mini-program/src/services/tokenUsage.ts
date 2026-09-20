import { request } from './request';

/**
 * Token 消耗统计 API — 已迁移到 /summary + /details 新接口
 * （原 /db-query 已被后端标记 DEPRECATED，且其响应缺少 total_count/count 等字段，
 * 导致旧页面"请求数"列恒为空）。
 */

export interface DeviceInfo {
  id: string;
  name: string;
}

/** /summary 顶栏汇总（含缓存 token 四项拆分） */
export interface UsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_creation_tokens: number;
  total_cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  days_count: number;
  avg_daily_cost: number;
}

/** chart_series 单项：某日（group_by=none）聚合，含输入/输出/缓存拆分 */
export interface ChartSeriesItem {
  date: string;
  group_key?: string | null;
  total_tokens: number;
  total_cost: number;
  input_tokens: number;
  output_tokens: number;
  cache_tokens: number;
}

export interface SyncMeta {
  last_synced_at?: string | null;
  last_success_at?: string | null;
  latest_record_at?: string | null;
  data_age_seconds?: number | null;
  is_stale: boolean;
  stale_reason?: string | null;
}

export interface SummaryResponse {
  summary: UsageSummary;
  chart_series: ChartSeriesItem[];
  devices: DeviceInfo[];
  sync_meta: SyncMeta;
  cached: boolean;
  auto_expanded: boolean;
  actual_days?: number | null;
}

/** /details 明细行（date × device × source × model 粒度） */
export interface DetailItem {
  date: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  models_used: string[];
  device_id?: string | null;
  device_name?: string | null;
  tool_id?: string | null;
  created_at?: string | null;
}

export interface DetailsResponse {
  items: DetailItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  cached: boolean;
}

export interface RefreshResponse {
  message: string;
  sources_synced: string[];
  total_records: number;
  errors: Array<{ source: string; error: string }>;
  locked: boolean;
}

export const tokenUsageApi = {
  /** 概览查询：汇总 + 每日趋势 + 设备列表 + 同步状态（后端检测过期会自动触发同步） */
  summary: async (params: {
    type?: 'daily' | 'weekly' | 'monthly';
    days?: number;
    device_id?: string;
  } = {}): Promise<SummaryResponse> => {
    const qs = new URLSearchParams();
    qs.append('type', params.type || 'daily');
    qs.append('days', String(params.days || 30));
    if (params.device_id) qs.append('device_id', params.device_id);
    return request(`/token-usage/summary?${qs.toString()}`, { needAuth: true });
  },

  /** 明细查询：date × device × model 粒度分页 */
  details: async (params: {
    type?: 'daily' | 'weekly' | 'monthly';
    days?: number;
    device_id?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<DetailsResponse> => {
    return request('/token-usage/details', {
      method: 'POST',
      data: {
        type: params.type || 'daily',
        days: params.days || 30,
        group_by: 'none',
        source: 'all',
        device_id: params.device_id || null,
        limit: params.limit || 50,
        offset: params.offset || 0,
        sort_by: 'date',
        sort_order: 'desc',
      },
      needAuth: true,
    });
  },

  /** 手动同步（同步式）：拉取本机最近 N 天全部数据源并失效缓存 */
  refresh: async (days: number = 90): Promise<RefreshResponse> => {
    return request('/token-usage/refresh', {
      method: 'POST',
      data: { days, background: false, reason: 'manual' },
      needAuth: true,
    });
  },
};

import { request } from './request';

export interface DeviceInfo {
  id: string;
  name: string;
}

export interface UsageItem {
  date?: string;
  week?: string;
  month?: string;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cost?: number;
  count: number;
}

export interface UsageSummary {
  total_tokens: number;
  total_cost?: number;
  total_count: number;
}

export interface DbQueryResponse {
  items: UsageItem[];
  summary: UsageSummary;
  devices: DeviceInfo[];
  cached: boolean;
  model_summary?: Record<string, number>;
  dimension_summaries?: Record<string, any>;
  filter_options: {
    sources: string[];
    models: string[];
    tools: string[];
  };
  sync_meta?: {
    last_sync: string;
    total_records: number;
  };
}

export interface HealthCheckResponse {
  status: string;
  claude?: { available: boolean; last_sync?: string; record_count: number };
  opencode?: { available: boolean; last_sync?: string; record_count: number };
}

export const tokenUsageApi = {
  healthCheck: async (): Promise<HealthCheckResponse> => {
    return request('/token-usage/health', { needAuth: true });
  },

  queryUsage: async (params: {
    type?: 'daily' | 'weekly' | 'monthly';
    days?: number;
    group_by?: string;
    source?: string;
    device_id?: string;
    model?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  } = {}): Promise<DbQueryResponse> => {
    return request('/token-usage/db-query', {
      method: 'POST',
      data: {
        type: params.type || 'daily',
        days: params.days || 30,
        group_by: params.group_by || 'none',
        source: params.source || 'all',
        device_id: params.device_id,
        model: params.model,
        sort_by: params.sort_by || 'date',
        sort_order: params.sort_order || 'desc',
      },
      needAuth: true,
    });
  },

  getDevices: async (): Promise<{ devices: DeviceInfo[] }> => {
    return request('/token-usage/devices', { needAuth: true });
  },
};

import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const BASE_URL = `${API_BASE_URL}/token-usage`;

export type TokenUsageSource = 'claude' | 'opencode' | 'codex' | 'all';
export type TokenUsageReportType = 'daily' | 'weekly' | 'monthly';
export type TokenUsageGroupBy = 'none' | 'device' | 'tool' | 'model';
export type TokenUsageSortBy = 'date' | 'total_tokens' | 'total_cost' | 'input_tokens' | 'output_tokens' | 'cache_tokens';
export type TokenUsageSortOrder = 'asc' | 'desc';

export interface UsageItem {
  date: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  models_used: string[];
  model_breakdowns: Record<string, any>[];
}

export interface UsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost: number;
  days_count: number;
  avg_daily_cost: number;
}

export interface UsageResponse {
  items: UsageItem[];
  summary: UsageSummary;
  cached?: boolean;
  cache_time?: string;
}

export interface UsageHealthCheck {
  ccusage_installed: boolean;
  opencode_usage_installed: boolean;
  ccusage_opencode_installed: boolean;
}

export interface ModelSummaryItem {
  source: string;
  model: string;
  display_model: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
}

export interface SyncMeta {
  last_synced_at?: string | null;
  last_success_at?: string | null;
  cache_written_at?: string | null;
  cache_ttl_seconds: number;
  cache_expires_at?: string | null;
  data_age_seconds?: number | null;
  is_stale: boolean;
  stale_reason?: string | null;
  refresh_lock: {
    locked: boolean;
    owner?: string | null;
    ttl_seconds: number;
  };
  sources_status: Array<{
    source: string;
    status: string;
    records_count: number;
    synced_at?: string | null;
    error_message?: string | null;
  }>;
}

export interface DeviceInfo {
  id: string;
  name: string;
}

export interface DimensionSummaryItem {
  dimension: 'device' | 'tool' | 'model';
  key: string;
  label: string;
  device_id?: string | null;
  tool_id?: string | null;
  source?: string | null;
  model?: string | null;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  token_share: number;
  cost_share: number;
  records_count: number;
  last_used_at?: string | null;
}

export interface DimensionSummaries {
  devices: DimensionSummaryItem[];
  tools: DimensionSummaryItem[];
  models: DimensionSummaryItem[];
}

export interface ToolFilterOption {
  tool_id: string;
  tool_name: string;
  records_count: number;
}

export interface DeviceFilterOption {
  device_id: string;
  device_name: string;
  records_count: number;
}

export interface ModelFilterOption {
  tool_id: string;
  source: string;
  model: string;
  model_display_name: string;
  records_count: number;
}

export interface FilterOptions {
  tools: ToolFilterOption[];
  devices: DeviceFilterOption[];
  models: ModelFilterOption[];
}

export interface DbQueryParams {
  type: TokenUsageReportType;
  days?: number;
  group_by?: TokenUsageGroupBy;
  source?: TokenUsageSource;
  device_id?: string;
  tool_id?: string;
  model?: string;
  sort_by?: TokenUsageSortBy;
  sort_order?: TokenUsageSortOrder;
}

export interface DbUsageItem extends UsageItem {
  group_key?: string;
}

export interface DbUsageResponse {
  items: DbUsageItem[];
  summary: UsageSummary;
  devices: DeviceInfo[];
  cached?: boolean;
  actual_days?: number;
  auto_expanded?: boolean;
  model_summary: ModelSummaryItem[];
  dimension_summaries: DimensionSummaries;
  filter_options: FilterOptions;
  sync_meta: SyncMeta;
}

export interface ChartSeriesItem {
  date: string;
  group_key?: string | null;
  total_tokens: number;
  total_cost: number;
}

export interface SummaryUsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_creation_tokens: number;
  total_cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  days_count: number;
  avg_daily_cost: number;
}

export interface TokenUsageSummaryResponse {
  summary: SummaryUsageSummary;
  dimension_summaries: DimensionSummaries;
  model_summary: ModelSummaryItem[];
  filter_options: FilterOptions;
  sync_meta: SyncMeta;
  chart_series: ChartSeriesItem[];
  cached?: boolean;
  auto_expanded?: boolean;
  actual_days?: number | null;
  devices: DeviceInfo[];
}

export interface TokenUsageDetailsResponse {
  items: DbUsageItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  cached?: boolean;
}

export interface TokenUsageDetailsParams {
  type?: TokenUsageReportType;
  days?: number;
  group_by?: TokenUsageGroupBy;
  source?: TokenUsageSource;
  device_id?: string;
  tool_id?: string;
  model?: string;
  sort_by?: TokenUsageSortBy;
  sort_order?: TokenUsageSortOrder;
  limit?: number;
  offset?: number;
}

export interface SyncTokenUsageResponse {
  message?: string;
  sources_synced: string[];
  total_records: number;
  errors: string[];
  locked?: boolean;
  lock_ttl_seconds?: number;
}

async function readError(response: Response, fallback: string): Promise<Error> {
  const error = await response.json().catch(() => ({ detail: response.statusText }));
  return new Error(error.detail || fallback);
}

export async function checkTokenUsageHealth(): Promise<UsageHealthCheck> {
  const response = await fetch(`${BASE_URL}/health`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '健康检查失败');
  }
  return response.json();
}

export async function getTokenUsageSummary(params: DbQueryParams): Promise<TokenUsageSummaryResponse> {
  const search = new URLSearchParams();
  search.set('type', params.type);
  search.set('days', String(params.days || 30));
  search.set('group_by', params.group_by || 'none');
  search.set('source', params.source || 'all');
  if (params.device_id) search.set('device_id', params.device_id);
  if (params.tool_id) search.set('tool_id', params.tool_id);
  if (params.model) search.set('model', params.model);

  const response = await fetch(`${BASE_URL}/summary?${search.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '概览加载失败');
  }
  return response.json();
}

export async function getTokenUsageDetails(params: TokenUsageDetailsParams): Promise<TokenUsageDetailsResponse> {
  const response = await fetch(`${BASE_URL}/details`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type: params.type,
      days: params.days || 30,
      group_by: params.group_by || 'none',
      source: params.source || 'all',
      device_id: params.device_id,
      tool_id: params.tool_id,
      model: params.model,
      sort_by: params.sort_by || 'date',
      sort_order: params.sort_order || 'desc',
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    }),
  });
  if (!response.ok) {
    throw await readError(response, '明细加载失败');
  }
  return response.json();
}

export async function getDbTokenUsage(params: DbQueryParams): Promise<DbUsageResponse> {
  const response = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type: params.type,
      days: params.days || 30,
      group_by: params.group_by || 'none',
      source: params.source || 'all',
      device_id: params.device_id,
      tool_id: params.tool_id,
      model: params.model,
      sort_by: params.sort_by || 'date',
      sort_order: params.sort_order || 'desc',
    }),
  });
  if (!response.ok) {
    throw await readError(response, '数据库查询失败');
  }
  return response.json();
}

export async function syncTokenUsage(): Promise<SyncTokenUsageResponse> {
  const response = await fetch(`${BASE_URL}/sync`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw await readError(response, '同步失败');
  }
  return response.json();
}

export async function refreshTokenUsage(params?: {
  days?: number;
  background?: boolean;
  reason?: 'manual' | 'stale';
}): Promise<SyncTokenUsageResponse> {
  const response = await fetch(`${BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      days: params?.days ?? 90,
      background: params?.background ?? false,
      reason: params?.reason ?? 'manual',
    }),
  });
  if (!response.ok) {
    throw await readError(response, '刷新失败');
  }
  return response.json();
}

export async function clearTokenUsageData(): Promise<{
  message: string;
  records_deleted: number;
  sync_logs_deleted: number;
}> {
  const response = await fetch(`${BASE_URL}/clear-data`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw await readError(response, '清理数据失败');
  }
  return response.json();
}

export async function renameDevice(
  deviceId: string,
  name: string
): Promise<{ device_id: string; display_name: string | null }> {
  const response = await fetch(`${BASE_URL}/devices/${deviceId}/rename`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw await readError(response, '重命名设备失败');
  }
  return response.json();
}

export async function getUserDevices(): Promise<{ devices: DeviceInfo[] }> {
  const response = await fetch(`${BASE_URL}/devices`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取设备列表失败');
  }
  return response.json();
}

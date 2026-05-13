import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const BASE_URL = `${API_BASE_URL}/token-usage`;

export type TokenUsageSource = 'claude' | 'opencode' | 'all';
export type TokenUsageReportType = 'daily' | 'weekly' | 'monthly';
export type TokenUsageGroupBy = 'none' | 'device' | 'model';

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

export interface DeviceInfo {
  id: string;
  name: string;
}

export interface DbQueryParams {
  type: TokenUsageReportType;
  days?: number;
  group_by?: TokenUsageGroupBy;
  source?: TokenUsageSource;
  device_id?: string;
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
}

export interface SyncTokenUsageResponse {
  message?: string;
  sources_synced: string[];
  total_records: number;
  errors: string[];
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

export async function refreshTokenUsage(): Promise<SyncTokenUsageResponse> {
  const response = await fetch(`${BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
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

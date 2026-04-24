import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const BASE_URL = `${API_BASE_URL}/token-usage`;

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

export async function getTokenUsage(params: {
  source: 'claude' | 'opencode';
  type: 'daily' | 'weekly' | 'monthly';
  days?: number;
  since?: string;
  until?: string;
  by?: string;
  breakdown?: boolean;
}): Promise<UsageResponse> {
  const response = await fetch(`${BASE_URL}`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source: params.source,
      type: params.type,
      days: params.days || 30,
      since: params.since,
      until: params.until,
      by: params.by,
      breakdown: params.breakdown || false,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || '获取 Token 消耗数据失败');
  }
  return response.json();
}

export async function checkTokenUsageHealth(): Promise<UsageHealthCheck> {
  const response = await fetch(`${BASE_URL}/health`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('健康检查失败');
  }
  return response.json();
}

export async function refreshTokenUsage(): Promise<{ message: string }> {
  const response = await fetch(`${BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error('刷新缓存失败');
  }
  return response.json();
}

import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const REDIS_API_URL = `${API_BASE_URL}/redis-tool`;

export interface RedisConfig {
  id: string;
  alias: string;
  host: string;
  port: number;
  username?: string;
  db: number;
  group_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateRedisRequest {
  alias: string;
  host: string;
  port: number;
  username?: string;
  password?: string;
  db: number;
  group_name?: string;
  is_active?: boolean;
}

export interface UpdateRedisRequest extends Partial<CreateRedisRequest> {}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  elapsed_ms?: number;
  version?: string;
}

export interface RedisKeyInfo {
  key: string;
  type: string;
  ttl: number;
  size?: number;
}

export interface RedisKeyContent {
  key: string;
  type: string;
  ttl: number;
  value: any;
}

export interface KeyOperationRequest {
  key: string;
  type: string;
  value: any;
  ttl?: number;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  } as HeadersInit;
  
  const response = await fetch(url, { ...options, headers });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}

export const getRedisConfigs = () => {
  return request<RedisConfig[]>(`${REDIS_API_URL}/configs`);
};

export const createRedisConfig = (data: CreateRedisRequest) => {
  return request<RedisConfig>(`${REDIS_API_URL}/configs`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const updateRedisConfig = (id: string, data: UpdateRedisRequest) => {
  return request<RedisConfig>(`${REDIS_API_URL}/configs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

export const deleteRedisConfig = (id: string) => {
  return request<{ message: string }>(`${REDIS_API_URL}/configs/${id}`, {
    method: 'DELETE',
  });
};

export const testConnection = (data: any) => {
  return request<ConnectionTestResult>(`${REDIS_API_URL}/configs/test`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const testConnectionById = (id: string) => {
  return request<ConnectionTestResult>(`${REDIS_API_URL}/configs/${id}/test`, {
    method: 'POST',
  });
};

export const getRedisKeys = (id: string, pattern: string = '*') => {
  return request<RedisKeyInfo[]>(`${REDIS_API_URL}/configs/${id}/keys?pattern=${encodeURIComponent(pattern)}`);
};

export const getRedisKeyContent = (id: string, key: string) => {
  return request<RedisKeyContent>(`${REDIS_API_URL}/configs/${id}/keys/${encodeURIComponent(key)}`);
};

export const setRedisKey = (id: string, data: KeyOperationRequest) => {
  return request<{ message: string }>(`${REDIS_API_URL}/configs/${id}/keys`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const deleteRedisKeys = (id: string, keys: string[]) => {
  return request<{ message: string; count: number }>(`${REDIS_API_URL}/configs/${id}/keys`, {
    method: 'DELETE',
    body: JSON.stringify({ keys }),
  });
};

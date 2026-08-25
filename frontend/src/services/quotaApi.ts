/**
 * LLM 配额管理 API 服务
 */
import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE = '/api';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export interface QuotaInfo {
  user_id: string;
  username: string | null;
  quota_mode: string;
  daily_limit: number | null;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number | null;
  monthly_used: number;
  monthly_remaining: number;
  token_period: string | null;
  token_limit: number | null;
  token_used: number;
  token_remaining: number;
  valid_from: string | null;
  valid_until: string | null;
  is_valid: boolean;
  granted_by: string | null;
  notes: string | null;
}

export interface QuotaListResponse {
  items: QuotaInfo[];
  skip: number;
  limit: number;
  count: number;
}

export interface GrantQuotaRequest {
  quota_mode: string;
  daily_limit?: number;
  monthly_limit?: number;
  token_period?: string;
  token_limit?: number;
  valid_from?: string;
  valid_until?: string;
  notes?: string;
}

export interface QuotaStats {
  total_users: number;
  by_mode: Record<string, number>;
  today_total_requests: number;
  month_total_requests: number;
}

export const quotaApi = {
  // 列表用户配额（分页 + 搜索）
  listUsers: async (params?: { search?: string; skip?: number; limit?: number }): Promise<QuotaListResponse> => {
    const response = await axios.get(`${API_BASE}/admin/llm-quota/users`, {
      headers: getAuthHeaders(),
      params,
    });
    return response.data;
  },

  // 查询单用户配额
  getUser: async (userId: string): Promise<QuotaInfo> => {
    const response = await axios.get(`${API_BASE}/admin/llm-quota/users/${userId}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 分配/覆盖配额
  grant: async (userId: string, data: GrantQuotaRequest): Promise<QuotaInfo> => {
    const response = await axios.post(`${API_BASE}/admin/llm-quota/users/${userId}/grant`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 重置计数器
  reset: async (userId: string): Promise<QuotaInfo> => {
    const response = await axios.post(`${API_BASE}/admin/llm-quota/users/${userId}/reset`, {}, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 撤销配额
  revoke: async (userId: string): Promise<void> => {
    await axios.delete(`${API_BASE}/admin/llm-quota/users/${userId}`, {
      headers: getAuthHeaders(),
    });
  },

  // 全局统计
  getStats: async (): Promise<QuotaStats> => {
    const response = await axios.get(`${API_BASE}/admin/llm-quota/stats`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },
};

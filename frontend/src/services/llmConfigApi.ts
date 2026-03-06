import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export type LLMConfigCategory = 'chat' | 'code';

export interface LLMConfig {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  api_key_suffix?: string;
  model_name: string;
  request_params: {
    temperature?: number;
    max_tokens?: number;
    timeout?: number;
  };
  category: LLMConfigCategory;
  notes?: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CreateLLMConfigRequest {
  name: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  model_name: string;
  request_params?: {
    temperature?: number;
    max_tokens?: number;
    timeout?: number;
  };
  category?: LLMConfigCategory;
  notes?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  latency_ms: number;
}

export const llmConfigApi = {
  // 获取所有配置
  getConfigs: async (): Promise<LLMConfig[]> => {
    const response = await axios.get(`${API_BASE_URL}/admin/llm-configs`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 创建配置
  createConfig: async (data: CreateLLMConfigRequest): Promise<LLMConfig> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-configs`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 更新配置
  updateConfig: async (id: string, data: Partial<CreateLLMConfigRequest>): Promise<LLMConfig> => {
    const response = await axios.put(`${API_BASE_URL}/admin/llm-configs/${id}`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 删除配置
  deleteConfig: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/admin/llm-configs/${id}`, {
      headers: getAuthHeaders(),
    });
  },

  // 测试连接
  testConnection: async (id: string): Promise<TestConnectionResponse> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-configs/${id}/test`, {}, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 设置为默认
  setDefault: async (id: string): Promise<void> => {
    await axios.post(`${API_BASE_URL}/admin/llm-configs/${id}/set-default`, {}, {
      headers: getAuthHeaders(),
    });
  },

  // 获取统计信息
  getStats: async (): Promise<{
    total: number;
    active: number;
    by_provider: Record<string, number>;
  }> => {
    const response = await axios.get(`${API_BASE_URL}/admin/llm-stats`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 获取限流配置
  getRateLimits: async (): Promise<{
    normal_user: { hourly_limit: number };
    premium_user: { hourly_limit: number };
  }> => {
    const response = await axios.get(`${API_BASE_URL}/admin/rate-limits`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 更新限流配置
  updateRateLimits: async (limits: {
    normal_user?: { hourly_limit: number };
    premium_user?: { hourly_limit: number };
  }): Promise<void> => {
    await axios.put(`${API_BASE_URL}/admin/rate-limits`, limits, {
      headers: getAuthHeaders(),
    });
  },
};

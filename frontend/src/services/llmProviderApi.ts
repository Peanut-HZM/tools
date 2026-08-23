/**
 * 大模型供应商管理 API 服务层
 * Task 1.5.4 — 对应后端 admin_llm_providers 路由
 */
import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/** 供应商类型 */
export interface LLMProvider {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  api_key_suffix?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

/** 创建供应商请求 */
export interface CreateProviderRequest {
  name: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  notes?: string;
  is_active?: boolean;
}

/** 更新供应商请求 */
export interface UpdateProviderRequest {
  name?: string;
  provider_type?: string;
  base_url?: string;
  api_key?: string;
  notes?: string;
  is_active?: boolean;
}

/** 连通性测试结果 */
export interface TestConnectionResult {
  success: boolean;
  message: string;
  latency_ms: number;
}

/** 揭示 API Key */
export interface RevealResult {
  api_key: string;
}

export const llmProviderApi = {
  /** 获取供应商列表 */
  list: async (activeOnly = false): Promise<LLMProvider[]> => {
    const response = await axios.get(`${API_BASE_URL}/admin/llm-providers`, {
      headers: getAuthHeaders(),
      params: activeOnly ? { active_only: true } : {},
    });
    return response.data;
  },

  /** 获取单个供应商 */
  get: async (id: string): Promise<LLMProvider> => {
    const response = await axios.get(`${API_BASE_URL}/admin/llm-providers/${id}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 新建供应商 */
  create: async (data: CreateProviderRequest): Promise<LLMProvider> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-providers`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 更新供应商 */
  update: async (id: string, data: UpdateProviderRequest): Promise<LLMProvider> => {
    const response = await axios.put(`${API_BASE_URL}/admin/llm-providers/${id}`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 删除供应商 */
  delete: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/admin/llm-providers/${id}`, {
      headers: getAuthHeaders(),
    });
  },

  /** 切换启用/禁用 */
  toggle: async (id: string): Promise<{ id: string; is_active: boolean }> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-providers/${id}/toggle`, {}, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 测试连通性 */
  testConnection: async (id: string): Promise<TestConnectionResult> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-providers/${id}/test`, {}, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 揭示 API Key 明文 */
  reveal: async (id: string): Promise<RevealResult> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-providers/${id}/reveal`, {}, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },
};

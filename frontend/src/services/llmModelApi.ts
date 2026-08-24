/**
 * 大模型模型管理 API 服务层
 * Task 1.5.4 — 对应后端 admin_llm_models 路由
 */
import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/** 模型分类 */
export type ModelCategory =
  | 'text'
  | 'voice'
  | 'vision'
  | 'embedding'
  | 'image_gen'
  | 'ocr';

/** 模型 */
export interface LLMModel {
  id: string;
  name: string;
  model_name: string;
  provider_id: string;
  provider_name?: string;
  request_params?: string;
  category: ModelCategory;
  is_default: boolean;
  is_default_for_category: boolean;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  /** 兜底链优先级，越小越优先 */
  priority: number;
}

/** 创建模型请求 */
export interface CreateModelRequest {
  name: string;
  model_name: string;
  provider_id: string;
  request_params?: string;
  category?: ModelCategory;
  is_default?: boolean;
  is_default_for_category?: boolean;
  notes?: string;
  is_active?: boolean;
  priority?: number;
}

/** 更新模型请求 */
export interface UpdateModelRequest {
  name?: string;
  model_name?: string;
  provider_id?: string;
  request_params?: string;
  category?: ModelCategory;
  is_default?: boolean;
  is_default_for_category?: boolean;
  notes?: string;
  is_active?: boolean;
  priority?: number;
}

export const llmModelApi = {
  /** 获取模型列表 */
  list: async (params?: {
    category?: string;
    provider_id?: string;
    active_only?: boolean;
  }): Promise<LLMModel[]> => {
    const response = await axios.get(`${API_BASE_URL}/admin/llm-models`, {
      headers: getAuthHeaders(),
      params: params || {},
    });
    return response.data;
  },

  /** 获取单个模型 */
  get: async (id: string): Promise<LLMModel> => {
    const response = await axios.get(`${API_BASE_URL}/admin/llm-models/${id}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 新建模型 */
  create: async (data: CreateModelRequest): Promise<LLMModel> => {
    const response = await axios.post(`${API_BASE_URL}/admin/llm-models`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 更新模型 */
  update: async (id: string, data: UpdateModelRequest): Promise<LLMModel> => {
    const response = await axios.put(`${API_BASE_URL}/admin/llm-models/${id}`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /** 删除模型 */
  delete: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/admin/llm-models/${id}`, {
      headers: getAuthHeaders(),
    });
  },

  /** 设为默认（全局或分类） */
  setDefault: async (id: string, category?: string): Promise<void> => {
    await axios.post(
      `${API_BASE_URL}/admin/llm-models/${id}/set-default`,
      { category: category || null },
      { headers: getAuthHeaders() },
    );
  },
};

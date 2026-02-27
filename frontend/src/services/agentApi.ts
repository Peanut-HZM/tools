import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  icon: string;
  icon_color: string;
  category: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AgentCreateRequest {
  name: string;
  description: string;
  system_prompt: string;
  icon?: string;
  icon_color?: string;
  category?: string;
}

export interface AgentUpdateRequest {
  name?: string;
  description?: string;
  system_prompt?: string;
  icon?: string;
  icon_color?: string;
  category?: string;
  is_active?: boolean;
}

export const agentApi = {
  // 获取Agent列表（管理员）
  getAgents: async (params?: { skip?: number; limit?: number; is_active?: boolean }): Promise<Agent[]> => {
    const response = await axios.get(`${API_BASE_URL}/admin/agents`, {
      params,
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 获取Agent详情（管理员）
  getAgent: async (id: string): Promise<Agent> => {
    const response = await axios.get(`${API_BASE_URL}/admin/agents/${id}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 创建Agent（管理员）
  createAgent: async (data: AgentCreateRequest): Promise<Agent> => {
    const response = await axios.post(`${API_BASE_URL}/admin/agents`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 更新Agent（管理员）
  updateAgent: async (id: string, data: AgentUpdateRequest): Promise<Agent> => {
    const response = await axios.put(`${API_BASE_URL}/admin/agents/${id}`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 删除Agent（管理员）
  deleteAgent: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/admin/agents/${id}`, {
      headers: getAuthHeaders(),
    });
  },

  // 设置默认Agent（管理员）
  setDefaultAgent: async (id: string): Promise<Agent> => {
    const response = await axios.post(`${API_BASE_URL}/admin/agents/${id}/default`, {}, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 获取Agent统计（管理员）
  getAgentStats: async (): Promise<{ total: number; active: number; inactive: number }> => {
    const response = await axios.get(`${API_BASE_URL}/admin/agents/stats/overview`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },
};

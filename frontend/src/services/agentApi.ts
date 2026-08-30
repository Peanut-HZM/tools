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
  // --- Phase 1 harness 字段（均为 optional，向后兼容）---
  slug?: string;
  welcome_message?: string;
  default_model_id?: string;
  fallback_model_ids?: string[];
  generation_params?: Record<string, any>;
  memory_short_term_policy?: string;
  memory_short_term_window?: number;
  memory_long_term_enabled?: boolean;
  max_steps_per_turn?: number;
  tool_timeout_seconds?: number;
  error_strategy?: 'stop' | 'retry' | 'skip';
  can_handoff_to?: string[];
  handoff_instruction?: string;
  input_guardrails?: string[];
  output_guardrails?: string[];
  guardrail_on_violation?: 'block' | 'warn';
  visibility?: 'public' | 'private' | 'unlisted';
  capabilities?: string[];
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

export interface AgentHarnessUpdate {
  slug?: string;
  welcome_message?: string;
  default_model_id?: string;
  fallback_model_ids?: string[];
  generation_params?: Record<string, any>;
  memory_short_term_policy?: string;
  memory_short_term_window?: number;
  memory_long_term_enabled?: boolean;
  memory_long_term_config?: Record<string, any>;
  memory_procedural_enabled?: boolean;
  sandbox_enabled?: boolean;
  max_steps_per_turn?: number;
  tool_timeout_seconds?: number;
  error_strategy?: 'stop' | 'retry' | 'skip' | 'fallback_message';
  max_retries?: number;
  can_handoff_to?: string[];
  handoff_instruction?: string;
  input_guardrails?: Record<string, any>[];
  output_guardrails?: Record<string, any>[];
  guardrail_on_violation?: 'block' | 'warn';
  visibility?: 'public' | 'private' | 'unlisted';
  owner_id?: string;
}

export interface AgentHarnessView {
  id: string;
  name: string;
  description: string;
  icon: string;
  icon_color: string;
  category: string;
  is_active: boolean;
  slug?: string;
  welcome_message?: string;
  default_model_id?: string;
  fallback_model_ids?: string[];
  generation_params?: Record<string, any>;
  memory_short_term_policy?: string;
  memory_short_term_window?: number;
  memory_long_term_enabled: boolean;
  memory_long_term_config: Record<string, any>;
  memory_procedural_enabled?: boolean;
  sandbox_enabled?: boolean;
  max_steps_per_turn?: number;
  tool_timeout_seconds?: number;
  error_strategy?: string;
  max_retries?: number;
  can_handoff_to?: string[];
  handoff_instruction?: string;
  input_guardrails?: Record<string, any>[];
  output_guardrails?: Record<string, any>[];
  guardrail_on_violation?: string;
  visibility?: string;
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

  // 获取 Agent harness 扩展字段
  getAgentHarness: async (id: string): Promise<AgentHarnessView> => {
    const response = await axios.get(`${API_BASE_URL}/admin/agents/${id}/harness`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 更新 Agent harness 扩展字段
  updateAgentHarness: async (id: string, data: AgentHarnessUpdate): Promise<AgentHarnessView> => {
    const response = await axios.post(
      `${API_BASE_URL}/admin/agents/${id}/harness`,
      data,
      { headers: getAuthHeaders() },
    );
    return response.data;
  },

  // P2-④: 导出 Agent bundle（JSON）
  exportAgentBundle: async (id: string): Promise<Record<string, unknown>> => {
    const response = await axios.post(
      `${API_BASE_URL}/admin/agents/${id}/export`,
      {},
      { headers: getAuthHeaders() },
    );
    return response.data;
  },

  // P2-④: 导入 Agent bundle
  importAgentBundle: async (
    bundle: Record<string, unknown>,
  ): Promise<{ agent: { id: string; name: string; visibility: string }; warnings: string[] }> => {
    const response = await axios.post(
      `${API_BASE_URL}/admin/agents/import`,
      bundle,
      { headers: getAuthHeaders() },
    );
    return response.data;
  },
};

import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export interface ConversationListItem {
  id: string;
  user_id: string;
  username: string;
  title: string | null;
  current_stage: string;
  message_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  user_id: string;
  username: string;
  email: string;
  title: string | null;
  current_stage: string;
  created_at: string;
  updated_at: string;
  messages: MessageDetail[];
}

export interface MessageDetail {
  id: string;
  sender_type: string;
  content: string;
  sent_at: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  llm_model_name: string | null;
}

export interface ConversationStats {
  total_conversations: number;
  total_messages: number;
  total_tokens: number;
  today_conversations: number;
  today_tokens: number;
  avg_tokens_per_conversation: number;
}

export interface ModelUsageStat {
  model_name: string;
  usage_count: number;
  total_tokens: number;
  percentage: number;
}

export interface UserConversationStat {
  user_id: string;
  username: string;
  email: string;
  conversation_count: number;
  total_tokens: number;
}

export const adminConversationApi = {
  // 获取对话列表
  getConversations: async (params?: {
    skip?: number;
    limit?: number;
    user_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ConversationListItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/admin/conversations/list`, {
      params,
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 获取对话详情
  getConversationDetail: async (conversationId: string): Promise<ConversationDetail> => {
    const response = await axios.get(
      `${API_BASE_URL}/admin/conversations/${conversationId}/detail`,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 获取统计概览
  getStats: async (): Promise<ConversationStats> => {
    const response = await axios.get(
      `${API_BASE_URL}/admin/conversations/stats/overview`,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 获取模型使用统计
  getModelStats: async (): Promise<ModelUsageStat[]> => {
    const response = await axios.get(
      `${API_BASE_URL}/admin/conversations/stats/models`,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 获取用户统计排行
  getUserStats: async (params?: { skip?: number; limit?: number }): Promise<UserConversationStat[]> => {
    const response = await axios.get(
      `${API_BASE_URL}/admin/conversations/stats/users`,
      { params, headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 删除对话
  deleteConversation: async (conversationId: string): Promise<void> => {
    await axios.delete(
      `${API_BASE_URL}/admin/conversations/${conversationId}`,
      { headers: getAuthHeaders() }
    );
  },
};

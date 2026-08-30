import axios from 'axios';
import { getAuthToken } from '../api/authApi';
import { authedFetch } from '../api/http';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// 获取认证头
const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  current_stage: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: 'user' | 'agent';
  content: string;
  message_type: 'text' | 'structured' | 'chart';
  sent_at: string;
}

export interface CreateConversationRequest {
  title?: string;
  initial_message?: string;
}

export interface SendMessageRequest {
  content: string;
  action?: 'chat' | 'analyze_competitor' | 'generate_prd' | 'export';
  llm_config_id?: string;
  agent_id?: string;
}

export interface ChatResponse {
  user_message: Message;
  agent_message: Message;
  stage_changed: boolean;
  new_stage: string | null;
}

export const conversationApi = {
  // 获取会话列表
  getConversations: async (skip = 0, limit = 20): Promise<Conversation[]> => {
    const response = await axios.get(`${API_BASE_URL}/conversations`, {
      params: { skip, limit },
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 创建会话
  createConversation: async (data: CreateConversationRequest): Promise<Conversation> => {
    const response = await axios.post(`${API_BASE_URL}/conversations`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 获取会话详情
  getConversation: async (id: string): Promise<Conversation> => {
    const response = await axios.get(`${API_BASE_URL}/conversations/${id}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 更新会话
  updateConversation: async (
    id: string,
    data: { title?: string; version: number }
  ): Promise<Conversation> => {
    const response = await axios.put(`${API_BASE_URL}/conversations/${id}`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  // 删除会话
  deleteConversation: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/conversations/${id}`, {
      headers: getAuthHeaders(),
    });
  },

  // 获取消息列表
  getMessages: async (
    conversationId: string,
    limit = 50,
    beforeId?: string
  ): Promise<Message[]> => {
    const response = await axios.get(
      `${API_BASE_URL}/conversations/${conversationId}/messages`,
      {
        params: { limit, before_id: beforeId },
        headers: getAuthHeaders(),
      }
    );
    return response.data;
  },

  // 发送消息
  sendMessage: async (
    conversationId: string,
    data: SendMessageRequest
  ): Promise<ChatResponse> => {
    const response = await axios.post(
      `${API_BASE_URL}/conversations/${conversationId}/messages`,
      data,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  // 流式发送消息
  sendMessageStream: (
    conversationId: string,
    data: SendMessageRequest,
    callbacks: {
      onChunk: (chunk: string) => void;
      onDone: (message: Message) => void;
      onError: (error: string) => void;
      /** 可选：透传全部原始 SSE 事件（tool_call_start / tool_result 等，图生页面使用） */
      onEvent?: (event: { type: string; [key: string]: unknown }) => void;
    }
  ) => {
    const token = getAuthToken();
    const url = `${API_BASE_URL}/conversations/${conversationId}/chat/stream`;
    
    authedFetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    }).then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        callbacks.onError(errorData.detail || `HTTP ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError('无法读取响应流');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let agentMessage: Message | null = null;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6));

                switch (event.type) {
                  case 'chunk':
                    callbacks.onChunk(event.content);
                    break;
                  case 'done':
                    agentMessage = event.data;
                    callbacks.onDone(agentMessage);
                    break;
                  case 'error':
                    callbacks.onError(event.message);
                    break;
                  default:
                    // tool_call_start / tool_result 等事件交给 onEvent 消费方
                    if (callbacks.onEvent) callbacks.onEvent(event);
                    break;
                }
              } catch (e) {
                console.error('解析 SSE 数据失败:', e);
              }
            }
          }
        }
      } catch (error) {
        callbacks.onError(error instanceof Error ? error.message : '流读取失败');
      } finally {
        reader.releaseLock();
      }
    }).catch((error) => {
      callbacks.onError(error instanceof Error ? error.message : '请求失败');
    });
  },
};

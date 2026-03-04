import { useState, useCallback, useEffect } from 'react';
import { conversationApi, Conversation, Message, CreateConversationRequest } from '../services/conversationApi';

interface UseConversationOptions {
  autoLoad?: boolean;
}

interface UseConversationReturn {
  // State
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  loading: boolean;
  sending: boolean;
  error: string | null;
  
  // Actions
  loadConversations: () => Promise<void>;
  createConversation: (data: CreateConversationRequest) => Promise<Conversation>;
  selectConversation: (conversationId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<Message>;
  clearError: () => void;
}

export function useConversation(options: UseConversationOptions = {}): UseConversationReturn {
  const { autoLoad = true } = options;
  
  // State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Load conversations on mount
  useEffect(() => {
    if (autoLoad) {
      loadConversations();
    }
  }, [autoLoad]);
  
  // Load messages when conversation changes
  useEffect(() => {
    if (currentConversation) {
      loadMessages(currentConversation.id);
    }
  }, [currentConversation?.id]);
  
  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await conversationApi.getConversations();
      setConversations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载会话列表失败');
    } finally {
      setLoading(false);
    }
  }, []);
  
  const createConversation = useCallback(async (data: CreateConversationRequest): Promise<Conversation> => {
    setLoading(true);
    setError(null);
    try {
      const conversation = await conversationApi.createConversation(data);
      setConversations(prev => [conversation, ...prev]);
      setCurrentConversation(conversation);
      return conversation;
    } catch (err) {
      const message = err instanceof Error ? err.message : '创建会话失败';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  const selectConversation = useCallback(async (conversationId: string) => {
    setLoading(true);
    setError(null);
    try {
      const conversation = await conversationApi.getConversation(conversationId);
      setCurrentConversation(conversation);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载会话失败');
    } finally {
      setLoading(false);
    }
  }, []);
  
  const loadMessages = useCallback(async (conversationId: string) => {
    try {
      const data = await conversationApi.getMessages(conversationId);
      setMessages(data);
    } catch (err) {
      console.error('加载消息失败:', err);
    }
  }, []);
  
  const sendMessage = useCallback(async (content: string): Promise<Message> => {
    if (!currentConversation) {
      throw new Error('请先选择一个会话');
    }
    
    setSending(true);
    setError(null);
    try {
      const response = await conversationApi.sendMessage(currentConversation.id, {
        content,
        action: 'chat',
      });
      
      // Add user message
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        conversation_id: currentConversation.id,
        sender_type: 'user',
        content,
        message_type: 'text',
        sent_at: new Date().toISOString(),
      };
      
      // Add agent message
      const agentMessage: Message = {
        id: response.agent_message?.id || `temp-${Date.now() + 1}`,
        conversation_id: currentConversation.id,
        sender_type: 'agent',
        content: response.agent_message?.content || '',
        message_type: response.agent_message?.message_type || 'text',
        sent_at: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, userMessage, agentMessage]);
      
      return agentMessage;
    } catch (err) {
      const message = err instanceof Error ? err.message : '发送消息失败';
      setError(message);
      throw err;
    } finally {
      setSending(false);
    }
  }, [currentConversation]);
  
  const clearError = useCallback(() => {
    setError(null);
  }, []);
  
  return {
    // State
    conversations,
    currentConversation,
    messages,
    loading,
    sending,
    error,
    // Actions
    loadConversations,
    createConversation,
    selectConversation,
    sendMessage,
    clearError,
  };
}

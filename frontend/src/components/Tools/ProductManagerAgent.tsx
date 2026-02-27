import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { conversationApi, Conversation, Message } from '../../services/conversationApi';
import { llmConfigApi, LLMConfig } from '../../services/llmConfigApi';
import { agentApi, Agent } from '../../services/agentApi';

const ProductManagerAgent: React.FC = () => {
  const navigate = useNavigate();
  const { conversationId } = useParams<{ conversationId?: string }>();
  
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversations();
    loadLLMConfigs();
    loadAgents();
  }, []);

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
      loadMessages(conversationId);
    }
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    try {
      const data = await conversationApi.getConversations();
      setConversations(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      setConversations([]);
    }
  };

  const loadLLMConfigs = async () => {
    try {
      const data = await llmConfigApi.getConfigs();
      setLlmConfigs(data);
      // 默认选中默认配置
      const defaultConfig = data.find((c: LLMConfig) => c.is_default);
      if (defaultConfig) {
        setSelectedConfigId(defaultConfig.id);
      } else if (data.length > 0) {
        setSelectedConfigId(data[0].id);
      }
    } catch (error) {
      console.error('Failed to load LLM configs:', error);
    }
  };

  const loadAgents = async () => {
    try {
      const data = await agentApi.getAgents({ is_active: true });
      setAgents(data);
      // 默认选中默认Agent
      const defaultAgent = data.find((a: Agent) => a.is_default);
      if (defaultAgent) {
        setSelectedAgentId(defaultAgent.id);
      } else if (data.length > 0) {
        setSelectedAgentId(data[0].id);
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  };

  const loadConversation = async (id: string) => {
    try {
      const data = await conversationApi.getConversation(id);
      setCurrentConversation(data);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const loadMessages = async (id: string) => {
    try {
      const data = await conversationApi.getMessages(id);
      // 按时间升序排序，旧消息在前，最新消息在后
      const sortedData = [...data].sort((a, b) => 
        new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime()
      );
      setMessages(sortedData);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const data = await conversationApi.createConversation({
        title: '新会话',
      });
      navigate(`/tools/product-manager/${data.id}`);
      loadConversations();
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyMessage = async (content: string, msgId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !conversationId) return;

    const content = inputMessage.trim();
    setInputMessage('');
    setLoading(true);

    // 先添加用户消息到界面
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId,
      sender_type: 'user',
      content: content,
      message_type: 'text',
      sent_at: new Date().toISOString(),
    };

    // 创建空的 AI 消息占位
    const tempAgentMessage: Message = {
      id: `temp-agent-${Date.now()}`,
      conversation_id: conversationId,
      sender_type: 'agent',
      content: '',
      message_type: 'text',
      sent_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMessage, tempAgentMessage]);

    // 使用流式 API
    conversationApi.sendMessageStream(
      conversationId,
      {
        content: content,
        llm_config_id: selectedConfigId || undefined,
        agent_id: selectedAgentId || undefined,
      },
      {
        onChunk: (chunk) => {
          // 实时更新 AI 消息内容
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === tempAgentMessage.id
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        onDone: (agentMessage) => {
          // 替换临时消息为真实消息
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id === tempUserMessage.id) {
                return { ...msg, id: agentMessage.id + '-user' };
              }
              if (msg.id === tempAgentMessage.id) {
                return agentMessage;
              }
              return msg;
            })
          );
          setLoading(false);
        },
        onError: (error) => {
          console.error('Stream error:', error);
          // 更新 AI 消息显示错误
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === tempAgentMessage.id
                ? { ...msg, content: `抱歉，发生错误: ${error}` }
                : msg
            )
          );
          setLoading(false);
        },
      }
    );
  };

  const getStageLabel = (stage: string) => {
    const labels: Record<string, string> = {
      requirement_clarification: '需求澄清',
      market_research: '市场研究',
      architecture_design: '架构设计',
      detailed_design: '详细设计',
      integration_output: '整合输出',
    };
    return labels[stage] || stage;
  };

  const getProviderLabel = (type: string) => {
    const labels: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      azure_openai: 'Azure OpenAI',
      baidu: '百度文心',
      aliyun: '阿里通义',
      zhipu: '智谱 AI',
      openrouter: 'OpenRouter',
      deepseek: 'DeepSeek',
      moonshot: '月之暗面',
      other: '其他',
    };
    return labels[type] || type;
  };

  return (
    <div className="flex h-[calc(100vh-120px)]">
      {/* 侧边栏 */}
      <div className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <button
            onClick={createNewConversation}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center"
          >
            <i className="fas fa-plus mr-2"></i>
            新建会话
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => navigate(`/tools/product-manager/${conv.id}`)}
              className={`p-4 cursor-pointer border-b border-slate-700 hover:bg-slate-700 ${
                conversationId === conv.id ? 'bg-slate-700' : ''
              }`}
            >
              <div className="text-white font-medium truncate">{conv.title || '新会话'}</div>
              <div className="text-slate-400 text-sm mt-1">{getStageLabel(conv.current_stage)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col bg-slate-900">
        {currentConversation ? (
          <>
            {/* 头部 */}
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <div>
                <h2 className="text-white font-semibold">{currentConversation.title || '新会话'}</h2>
                <span className="text-slate-400 text-sm">{getStageLabel(currentConversation.current_stage)}</span>
              </div>

              {/* Agent选择和模型选择 */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <label className="text-slate-400 text-sm">Agent:</label>
                  <select
                    value={selectedAgentId}
                    onChange={(e) => setSelectedAgentId(e.target.value)}
                    className="px-3 py-1.5 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:outline-none focus:border-blue-500"
                  >
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                        {agent.is_default ? ' [默认]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-slate-400 text-sm">模型:</label>
                  <select
                    value={selectedConfigId}
                    onChange={(e) => setSelectedConfigId(e.target.value)}
                    className="px-3 py-1.5 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:outline-none focus:border-blue-500"
                  >
                    {llmConfigs.map((config) => (
                      <option key={config.id} value={config.id}>
                        {config.name} ({getProviderLabel(config.provider_type)})
                        {config.is_default ? ' [默认]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <button className="px-3 py-1 text-slate-300 hover:text-white">
                  <i className="fas fa-file-export mr-1"></i>
                  导出
                </button>
                <button className="px-3 py-1 text-slate-300 hover:text-white">
                  <i className="fas fa-chart-bar mr-1"></i>
                  分析竞品
                </button>
              </div>
            </div>

            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto p-4">
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-slate-400">
                    <div className="text-4xl mb-4">👋</div>
                    <p className="text-lg mb-2">你好！我是你的产品经经理助手</p>
                    <p>请告诉我你想做什么产品？比如"我想做个记账软件"</p>

                    {llmConfigs.length > 0 && (
                      <div className="mt-6 p-4 bg-slate-800 rounded-lg">
                        <p className="text-sm text-slate-400 mb-2">当前使用模型:</p>
                        <p className="text-blue-400">
                          {llmConfigs.find(c => c.id === selectedConfigId)?.name || '默认模型'}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          可在顶部切换其他已配置模型
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`mb-4 flex ${
                      msg.sender_type === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-[70%] rounded-lg p-4 relative group ${
                        msg.sender_type === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-700 text-white'
                      }`}
                    >
                      {/* 复制按钮 */}
                      <button
                        onClick={() => handleCopyMessage(msg.content, msg.id)}
                        className={`absolute top-2 right-2 p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity ${
                          msg.sender_type === 'user'
                            ? 'hover:bg-blue-500 text-white/80'
                            : 'hover:bg-slate-600 text-slate-400'
                        }`}
                        title="复制消息"
                      >
                        {copiedId === msg.id ? (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        )}
                      </button>
                      
                      <div className="whitespace-pre-wrap pr-8">{msg.content}</div>
                      <div className="text-xs mt-2 opacity-70">
                        {new Date(msg.sent_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入框 */}
            <div className="p-4 border-t border-slate-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="输入你的需求想法..."
                  className="flex-1 px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500"
                  disabled={loading}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={loading || !inputMessage.trim()}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? (
                    <i className="fas fa-spinner fa-spin"></i>
                  ) : (
                    <i className="fas fa-paper-plane"></i>
                  )}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-6xl mb-4">🤖</div>
              <p className="text-xl mb-2">产品经理 Agent</p>
              <p>选择左侧会话或创建新会话开始</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductManagerAgent;

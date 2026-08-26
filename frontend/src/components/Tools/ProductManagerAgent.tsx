import { BarChart3, FileText, FileDown } from 'lucide-react';
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from "@/components/ui/Button";
import { conversationApi, Conversation, Message } from '../../services/conversationApi';
import { llmConfigApi, LLMConfig } from '../../services/llmConfigApi';
import { agentApi, Agent } from '../../services/agentApi';
import Sidebar from '../ProductManagerAgent/Sidebar';
import ChatInterface from '../ProductManagerAgent/ChatInterface';
import PRDPreview from '../ProductManagerAgent/PRDPreview';
import ExportDialog from '../ProductManagerAgent/ExportDialog';

const ProductManagerAgent: React.FC = () => {
  const navigate = useNavigate();
  const { conversationId } = useParams<{ conversationId?: string }>();

  // State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [showPRDPreview, setShowPRDPreview] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showCompetitorAnalysis, setShowCompetitorAnalysis] = useState(false);

  // Load initial data
  useEffect(() => {
    loadConversations();
    loadLLMConfigs();
    loadAgents();
  }, []);

  // Load conversation when ID changes
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
      loadMessages(conversationId);
    }
  }, [conversationId]);

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
      const sortedData = [...data].sort((a, b) =>
        new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime()
      );
      setMessages(sortedData);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleNewConversation = async () => {
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

  const handleSelectConversation = (id: string) => {
    navigate(`/tools/product-manager/${id}`);
  };

  const handleSendMessage = async (content: string) => {
    if (!conversationId) return;

    setLoading(true);

    // Create temp user message
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId,
      sender_type: 'user',
      content: content,
      message_type: 'text',
      sent_at: new Date().toISOString(),
    };

    // Create temp agent message placeholder
    const tempAgentMessage: Message = {
      id: `temp-agent-${Date.now()}`,
      conversation_id: conversationId,
      sender_type: 'agent',
      content: '',
      message_type: 'text',
      sent_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMessage, tempAgentMessage]);

    // Use streaming API
    conversationApi.sendMessageStream(
      conversationId,
      {
        content: content,
        llm_config_id: selectedConfigId || undefined,
        agent_id: selectedAgentId || undefined,
      },
      {
        onChunk: (chunk) => {
          // Update agent message content in real-time
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === tempAgentMessage.id
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        onDone: (agentMessage) => {
          // Replace temp messages with real messages
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
          // Update agent message with error
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === tempAgentMessage.id
                ? { ...msg, content: `抱歉，发生错误：${error}` }
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
      {/* Left Sidebar - Conversation List */}
      <Sidebar
        conversations={conversations}
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        loading={false}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col bg-canvas">
        {currentConversation ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h2 className="text-ink-inverse font-semibold">{currentConversation.title || '新会话'}</h2>
                <span className="text-ink-muted text-sm">{getStageLabel(currentConversation.current_stage)}</span>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-4">
                {/* Agent Selection */}
                <div className="flex items-center gap-2">
                  <label className="text-ink-muted text-sm">Agent:</label>
                  <select
                    value={selectedAgentId}
                    onChange={(e) => setSelectedAgentId(e.target.value)}
                    className="px-3 py-1.5 bg-surface-1 text-ink-inverse text-sm rounded border border-border focus:outline-none focus:border-accent"
                  >
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                        {agent.is_default ? ' [默认]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Model Selection */}
                <div className="flex items-center gap-2">
                  <label className="text-ink-muted text-sm">模型:</label>
                  <select
                    value={selectedConfigId}
                    onChange={(e) => setSelectedConfigId(e.target.value)}
                    className="px-3 py-1.5 bg-surface-1 text-ink-inverse text-sm rounded border border-border focus:outline-none focus:border-accent"
                  >
                    {llmConfigs.map((config) => (
                      <option key={config.id} value={config.id}>
                        {config.name} ({getProviderLabel(config.provider_type)})
                        {config.is_default ? ' [默认]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Action Buttons */}
                <Button
                  onClick={() => setShowPRDPreview(!showPRDPreview)}
                  variant={showPRDPreview ? "default" : "ghost"}
                  size="sm"
                >
                  <FileText className="w-3.5 h-3.5 mr-1" />
                  PRD
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setShowExportDialog(true)}
                  size="sm"
                >
                  <FileDown className="w-3.5 h-3.5 mr-1" />
                  导出
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setShowCompetitorAnalysis(!showCompetitorAnalysis)}
                  size="sm"
                >
                  <BarChart3 className="w-3.5 h-3.5 mr-1" />
                  分析竞品
                </Button>
              </div>
            </div>

            {/* Content Area - Split view for Chat and PRD Preview */}
            <div className="flex-1 flex overflow-hidden">
              {/* Chat Area */}
              <div className={`flex-1 ${showPRDPreview ? 'w-1/2 border-r border-border' : 'w-full'}`}>
                <ChatInterface
                  messages={messages}
                  sending={loading}
                  onSendMessage={handleSendMessage}
                  disabled={!conversationId}
                />
              </div>

              {/* PRD Preview Panel */}
              {showPRDPreview && conversationId && (
                <div className="w-1/2">
                  <PRDPreview
                    conversationId={conversationId}
                    onExport={() => setShowExportDialog(true)}
                  />
                </div>
              )}
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex items-center justify-center h-full text-ink-muted">
            <div className="text-center">
              <div className="text-6xl mb-4">🤖</div>
              <p className="text-xl mb-2">产品经理 Agent</p>
              <p>选择左侧会话或创建新会话开始</p>
            </div>
          </div>
        )}
      </div>

      {/* Export Dialog */}
      {conversationId && (
        <ExportDialog
          isOpen={showExportDialog}
          onClose={() => setShowExportDialog(false)}
          conversationId={conversationId}
        />
      )}
    </div>
  );
};

export default ProductManagerAgent;
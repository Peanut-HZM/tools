import React from 'react';
import { Conversation } from '../../services/conversationApi';

interface SidebarProps {
  conversations: Conversation[];
  currentConversationId?: string;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  loading?: boolean;
}

// Stage display names
const stageNames: Record<string, string> = {
  'requirement_clarification': '需求澄清',
  'market_research': '市场研究',
  'architecture_design': '架构设计',
  'detailed_design': '详细设计',
  'integration_output': '整合输出',
};

// Stage colors
const stageColors: Record<string, string> = {
  'requirement_clarification': 'bg-accent-info/20 text-accent-info',
  'market_research': 'bg-accent-secondary/20 text-accent-secondary',
  'architecture_design': 'bg-warning/20 text-warning',
  'detailed_design': 'bg-success/20 text-success',
  'integration_output': 'bg-surface-2 text-ink',
};

const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  loading = false,
}) => {
  const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    // Less than 1 minute
    if (diff < 60000) return '刚刚';
    
    // Less than 1 hour
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    
    // Less than 24 hours
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    
    // Less than 7 days
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
    
    // Otherwise, show date
    return date.toLocaleDateString();
  };
  
  return (
    <div className="w-72 bg-surface-1 h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-bold text-ink mb-3">对话列表</h2>
        <button
          onClick={onNewConversation}
          disabled={loading}
          className="w-full px-4 py-2 bg-accent text-ink-inverse rounded-lg hover:bg-accent disabled:bg-surface-2 disabled:cursor-not-allowed transition-colors"
        >
          + 新建对话
        </button>
      </div>
      
      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {loading && conversations.length === 0 ? (
          <div className="p-4 text-center text-ink-muted">
            加载中...
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-ink-muted">
            <p>暂无对话</p>
            <p className="text-sm mt-1">点击上方按钮开始新对话</p>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                onClick={() => onSelectConversation(conversation.id)}
                className={`w-full text-left p-3 rounded-lg mb-1 transition-colors ${
                  currentConversationId === conversation.id
                    ? 'bg-accent text-ink-inverse'
                    : 'text-ink-muted hover:bg-surface-2'
                }`}
              >
                <div className="font-medium truncate">
                  {conversation.title || '新对话'}
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    currentConversationId === conversation.id
                      ? 'bg-accent-hover text-ink-inverse'
                      : stageColors[conversation.current_stage] || 'bg-surface-2 text-ink-muted'
                  }`}>
                    {stageNames[conversation.current_stage] || conversation.current_stage}
                  </span>
                  <span className={`text-xs ${
                    currentConversationId === conversation.id
                      ? 'text-accent-info'
                      : 'text-ink-faint'
                  }`}>
                    {formatDate(conversation.updated_at)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;

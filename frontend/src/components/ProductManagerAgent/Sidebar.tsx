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
  'requirement_clarification': 'bg-blue-100 text-blue-800',
  'market_research': 'bg-purple-100 text-purple-800',
  'architecture_design': 'bg-yellow-100 text-yellow-800',
  'detailed_design': 'bg-green-100 text-green-800',
  'integration_output': 'bg-gray-100 text-gray-800',
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
    <div className="w-72 bg-slate-800 h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <h2 className="text-lg font-bold text-white mb-3">对话列表</h2>
        <button
          onClick={onNewConversation}
          disabled={loading}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors"
        >
          + 新建对话
        </button>
      </div>
      
      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {loading && conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            加载中...
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
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
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-slate-700'
                }`}
              >
                <div className="font-medium truncate">
                  {conversation.title || '新对话'}
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    currentConversationId === conversation.id
                      ? 'bg-blue-700 text-blue-100'
                      : stageColors[conversation.current_stage] || 'bg-gray-600 text-gray-300'
                  }`}>
                    {stageNames[conversation.current_stage] || conversation.current_stage}
                  </span>
                  <span className={`text-xs ${
                    currentConversationId === conversation.id
                      ? 'text-blue-200'
                      : 'text-gray-500'
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

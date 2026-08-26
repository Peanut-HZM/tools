import React, { useState, useRef, useEffect } from 'react';
import { Message } from '../../services/conversationApi';
import MessageBubble from './MessageBubble';
import FileUpload from './FileUpload';

interface ChatInterfaceProps {
  messages: Message[];
  sending?: boolean;
  onSendMessage: (content: string) => Promise<void>;
  disabled?: boolean;
  conversationId?: string;
  onFileUploadComplete?: (result: any) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  sending = false,
  onSendMessage,
  disabled = false,
  conversationId,
  onFileUploadComplete,
}) => {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const content = input.trim();
    if (!content || isSending || disabled) return;
    
    setInput('');
    setIsSending(true);
    
    try {
      await onSendMessage(content);
    } catch (error) {
      console.error('发送消息失败:', error);
      // Restore input on error
      setInput(content);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-ink-muted">
            <div className="text-center">
              <p className="text-lg mb-2">👋 开始对话</p>
              <p className="text-sm">输入您的需求，让我帮您生成 PRD</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
            />
          ))
        )}
        
        {sending && (
          <div className="flex items-center justify-center py-2">
            <div className="flex items-center space-x-2 text-ink-muted">
              <div className="animate-bounce">•</div>
              <div className="animate-bounce" style={{ animationDelay: '0.1s' }}>•</div>
              <div className="animate-bounce" style={{ animationDelay: '0.2s' }}>•</div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <div className="border-t border-border p-4 bg-surface-1">
        {/* File Upload Button */}
        {conversationId && (
          <div className="mb-3">
            <FileUpload
              conversationId={conversationId}
              onUploadComplete={onFileUploadComplete}
              disabled={disabled}
            />
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的需求..."
              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent resize-none"
              rows={2}
              disabled={disabled || isSending}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || disabled || isSending}
            className="px-6 py-2 bg-accent text-ink-inverse rounded-lg hover:bg-accent-hover disabled:bg-surface-2 disabled:cursor-not-allowed transition-colors"
          >
            {isSending ? '发送中...' : '发送'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;

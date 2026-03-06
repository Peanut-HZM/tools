/**
 * 消息面板组件
 */
import React, { useState, useEffect, useRef } from 'react';
import { messageApi, Message } from '../../../services/crossShare';
import ReactMarkdown from 'react-markdown';
import { useToast } from '../../../hooks/useToast';

const MessagePanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast, showToast } = useToast();

  useEffect(() => {
    loadMessages();
    // 轮询新消息（每 5 秒）
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadMessages = async () => {
    try {
      setLoadError(null);
      const data = await messageApi.getMessages(100, 0);
      setMessages(data.reverse()); // 最新消息在最后
    } catch (error: any) {
      console.error('Failed to load messages:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      setLoadError(errorMsg);
      showToast('加载消息失败：' + errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return;

    setSending(true);
    try {
      await messageApi.sendMessage(inputValue.trim(), 'text');
      setInputValue('');
      loadMessages();
      showToast('消息发送成功', 'success');
    } catch (error: any) {
      console.error('Failed to send message:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      showToast('发送失败：' + errorMsg, 'error');
      // 保留输入内容，不清空 inputValue，让用户可以重试
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePaste = async (e: React.ClipboardEvent) => {
    // 同步剪贴板
    const text = e.clipboardData.getData('text');
    if (text) {
      try {
        await messageApi.syncClipboard(text);
        showToast('剪贴板已同步', 'success');
      } catch (error: any) {
        console.error('Failed to sync clipboard:', error);
        showToast('同步剪贴板失败：' + (error.response?.data?.detail || error.message), 'error');
      }
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'text':
        return '💬';
      case 'file':
        return '📎';
      case 'link':
        return '🔗';
      case 'clipboard':
        return '📋';
      case 'image':
        return '🖼️';
      default:
        return '💬';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-white/60">加载中...</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 overflow-hidden p-8">
          <div className="text-center">
            <div className="text-6xl mb-4">⚠️</div>
            <div className="text-white text-xl font-semibold mb-2">加载消息失败</div>
            <div className="text-white/60 mb-6">{loadError}</div>
            <button
              onClick={loadMessages}
              className="px-6 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-semibold rounded-xl transition-colors"
            >
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 overflow-hidden">
        {/* Messages List */}
        <div className="h-[60vh] overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-white/40 py-16">
              <div className="text-6xl mb-4">📭</div>
              <div>暂无消息</div>
              <div className="text-sm mt-2">发送一条消息开始跨设备同步</div>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <div
                  key={msg.id}
                  className={`flex items-start space-x-3 ${
                    msg.message_type === 'clipboard' ? 'opacity-70' : ''
                  }`}
                >
                  <div className="text-2xl">{getMessageIcon(msg.message_type)}</div>
                  <div className="flex-1 bg-white/5 rounded-xl p-4">
                    {msg.message_type === 'text' || msg.message_type === 'clipboard' ? (
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown>{msg.content || ''}</ReactMarkdown>
                      </div>
                    ) : msg.message_type === 'file' ? (
                      <div className="text-white">📎 文件消息</div>
                    ) : msg.message_type === 'link' ? (
                      <div className="text-white">🔗 {msg.content}</div>
                    ) : null}
                    <div className="text-xs text-white/40 mt-2">
                      {new Date(msg.created_at).toLocaleString('zh-CN')}
                      {msg.message_type === 'clipboard' && ' • 剪贴板'}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-white/10 p-4">
          <div className="flex items-end space-x-3">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              onPaste={handlePaste}
              placeholder="输入消息... (支持 Markdown，Ctrl+V 同步剪贴板)"
              className="flex-1 bg-white/5 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:border-yellow-500 resize-none"
              rows={2}
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || sending}
              className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-colors"
            >
              {sending ? '发送中...' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessagePanel;

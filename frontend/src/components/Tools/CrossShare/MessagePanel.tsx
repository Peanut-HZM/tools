/**
 * 消息面板组件
 */
import React, { useState, useEffect, useRef } from 'react';
import { messageApi, Message } from '../../../services/crossShare';
import ReactMarkdown from 'react-markdown';
import { useToast } from '../../../hooks/useToast';
import JsonViewer from './JsonViewer';
import CodeViewer from './CodeViewer';
import CopyDropdown from './CopyDropdown';
import { detectContentType, countLines } from './utils/contentDetector';

const MessagePanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true); // 追踪用户是否在底部
  const [hasNewMessage, setHasNewMessage] = useState(false); // 是否有新消息（当用户不在底部时）
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const { toast, showToast } = useToast();

  // 检查用户是否在底部
  const checkIsAtBottom = () => {
    const container = messagesContainerRef.current;
    if (!container) return true;

    const threshold = 50; // 距离底部 50px 以内都算在底部
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;

    return scrollHeight - scrollTop - clientHeight < threshold;
  };

  // 监听滚动事件
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      setIsAtBottom(checkIsAtBottom());
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    loadMessages();
    // 轮询新消息（每 5 秒）
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, []);

  // 只有当用户在底部时才自动滚动
  useEffect(() => {
    if (isAtBottom) {
      scrollToBottom();
      setHasNewMessage(false);
    } else {
      // 用户不在底部，标记有新消息
      setHasNewMessage(true);
    }
  }, [messages]);

  const loadMessages = async () => {
    try {
      setLoadError(null);
      const data = await messageApi.getMessages(100, 0);
      // 去重：根据消息 id 去重
      const uniqueMessages = Array.from(
        new Map(data.map(msg => [msg.id, msg])).values()
      );
      setMessages(uniqueMessages.reverse()); // 最新消息在最后
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

  // 手动滚动到底部按钮
  const handleScrollToBottom = () => {
    scrollToBottom();
    setHasNewMessage(false);
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

  const handleDelete = async (messageId: string) => {
    if (!confirm('确定要删除这条消息吗？')) return;

    setDeletingId(messageId);
    try {
      await messageApi.deleteMessage(messageId);
      showToast('消息已删除', 'success');
      loadMessages();
    } catch (error: any) {
      console.error('Failed to delete message:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      showToast('删除失败：' + errorMsg, 'error');
    } finally {
      setDeletingId(null);
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

  // 渲染消息内容
  const renderMessageContent = (msg: Message) => {
    const content = msg.content || '';
    const contentType = detectContentType(content);

    // JSON 类型
    if (contentType === 'json') {
      return <JsonViewer content={content} />;
    }

    // 代码块类型
    if (contentType === 'code') {
      return <CodeViewer content={content} />;
    }

    // Markdown 或普通文本
    return (
      <div className="relative">
        <div className="absolute right-0 top-0 opacity-0 hover:opacity-100 transition-opacity z-10">
          <CopyDropdown
            content={content}
            onCopySuccess={() => showToast('已复制到剪贴板', 'success')}
          />
        </div>
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800 rounded-xl shadow-md border border-slate-700">
        <div className="text-slate-400">加载中...</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800 rounded-xl shadow-md border border-slate-700">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <div className="text-slate-100 text-xl font-semibold mb-2">加载消息失败</div>
          <div className="text-slate-400 mb-6">{loadError}</div>
          <button
            onClick={loadMessages}
            className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-slate-800 rounded-xl shadow-md border border-slate-700 overflow-hidden">
      {/* Messages List - 使用 flex-1 填充剩余空间，内部滚动 */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-6 space-y-4 relative">
        {messages.length === 0 ? (
          <div className="text-center text-slate-500 py-16">
            <div className="text-6xl mb-4">📭</div>
            <div className="text-slate-300">暂无消息</div>
            <div className="text-sm mt-2 text-slate-500">发送一条消息开始跨设备同步</div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 group ${
                msg.message_type === 'clipboard' ? 'opacity-70' : ''
              }`}
            >
              <div className="text-2xl">{getMessageIcon(msg.message_type)}</div>
              <div className="flex-1 bg-slate-700/50 rounded-lg p-4 border border-slate-600 relative">
                {renderMessageContent(msg)}
                <div className="text-xs text-slate-500 mt-2 flex items-center justify-between">
                  <span>
                    {new Date(msg.created_at).toLocaleString('zh-CN')}
                    {msg.message_type === 'clipboard' && ' • 剪贴板'}
                  </span>
                  <button
                    onClick={() => handleDelete(msg.id)}
                    disabled={deletingId === msg.id}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-red-400 hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="删除消息"
                  >
                    {deletingId === msg.id ? '删除中...' : '🗑️ 删除'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />

        {/* 滚动到底部按钮 - 当用户不在底部时显示 */}
        {!isAtBottom && (
          <button
            onClick={handleScrollToBottom}
            className="absolute bottom-4 right-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg shadow-lg transition-all duration-300 flex items-center space-x-2"
          >
            <span>滚动到底部</span>
            {hasNewMessage && (
              <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                新
              </span>
            )}
          </button>
        )}
      </div>

      {/* Input Area - 固定在底部 */}
      <div className="flex-shrink-0 border-t border-slate-700 p-4">
        <div className="flex items-end space-x-3">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            onPaste={handlePaste}
            placeholder="输入消息... (支持 Markdown，Ctrl+V 同步剪贴板)"
            className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || sending}
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
          >
            {sending ? '发送中...' : '发送'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MessagePanel;

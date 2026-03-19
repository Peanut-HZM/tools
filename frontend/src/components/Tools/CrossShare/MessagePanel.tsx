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
import { detectContentType, countLines, isUrl } from './utils/contentDetector';

const COLLAPSE_HEIGHT = 200; // 折叠高度阈值（px）

const MessagePanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [hasUserScrolled, setHasUserScrolled] = useState(false); // 用户是否曾经手动向上滚动
  const [showScrollButton, setShowScrollButton] = useState(false); // 是否显示滚动按钮
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set()); // 记录已展开的消息 ID
  const [collapsibleMessages, setCollapsibleMessages] = useState<Set<string>>(new Set()); // 记录需要折叠的消息 ID
  const [pasteContent, setPasteContent] = useState<string | null>(null); // 待粘贴的内容
  const [showPasteConfirm, setShowPasteConfirm] = useState(false); // 是否显示粘贴确认对话框
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isInitialLoad = useRef(true); // 是否是首次加载
  const contentRefs = useRef<Map<string, HTMLDivElement>>(new Map()); // 存储消息内容 ref
  const { toast, showToast } = useToast();

  // 检查用户是否在底部
  const checkIsAtBottom = () => {
    const container = messagesContainerRef.current;
    if (!container) return true;

    const threshold = 100; // 距离底部 100px 以内都算在底部
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
      const atBottom = checkIsAtBottom();
      if (!atBottom) {
        setHasUserScrolled(true);
        setShowScrollButton(true);
      } else {
        setShowScrollButton(false);
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // 检查消息内容高度，确定是否需要折叠
  useEffect(() => {
    const checkContentHeight = () => {
      const newCollapsible = new Set<string>();
      contentRefs.current.forEach((contentEl, messageId) => {
        if (contentEl.scrollHeight > COLLAPSE_HEIGHT) {
          newCollapsible.add(messageId);
        }
      });
      setCollapsibleMessages(newCollapsible);
    };

    // 延迟检查，确保 DOM 已渲染
    const timer = setTimeout(checkContentHeight, 100);
    return () => clearTimeout(timer);
  }, [messages]);

  useEffect(() => {
    loadMessages();
    // 轮询新消息（每 5 秒）
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, []);

  // 只在首次加载或用户已经在底部时才自动滚动
  useEffect(() => {
    if (isInitialLoad.current) {
      // 首次加载完成后，延迟滚动确保 DOM 已渲染
      setTimeout(() => {
        scrollToBottom();
        isInitialLoad.current = false;
      }, 100);
    } else if (!hasUserScrolled) {
      // 如果用户从未手动滚动过，保持自动滚动
      setTimeout(() => {
        if (checkIsAtBottom()) {
          scrollToBottom();
        }
      }, 50);
    }
    // 如果用户已经手动滚动过，不再自动滚动
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
    setHasUserScrolled(false); // 重置标志，允许后续自动滚动
    setShowScrollButton(false);
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
    if (!text) return;

    // 阻止默认粘贴行为，由我们手动控制
    e.preventDefault();

    // 检测是否是 URL
    if (isUrl(text)) {
      // 弹出确认对话框
      setPasteContent(text);
      setShowPasteConfirm(true);
      return;
    }

    // 纯文本/代码/Markdown 直接插入到光标位置
    const textarea = e.target as HTMLTextAreaElement;
    const startPos = textarea.selectionStart;
    const endPos = textarea.selectionEnd;
    const newValue = inputValue.slice(0, startPos) + text + inputValue.slice(endPos);
    setInputValue(newValue);

    // 恢复光标位置
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = startPos + text.length;
      textarea.focus();
    }, 0);
  };

  // 确认发送粘贴的 URL
  const handlePasteConfirm = async (send: boolean) => {
    setShowPasteConfirm(false);
    if (!pasteContent) return;

    if (send) {
      // 用户确认发送
      setSending(true);
      try {
        await messageApi.sendMessage(pasteContent.trim(), 'text');
        showToast('消息发送成功', 'success');
        loadMessages();
      } catch (error: any) {
        console.error('Failed to send message:', error);
        const errorMsg = error.response?.data?.detail || error.message || '未知错误';
        showToast('发送失败：' + errorMsg, 'error');
      } finally {
        setSending(false);
      }
    } else {
      // 用户取消，将内容插入输入框
      const textarea = document.querySelector('textarea');
      if (textarea) {
        const startPos = textarea.selectionStart || 0;
        const newValue = inputValue.slice(0, startPos) + pasteContent + inputValue.slice(startPos);
        setInputValue(newValue);
      }
    }
    setPasteContent(null);
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

  // 切换消息展开/折叠状态
  const toggleExpand = (messageId: string) => {
    setExpandedMessages(prev => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  // 渲染消息内容
  const renderMessageContent = (msg: Message) => {
    const content = msg.content || '';
    const contentType = detectContentType(content);
    const isExpanded = expandedMessages.has(msg.id);
    const needsCollapse = collapsibleMessages.has(msg.id);

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
        <div className="absolute right-0 top-0 z-10">
          <CopyDropdown
            content={content}
            messageId={msg.id}
            onDelete={handleDelete}
            onCopySuccess={() => showToast('已复制到剪贴板', 'success')}
          />
        </div>
        <div
          ref={(el) => {
            if (el) {
              contentRefs.current.set(msg.id, el);
            }
          }}
          className={`prose prose-invert prose-sm max-w-none transition-all duration-300 ${
            !isExpanded && needsCollapse ? 'overflow-hidden' : ''
          }`}
          style={
            !isExpanded && needsCollapse
              ? { maxHeight: `${COLLAPSE_HEIGHT}px` }
              : undefined
          }
        >
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
        {/* 渐变遮罩和展开/折叠按钮 */}
        {!isExpanded && needsCollapse && (
          <div className="absolute bottom-0 left-0 right-0 h-24 flex items-end justify-center pb-4 bg-gradient-to-t from-slate-700/90 to-transparent pointer-events-none">
            <button
              onClick={() => toggleExpand(msg.id)}
              className="pointer-events-auto px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold rounded-lg shadow-lg transition-colors flex items-center space-x-2"
            >
              <span>展开</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        )}
        {/* 折叠按钮 - 当消息已展开时显示 */}
        {isExpanded && needsCollapse && (
          <div className="flex justify-end mt-2">
            <button
              onClick={() => toggleExpand(msg.id)}
              className="px-3 py-1 bg-slate-600 hover:bg-slate-500 text-white text-xs rounded transition-colors flex items-center space-x-1"
            >
              <span>折叠</span>
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </button>
          </div>
        )}
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
                <div className="text-xs text-slate-500 mt-2">
                  <span>
                    {new Date(msg.created_at).toLocaleString('zh-CN')}
                    {msg.message_type === 'clipboard' && ' • 剪贴板'}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />

        {/* 滚动到底部按钮 - 当用户手动向上滚动后显示 */}
        {showScrollButton && (
          <button
            onClick={handleScrollToBottom}
            className="absolute bottom-4 right-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg shadow-lg transition-all duration-300 flex items-center space-x-2"
          >
            <i className="fas fa-arrow-down"></i>
            <span>滚动到底部</span>
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

      {/* 粘贴 URL 确认对话框 */}
      {showPasteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 max-w-md mx-4 shadow-2xl">
            <div className="text-lg font-semibold text-white mb-2">检测到链接</div>
            <div className="text-slate-400 text-sm mb-4 break-all bg-slate-900 p-3 rounded-lg max-h-32 overflow-y-auto">
              {pasteContent}
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => handlePasteConfirm(false)}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                插入输入框
              </button>
              <button
                onClick={() => handlePasteConfirm(true)}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
              >
                立即发送
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessagePanel;

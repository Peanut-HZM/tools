import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../../../stores/authStore';
import { useLoginModalStore } from '../../../stores/loginModalStore';
import {
  chatStream,
  loadHistory,
  abortChat,
  resetSession,
  getStatus,
} from '../../../api/openclawApi';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

export default function OpenClawChat() {
  const { isAuthenticated } = useAuth();
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionKey] = useState('main');
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 检查连接状态
  const checkConnection = useCallback(async () => {
    try {
      const status = await getStatus();
      setIsConnected(status.connected === true);
      if (status.disabled) {
        setError('OpenClaw 功能已禁用，请联系管理员');
      }
    } catch {
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 从 OpenClaw 消息内容数组中提取用户可见文本
  // 过滤 thinking、系统提示、时间戳等非内容文本
  const extractText = (content: unknown): string => {
    const cleanText = (raw: string): string | null => {
      let text = raw.trim();
      if (!text) return null;
      // 过滤 thinking 内容
      if (text.startsWith('[思考]')) return null;
      // 去掉 bootstrap 提示：找到第一个时间戳，去掉它之前的所有内容
      if (text.startsWith('[Bootstrap')) {
        const tsPattern = /\[[A-Z][a-z]{2}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT[+-]\d+\]/;
        const match = text.match(tsPattern);
        if (match && match.index !== undefined) {
          text = text.slice(match.index + match[0].length).trim();
        } else {
          return null; // 没有时间戳，整条都是 bootstrap
        }
      }
      // 过滤时间戳前缀如 [Sat 2026-04-25 13:53 GMT+8]
      const tsPattern = /^\[[A-Z][a-z]{2}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT[+-]\d+\]\s*/;
      text = text.replace(tsPattern, '');
      return text || null;
    };

    if (typeof content === 'string') {
      return cleanText(content) || '';
    }
    if (content === null || content === undefined) return '';
    // content 可能是对象如 {type: 'text', text: '...'}
    if (typeof content === 'object' && !Array.isArray(content)) {
      const c = content as Record<string, unknown>;
      if (c.type === 'thinking') return '';
      if (typeof c.text === 'string') {
        return cleanText(c.text) || '';
      }
      return '';
    }
    if (!Array.isArray(content)) return '';
    const parts: string[] = [];
    for (const item of content) {
      if (typeof item !== 'object' || item === null) continue;
      const c = item as Record<string, unknown>;
      // 跳过 thinking 类型，其他类型只要有 text 字段就提取
      if (c.type === 'thinking') continue;
      if (typeof c.text !== 'string') continue;
      const cleaned = cleanText(c.text);
      if (cleaned) parts.push(cleaned);
    }
    return parts.join('\n');
  };

  // 加载历史消息
  const loadMessages = useCallback(async () => {
    try {
      const history = await loadHistory(sessionKey);
      console.log('[OpenClaw] history loaded:', history.length, 'messages');
      const formatted: Message[] = [];
      for (const [idx, msg] of history.entries()) {
        // 跳过工具结果消息，避免页面杂乱
        if (msg.role === 'toolResult') continue;
        const text = extractText(msg.content);
        if (!text) continue;
        formatted.push({
          id: `hist-${idx}`,
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: text,
          timestamp: msg.timestamp || Date.now(),
        });
      }
      setMessages(formatted);
    } catch (err) {
      console.error('[OpenClaw] load history error:', err);
    }
  }, [sessionKey]);

  useEffect(() => {
    if (!isAuthenticated) return;
    checkConnection();
    loadMessages();
  }, [checkConnection, loadMessages, isAuthenticated]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || isSending || !isConnected) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsSending(true);
    setError(null);

    // 添加用户消息
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: Date.now(),
    };

    // 添加助理消息占位
    const assistantMsgId = `assistant-${Date.now()}`;
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    await chatStream(
      userMessage,
      sessionKey,
      // onChunk
      (chunk) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, content: chunk }
              : msg
          )
        );
      },
      // onDone
      () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, isStreaming: false }
              : msg
          )
        );
        setIsSending(false);
      },
      // onError
      (err) => {
        setError(err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, content: msg.content || `请求失败：${err}`, isStreaming: false }
              : msg
          )
        );
        setIsSending(false);
      }
    );
  };

  const handleAbort = async () => {
    try {
      await abortChat(sessionKey);
      setIsSending(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isStreaming ? { ...msg, isStreaming: false, content: msg.content + '\n\n[已中止]' } : msg
        )
      );
    } catch {
      // 忽略中止错误
    }
  };

  const handleReset = async () => {
    try {
      await resetSession(sessionKey);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || '重置错误');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 未登录提示
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)]">
        <div className="text-center text-slate-400">
          <div className="text-6xl mb-4">
            <i className="fas fa-comments text-violet-500"></i>
          </div>
          <p className="text-xl mb-4 text-white">OpenClaw AI 对话</p>
          <p className="mb-4">需要登录后才能使用此功能</p>
          <button
            onClick={openLoginModal}
            className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
          >
            登录
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-slate-900 rounded-xl border border-slate-700/50 overflow-hidden">
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(100, 116, 139, 0.4);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background-color: rgba(100, 116, 139, 0.6);
        }
      `}</style>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center">
            <i className="fas fa-comments text-white"></i>
          </div>
          <div>
            <h2 className="text-white font-semibold">OpenClaw AI 对话</h2>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2 text-sm">
                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                <span className="text-slate-400">{isConnected ? '已连接' : '未连接'}</span>
              </div>
              {!isConnected && (
                <span className="text-xs text-amber-400/80">服务未连接，请前往管理面板配置 OpenClaw 连接信息</span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={handleReset}
          className="px-3 py-1.5 text-sm text-slate-400 hover:text-white border border-slate-600 rounded-lg hover:border-slate-500 transition-colors"
        >
          <i className="fas fa-rotate mr-1"></i>
          新对话
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="px-6 py-2 bg-red-500/10 border-b border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <i className="fas fa-times"></i>
          </button>
        </div>
      )}

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto px-6 py-4 space-y-4 custom-scrollbar"
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(100, 116, 139, 0.4) transparent',
        }}
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <div className="text-5xl mb-3">
                <i className="fas fa-comments text-violet-500/50"></i>
              </div>
              <p className="text-lg">发送一条消息开始对话</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className="max-w-[80%]">
                <div
                  className={`rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-violet-600 text-white rounded-br-md'
                      : 'bg-slate-800 text-slate-200 rounded-bl-md'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content || (msg.isStreaming ? 'Thinking...' : '')}</p>
                  {msg.isStreaming && (
                    <span className="inline-block w-1.5 h-4 bg-violet-400 animate-pulse ml-1"></span>
                  )}
                </div>
                <div className={`text-xs text-slate-500 mt-1 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-slate-700/50 bg-slate-800/30">
        <div className="flex gap-3">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Shift+Enter 换行，Enter 发送)"
            disabled={!isConnected || isSending}
            className="flex-1 bg-slate-800 text-white placeholder-slate-500 border border-slate-600 rounded-xl px-4 py-3 resize-none focus:outline-none focus:border-violet-500 disabled:opacity-50"
            rows={1}
          />
          {isSending ? (
            <button
              onClick={handleAbort}
              className="px-4 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors self-end"
            >
              <i className="fas fa-stop"></i>
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || !isConnected}
              className="px-4 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed self-end"
            >
              <i className="fas fa-paper-plane"></i>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

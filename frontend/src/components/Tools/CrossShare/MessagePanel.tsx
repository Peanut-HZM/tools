/**
 * 消息面板组件
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { messageApi, Message } from '../../../services/crossShare';
import ReactMarkdown from 'react-markdown';
import { useToast } from '../../../hooks/useToast';
import JsonViewer from './JsonViewer';
import CodeViewer from './CodeViewer';
import MessageActions from './MessageActions';
import HighlightText from './HighlightText';
import { detectContentType, countLines, isUrl } from './utils/contentDetector';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

const COLLAPSE_HEIGHT = 200; // 折叠高度阈值（px）

const MessagePanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false); // 是否显示滚动到底部按钮
  const [showScrollTopButton, setShowScrollTopButton] = useState(false); // 是否显示滚动到顶部按钮
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set()); // 记录已展开的消息 ID
  const [collapsibleMessages, setCollapsibleMessages] = useState<Set<string>>(new Set()); // 记录需要折叠的消息 ID
  const [pasteContent, setPasteContent] = useState<string | null>(null); // 待粘贴的内容
  const [showPasteConfirm, setShowPasteConfirm] = useState(false); // 是否显示粘贴确认对话框
  const [searchTerm, setSearchTerm] = useState(''); // 搜索关键词
  const [pollingStopped, setPollingStopped] = useState(false); // 轮询是否已停止（认证失败时）
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isInitialLoad = useRef(true); // 是否是首次加载
  const contentRefs = useRef<Map<string, HTMLDivElement>>(new Map()); // 存储消息内容 ref
  const intervalRef = useRef<NodeJS.Timeout | null>(null); // 轮询定时器 ID
  const lastErrorRef = useRef<string | null>(null); // 上一次错误信息（用于去重）
  const consecutiveErrorsRef = useRef(0); // 连续错误计数
  const hasShownFirstErrorRef = useRef(false); // 是否已显示过首次错误
  const { toast, showToast } = useToast();

  // 检查用户是否在底部
  const checkIsAtBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;

    const threshold = 100; // 距离底部 100px 以内都算在底部
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;

    return scrollHeight - scrollTop - clientHeight < threshold;
  }, []);

  // 监听滚动事件
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const atBottom = checkIsAtBottom();
      setShowScrollButton(!atBottom);
      setShowScrollTopButton(container.scrollTop > 300);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    // 初始化时检测一次滚动状态
    handleScroll();
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

  // 使用 useCallback 包裹 loadMessages，避免闭包陈旧问题
  const loadMessages = useCallback(async (isPolling: boolean = false) => {
    try {
      // 仅在首次加载时清除错误状态，轮询时保持当前错误状态避免闪烁
      if (!isPolling) {
        setLoadError(null);
      }
      const data = await messageApi.getMessages(100, 0);
      // 去重：根据消息 id 去重
      const uniqueMessages = Array.from(
        new Map(data.map(msg => [msg.id, msg])).values()
      );
      setMessages(uniqueMessages.reverse()); // 最新消息在最后

      // 成功时重置错误计数
      consecutiveErrorsRef.current = 0;
      lastErrorRef.current = null;
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      const httpStatus = error.response?.status;

      // 认证失败（401/403）熔断：停止轮询，提示用户重新登录
      if (httpStatus === 401 || httpStatus === 403) {
        if (intervalRef.current) {
          // 轮询已改为 setTimeout 链式调度，必须用 clearTimeout 清理
          // （用 clearInterval 清 setTimeout 的句柄在部分实现下不生效，会漏定时器）
          clearTimeout(intervalRef.current);
          intervalRef.current = null;
        }
        setPollingStopped(true);
        // 仅在首次认证失败时提示一次
        if (!hasShownFirstErrorRef.current) {
          showToast('登录已过期，请重新登录', 'warning');
          hasShownFirstErrorRef.current = true;
        }
        console.error('认证失败，已停止轮询:', errorMsg);
        setLoadError('登录已过期，请重新登录');
        return;
      }

      // 非认证失败的错误处理（带退避和去重）
      consecutiveErrorsRef.current += 1;

      // 区分「服务不可用」类错误（网络/超时/5xx）与「业务错误」。
      //
      // 服务不可用时（后端连不上数据库等），原来的去重策略是
      // 「首次 + 每连续失败 6 次弹一次」，但轮询在后台标签页会被浏览器
      // 节流到 1 分钟/次，于是用户在页签里会看到 3 个几乎同时弹出的
      // 500 报错弹窗——既刷屏又无法操作。
      //
      // 改进：这类错误**只提示一次**（错误信息变化时再提示一次，
      // 便于感知恢复或换了个错误），避免刷屏。
      const isServiceUnavailable =
        httpStatus >= 500 ||
        httpStatus === 429 ||
        error.code === 'ECONNABORTED' ||
        error.code === 'ETIMEDOUT' ||
        /timeout|network|failed to fetch|网络|连接/i.test(errorMsg);

      // 错误去重策略：
      // 1. 首次失败时显示 toast
      // 2. 错误信息变化时显示 toast（服务恢复后再次失败能感知到）
      // 3. 服务不可用类错误：不重复提示（避免刷屏）
      // 4. 其余业务错误：每连续失败 6 次提醒一次，避免完全静默
      //
      // 注意：规则 4 与规则 1/2 是**或**关系而非被「错误信息未变」整体挡住。
      // 原实现把 `lastErrorRef.current !== errorMsg` 放在最外层，导致
      // 「同一错误信息连续失败时每 6 次提醒一次」永远不触发（死代码），
      // 服务持续异常期间会彻底静默。
      const isSameError = lastErrorRef.current === errorMsg;
      const shouldShowToast =
        // 错误信息变化 → 重新提示（能感知服务恢复或换了个错误）
        (!isSameError && consecutiveErrorsRef.current > 0) ||
        // 首次失败
        (consecutiveErrorsRef.current === 1 && !hasShownFirstErrorRef.current) ||
        // 业务错误：每连续失败 6 次提醒一次（服务不可用时不重复，避免刷屏）
        (!isServiceUnavailable && consecutiveErrorsRef.current % 6 === 0);

      if (shouldShowToast) {
        showToast(
          isServiceUnavailable
            ? '服务暂时不可用，已停止重复提示：' + errorMsg
            : '加载消息失败：' + errorMsg,
          'error'
        );
        hasShownFirstErrorRef.current = true;
      }

      lastErrorRef.current = errorMsg;

      // 仅在首次加载失败时设置 loadError（避免轮询时整屏 UI 闪烁）
      if (!isPolling) {
        setLoadError(errorMsg);
      }

      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  // 轮询逻辑：首次加载 + 定时轮询
  //
  // 用 setTimeout 链式调度（而非 setInterval），以便在服务不可用时
  // 动态拉长间隔做退避，避免持续高频重试打爆后端。
  useEffect(() => {
    // React StrictMode 兼容：使用 cleanup 标记避免双重调用
    let isMounted = true;

    // 正常轮询间隔 5 秒；连续失败时按指数退避放大（5s → 10s → 20s → 60s 封顶）
    const BASE_POLL_MS = 5000;
    const MAX_POLL_MS = 60000;

    const scheduleNext = (delay: number) => {
      if (!isMounted || pollingStopped) return;
      intervalRef.current = setTimeout(() => {
        if (!isMounted || pollingStopped) return;
        void loadMessages(true).finally(() => {
          const errors = consecutiveErrorsRef.current;
          const nextDelay =
            errors === 0
              ? BASE_POLL_MS
              : Math.min(MAX_POLL_MS, BASE_POLL_MS * Math.pow(2, Math.min(errors - 1, 4)));
          scheduleNext(nextDelay);
        });
      }, delay);
    };

    // 首次加载
    void loadMessages(false).finally(() => {
      scheduleNext(BASE_POLL_MS);
    });

    // 清理函数
    return () => {
      isMounted = false;
      if (intervalRef.current) {
        clearTimeout(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [loadMessages, pollingStopped]);

  // 自动滚动到底部：仅初次加载时执行一次，使用 instant 方式
  useEffect(() => {
    if (!isInitialLoad.current) {
      return;
    }

    // 首次加载：使用 requestAnimationFrame + 多次尝试确保 DOM 渲染完成
    const scrollToBottomOnReady = () => {
      const container = messagesContainerRef.current;
      if (!container) {
        requestAnimationFrame(scrollToBottomOnReady);
        return;
      }

      // 如果内容高度还不够，继续等待
      if (container.scrollHeight === 0 || container.scrollHeight <= container.clientHeight) {
        setTimeout(scrollToBottomOnReady, 50);
        return;
      }

      // 使用双重 requestAnimationFrame 确保布局已完全更新
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (container && messagesContainerRef.current) {
            container.scrollTop = container.scrollHeight;
          }
          isInitialLoad.current = false;
        });
      });
    };

    requestAnimationFrame(scrollToBottomOnReady);
    // 仅在组件挂载时滚动一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 手动滚动到底部按钮
  const handleScrollToBottom = () => {
    scrollToBottom();
    setShowScrollButton(false);
  };

  // 手动滚动到顶部按钮
  const handleScrollToTop = () => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({ top: 0, behavior: 'smooth' });
    }
    setShowScrollTopButton(false);
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

  // 搜索过滤消息
  const filteredMessages = searchTerm.trim()
    ? messages.filter(msg => {
        const term = searchTerm.toLowerCase();
        const contentMatch = msg.content?.toLowerCase().includes(term);
        const typeMatch = msg.message_type?.toLowerCase().includes(term);
        const timeMatch = new Date(msg.created_at).toLocaleString('zh-CN').includes(term);
        return contentMatch || typeMatch || timeMatch;
      })
    : messages;

  // 渲染消息内容
  const renderMessageContent = (msg: Message) => {
    const content = msg.content || '';
    const contentType = detectContentType(content);
    const isExpanded = expandedMessages.has(msg.id);
    const needsCollapse = collapsibleMessages.has(msg.id);

    // JSON 类型
    if (contentType === 'json') {
      return (
        <JsonViewer
          content={content}
          messageId={msg.id}
          onDelete={handleDelete}
          onCopySuccess={() => showToast('已复制到剪贴板', 'success')}
        />
      );
    }

    // 代码块类型
    if (contentType === 'code') {
      return (
        <CodeViewer
          content={content}
          messageId={msg.id}
          onDelete={handleDelete}
          onCopySuccess={() => showToast('已复制到剪贴板', 'success')}
        />
      );
    }

    // Markdown 或普通文本
    return (
      <div className="relative">
        {/* 操作按钮 - 右对齐独立成行（不再绝对定位覆盖正文，
            窄屏下按钮与首行文字重叠、长文本被遮挡的问题） */}
        <div className="z-10 mb-2 flex flex-wrap justify-end gap-1.5">
          <MessageActions
            content={content}
            messageId={msg.id}
            onDelete={handleDelete}
            onCopySuccess={() => showToast('已复制到剪贴板', 'success')}
            isExpanded={isExpanded}
            needsCollapse={needsCollapse}
            onToggleExpand={() => toggleExpand(msg.id)}
          />
        </div>
        <div
          ref={(el) => {
            if (el) {
              contentRefs.current.set(msg.id, el);
            }
          }}
          className={`prose prose-sm dark:prose-invert max-w-none transition-all duration-300 break-words [overflow-wrap:anywhere] ${
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
        {/* 渐变遮罩 - 仅当消息折叠时显示 */}
        {!isExpanded && needsCollapse && (
          <div className="absolute bottom-0 left-0 right-0 h-24 flex items-end justify-center pb-4 bg-gradient-to-t from-surface-2/90 to-transparent pointer-events-none">
            <Button
              variant="default"
              onClick={() => toggleExpand(msg.id)}
              className="pointer-events-auto shadow-lg flex items-center space-x-2"
            >
              <span>展开</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </Button>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <Card className="w-full h-full flex items-center justify-center shadow-md">
        <div className="text-ink-muted">加载中...</div>
      </Card>
    );
  }

  if (loadError) {
    return (
      <Card className="w-full h-full flex items-center justify-center shadow-md">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <div className="text-ink text-xl font-semibold mb-2">加载消息失败</div>
          <div className="text-ink-muted mb-6">{loadError}</div>
          <Button
            variant="default"
            onClick={() => {
              // 手动重试：恢复轮询（认证失败时熔断会置 pollingStopped），
              // 否则重试虽能拉到数据但轮询不再恢复
              setPollingStopped(false);
              hasShownFirstErrorRef.current = false;
              consecutiveErrorsRef.current = 0;
              lastErrorRef.current = null;
              void loadMessages(false);
            }}
            className="px-6 py-2 font-semibold"
          >
            重试
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="w-full h-full flex flex-col shadow-md overflow-hidden">
      {/* 搜索栏 */}
      <div className="flex-shrink-0 px-6 pt-4 pb-2 border-b border-border/50">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <Input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索消息..."
            className="w-full pl-10 pr-24 py-2.5 bg-surface-2/50 placeholder-ink-faint text-sm focus-visible:border-accent-info"
          />
          {searchTerm && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center space-x-2">
              <span className="text-xs text-ink-faint">
                {filteredMessages.length} / {messages.length}
              </span>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => setSearchTerm('')}
                className="w-6 h-6 text-ink-muted hover:text-ink"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Messages List - 使用 flex-1 填充剩余空间，内部滚动 */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4">
          {filteredMessages.length === 0 ? (
            <div className="text-center text-ink-faint py-16">
              <div className="text-6xl mb-4">🔍</div>
              <div className="text-ink-muted">{searchTerm ? '未找到匹配的消息' : '暂无消息'}</div>
              <div className="text-sm mt-2 text-ink-faint">
                {searchTerm ? '尝试其他关键词' : '发送一条消息开始跨设备同步'}
              </div>
            </div>
          ) : (
            filteredMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-start space-x-3 group min-w-0 ${
                  msg.message_type === 'clipboard' ? 'opacity-70' : ''
                }`}
              >
                <div className="text-2xl">{getMessageIcon(msg.message_type)}</div>
                {/* min-w-0：flex 子项默认 min-width:auto，长 URL / API Key 等
                    不可断行的长串会把气泡撑破容器，导致窄屏下横向溢出。 */}
                <div className="flex-1 min-w-0 bg-surface-2/50 rounded-lg p-4 border border-border relative">
                  {renderMessageContent(msg)}
                  <div className="text-xs text-ink-faint mt-2">
                    <span>
                      {searchTerm ? (
                        <HighlightText
                          text={new Date(msg.created_at).toLocaleString('zh-CN')}
                          highlight={searchTerm}
                        />
                      ) : (
                        new Date(msg.created_at).toLocaleString('zh-CN')
                      )}
                      {msg.message_type === 'clipboard' && ' • 剪贴板'}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 浮动滚动按钮 - 放在滚动容器外面，使用绝对定位固定在右下角 */}
        {(showScrollButton || showScrollTopButton) && (
          <div className="absolute bottom-20 right-6 flex flex-col-reverse gap-2 z-50">
            {/* 滚动到底部 */}
            {showScrollButton && (
              <Button
                size="sm"
                variant="default"
                onClick={handleScrollToBottom}
                className="shadow-lg flex items-center gap-2"
                title="滚动到底部"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
                <span>底部</span>
              </Button>
            )}
            {/* 滚动到顶部 */}
            {showScrollTopButton && (
              <Button
                size="sm"
                variant="secondary"
                onClick={handleScrollToTop}
                className="shadow-lg flex items-center gap-2"
                title="滚动到顶部"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
                <span>顶部</span>
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Input Area - 固定在底部 */}
      <div className="flex-shrink-0 border-t border-border p-3 sm:p-4">
        {/* 窄屏（< sm）改为上下堆叠：横向排布会把输入框压到几十像素，
            placeholder 溢出且发送按钮点不到。 */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            onPaste={handlePaste}
            placeholder="输入消息... (支持 Markdown，Ctrl+V 同步剪贴板)"
            className="w-full sm:flex-1 sm:min-w-0 bg-surface-2/50 border border-border rounded-lg px-3 sm:px-4 py-3 text-ink placeholder-ink-faint focus:outline-none focus:border-accent-info resize-none"
            rows={2}
          />
          <Button
            variant="default"
            onClick={handleSend}
            disabled={!inputValue.trim() || sending}
            className="w-full sm:w-auto px-6 py-3 font-semibold disabled:bg-surface-3 disabled:text-ink-muted disabled:cursor-not-allowed h-auto shrink-0"
          >
            {sending ? '发送中...' : '发送'}
          </Button>
        </div>
      </div>

      {/* 粘贴 URL 确认对话框 */}
      {showPasteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="p-6 max-w-md mx-4 shadow-lg">
            <div className="text-lg font-semibold text-ink mb-2">检测到链接</div>
            <div className="text-ink-muted text-sm mb-4 break-all bg-canvas p-3 rounded-lg max-h-32 overflow-y-auto">
              {pasteContent}
            </div>
            <div className="flex justify-end space-x-3">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handlePasteConfirm(false)}
              >
                插入输入框
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={() => handlePasteConfirm(true)}
              >
                立即发送
              </Button>
            </div>
          </Card>
        </div>
      )}
    </Card>
  );
};

export default MessagePanel;

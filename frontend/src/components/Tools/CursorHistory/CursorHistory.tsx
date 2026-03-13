/**
 * Cursor 对话历史查看器 - 主组件
 * 作者：huazm
 * 描述：三栏布局的 Cursor AI 对话历史浏览和搜索工具
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { List } from 'react-window';
import { AutoSizer } from 'react-virtualized-auto-sizer';
import { API_BASE_URL } from '../../../config/api';
import { useToast } from '../../../hooks/useToast';
import { cacheSessionMessages, getCachedSessionMessages } from '../../../utils/cursorCache';
import { addRecentSession, getRecentSessions, formatVisitedTime, type RecentSession } from '../../../utils/recentSessions';
import TagManager from './TagManager';
import TagFilter from './TagFilter';
import BatchActions from './BatchActions';

// ==================== 类型定义 ====================

/** 项目信息 */
interface CursorProject {
  workspace_hash: string;
  project_name: string;
  project_path: string | null;
  session_count: number;
}

/** 会话信息 */
interface CursorSession {
  composer_id: string;
  name: string | null;
  created_at: number | null;
  message_count: number;
  workspace_hash: string | null;
}

/** 消息信息 */
interface CursorMessage {
  message_id: string;
  message_type: number;
  text: string;
  code_blocks: Record<string, unknown>[];
  /** 消息创建时间戳（毫秒） */
  timestamp: number | null;
  /** AI 思考/推理内容 */
  thinking: string | null;
  /** 工具调用信息 */
  tool_call: { toolName: string; status: string; responseText: string } | null;
  /** 能力类型：null=普通, 30=思考, 15=工具调用 */
  capability_type: number | null;
}

/** 搜索结果项 */
interface SearchResultItem {
  project_name: string;
  workspace_hash: string;
  composer_id: string;
  session_name: string | null;
  matched_text: string;
  message_type: number;
}

// ==================== 主组件 ====================

export default function CursorHistory() {
  const navigate = useNavigate();
  const { success: showSuccess, error: showError } = useToast();

  // 数据状态
  const [projects, setProjects] = useState<CursorProject[]>([]);
  const [sessions, setSessions] = useState<CursorSession[]>([]);
  const [messages, setMessages] = useState<CursorMessage[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);

  // 选中状态
  const [selectedProject, setSelectedProject] = useState<CursorProject | null>(null);
  const [selectedSession, setSelectedSession] = useState<CursorSession | null>(null);

  // UI 状态
  const [loading, setLoading] = useState({ projects: false, sessions: false, messages: false, search: false });
  const [projectSearch, setProjectSearch] = useState('');
  const [sessionSearch, setSessionSearch] = useState('');
  const [globalSearch, setGlobalSearch] = useState('');
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 新增状态：侧边栏折叠、自定义路径、路径设置面板
  const [showProjectPanel, setShowProjectPanel] = useState(true);
  const [customBasePath, setCustomBasePath] = useState('');
  const [showPathSettings, setShowPathSettings] = useState(false);
  const [pathInput, setPathInput] = useState('');
  const [pathValid, setPathValid] = useState<boolean | null>(null);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [totalMessages, setTotalMessages] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);

  // 虚拟滚动状态
  const [virtualListHeight, setVirtualListHeight] = useState(0);
  const virtualListRef = useRef<List>(null);

  // 导出功能状态
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportFormat, setExportFormat] = useState<'markdown' | 'json' | 'html'>('markdown');
  const [exportLoading, setExportLoading] = useState(false);
  const [exportOptions, setExportOptions] = useState({
    includeCodeBlocks: true,
    includeTimestamps: true,
    includeAvatars: false,
  });

  // 最近访问状态
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);
  const [showRecentPanel, setShowRecentPanel] = useState(false);

  // 收藏功能状态
  const [isFavorite, setIsFavorite] = useState(false);
  const [showFavoritesPanel, setShowFavoritesPanel] = useState(false);

  // 统计面板状态
  const [showStatsPanel, setShowStatsPanel] = useState(false);

  // 标签筛选状态
  const [selectedFilterTag, setSelectedFilterTag] = useState<string | null>(null);

  // 批量操作状态
  const [selectedSessionIds, setSelectedSessionIds] = useState<string[]>([]);
  const [selectMode, setSelectMode] = useState(false);

  // ==================== 数据加载 ====================

  /** 构建带 base_path 的查询参数 */
  const appendBasePath = useCallback((params: URLSearchParams) => {
    if (customBasePath) params.set('base_path', customBasePath);
  }, [customBasePath]);

  /** 加载项目列表 */
  const loadProjects = useCallback(async (search?: string) => {
    setLoading(prev => ({ ...prev, projects: true }));
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      appendBasePath(params);
      const res = await fetch(`${API_BASE_URL}/cursor-history/projects?${params}`);
      if (!res.ok) throw new Error('加载项目列表失败');
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, projects: false }));
    }
  }, [appendBasePath]);

  /** 加载会话列表 */
  const loadSessions = useCallback(async (workspaceHash: string, search?: string) => {
    setLoading(prev => ({ ...prev, sessions: true }));
    try {
      const params = new URLSearchParams({ workspace_hash: workspaceHash });
      if (search) params.set('search', search);
      appendBasePath(params);
      const res = await fetch(`${API_BASE_URL}/cursor-history/sessions?${params}`);
      if (!res.ok) throw new Error('加载会话列表失败');
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, sessions: false }));
    }
  }, [appendBasePath]);

  /** 加载消息列表（首次加载，重置分页） */
  const loadMessages = useCallback(async (composerId: string, sessionName?: string) => {
    setLoading(prev => ({ ...prev, messages: true }));
    setCurrentPage(1);

    // 尝试从缓存加载
    const cachedMessages = await getCachedSessionMessages(composerId);
    if (cachedMessages) {
      setMessages(cachedMessages);
      setLoading(prev => ({ ...prev, messages: false }));
      return;
    }

    try {
      const params = new URLSearchParams({ composer_id: composerId, page: '1', page_size: '50' });
      if (sessionName) params.set('session_name', sessionName);
      appendBasePath(params);
      const res = await fetch(`${API_BASE_URL}/cursor-history/messages?${params}`);
      if (!res.ok) throw new Error('加载消息失败');
      const data = await res.json();
      setMessages(data.messages || []);
      setTotalMessages(data.total || 0);
      setHasMore(data.has_more || false);

      // 存入缓存
      if (data.messages && data.messages.length > 0) {
        await cacheSessionMessages(composerId, data.messages, selectedProject?.project_name, sessionName);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, messages: false }));
    }
  }, [appendBasePath, selectedProject]);

  /** 加载更多消息（下一页，累积追加） */
  const loadMoreMessages = useCallback(async () => {
    if (!selectedSession || loadingMore || !hasMore) return;
    const nextPage = currentPage + 1;
    setLoadingMore(true);
    try {
      const params = new URLSearchParams({
        composer_id: selectedSession.composer_id,
        page: String(nextPage),
        page_size: '50',
      });
      appendBasePath(params);
      const res = await fetch(`${API_BASE_URL}/cursor-history/messages?${params}`);
      if (!res.ok) throw new Error('加载更多消息失败');
      const data = await res.json();
      // 累积模式：后端返回前 nextPage*50 条，直接替换
      setMessages(data.messages || []);
      setCurrentPage(nextPage);
      setHasMore(data.has_more || false);
      setTotalMessages(data.total || 0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }, [selectedSession, loadingMore, hasMore, currentPage, appendBasePath]);

  /** 全局搜索 */
  const doGlobalSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setIsSearchMode(false);
      setSearchResults([]);
      return;
    }
    setLoading(prev => ({ ...prev, search: true }));
    setIsSearchMode(true);
    try {
      const params = new URLSearchParams({ query, limit: '50' });
      appendBasePath(params);
      const res = await fetch(`${API_BASE_URL}/cursor-history/search?${params}`);
      if (!res.ok) throw new Error('搜索失败');
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, search: false }));
    }
  }, [appendBasePath]);

  /** 验证自定义路径 */
  const validatePath = useCallback(async (path: string) => {
    try {
      const params = new URLSearchParams({ path });
      const res = await fetch(`${API_BASE_URL}/cursor-history/basePath?${params}`);
      if (!res.ok) return;
      const data = await res.json();
      setPathValid(data.valid);
    } catch {
      setPathValid(false);
    }
  }, []);

  /** 应用自定义路径 */
  const applyCustomPath = useCallback(() => {
    if (pathInput.trim()) {
      setCustomBasePath(pathInput.trim());
    } else {
      setCustomBasePath('');
    }
    setShowPathSettings(false);
    // 重新加载项目列表会自动触发
  }, [pathInput]);

  /** 复制消息内容 */
  const handleCopyMessage = useCallback(async (msg: CursorMessage, copyType: 'text' | 'markdown' = 'text') => {
    try {
      let textToCopy = msg.text;

      // 如果是 Markdown 模式，保留原始格式
      if (copyType === 'markdown' && msg.message_type === 0) {
        textToCopy = msg.text;
      }

      await navigator.clipboard.writeText(textToCopy);
      showSuccess('复制成功');
    } catch (err) {
      showError('复制失败');
      console.error('Failed to copy:', err);
    }
  }, [showSuccess, showError]);

  /** 复制代码块 */
  const handleCopyCodeBlock = useCallback(async (code: string) => {
    try {
      const codeText = typeof code === 'object' ? JSON.stringify(code, null, 2) : String(code);
      await navigator.clipboard.writeText(codeText);
      showSuccess('代码已复制');
    } catch (err) {
      showError('复制失败');
      console.error('Failed to copy code:', err);
    }
  }, [showSuccess, showError]);

  /** 导出会话数据 */
  const handleExport = useCallback(async () => {
    if (!selectedSession) return;

    setExportLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          composer_id: selectedSession.composer_id,
          session_name: selectedSession.name || undefined,
          format: exportFormat,
          include_code_blocks: exportOptions.includeCodeBlocks,
          include_timestamps: exportOptions.includeTimestamps,
          include_avatars: exportOptions.includeAvatars,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '导出失败');
      }

      const result = await response.json();

      // 创建下载
      const blob = new Blob([result.data], {
        type: exportFormat === 'json' ? 'application/json' : exportFormat === 'html' ? 'text/html' : 'text/markdown',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      showSuccess(`导出成功：${result.filename}`);
      setShowExportDialog(false);
    } catch (err) {
      showError(err instanceof Error ? err.message : '导出失败');
      console.error('Export failed:', err);
    } finally {
      setExportLoading(false);
    }
  }, [selectedSession, exportFormat, exportOptions, showSuccess, showError]);

  /** 检查收藏状态 */
  const checkFavoriteStatus = useCallback(async (composerId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/cursor-history/favorites/check/${composerId}`);
      if (!res.ok) return;
      const data = await res.json();
      setIsFavorite(data.is_favorite || false);
    } catch (error) {
      console.error('检查收藏状态失败:', error);
    }
  }, []);

  /** 添加/取消收藏 */
  const handleToggleFavorite = useCallback(async () => {
    if (!selectedSession || !selectedProject) return;

    try {
      if (isFavorite) {
        // 取消收藏
        const res = await fetch(`${API_BASE_URL}/cursor-history/favorites/${selectedSession.composer_id}`, {
          method: 'DELETE',
        });
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || '取消收藏失败');
        }
        setIsFavorite(false);
        showSuccess('已取消收藏');
      } else {
        // 添加收藏
        const response = await fetch(`${API_BASE_URL}/cursor-history/favorites`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            composer_id: selectedSession.composer_id,
            session_name: selectedSession.name || undefined,
            project_name: selectedProject.project_name,
            workspace_hash: selectedProject.workspace_hash,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || '收藏失败');
        }

        setIsFavorite(true);
        showSuccess('收藏成功');
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : '操作失败');
      console.error('Toggle favorite failed:', err);
    }
  }, [selectedSession, selectedProject, isFavorite, showSuccess, showError]);

  /** 思考块折叠状态 */
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set());

  /** 切换思考块展开/折叠 */
  const toggleThinking = useCallback((msgId: string) => {
    setExpandedThinking(prev => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  }, []);

  /** 格式化消息时间戳 */
  const formatMessageTime = useCallback((ts: number | null) => {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      });
    } catch { return ''; }
  }, []);

  /** 虚拟滚动：消息项渲染器 */
  const MessageRow = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const msg = messages[index];
    if (!msg) return null;

    const isThinking = msg.capability_type === 30;
    const isToolCall = msg.capability_type === 15;
    const isUser = msg.message_type === 1;

    // 思考块渲染
    if (isThinking) {
      const isExpanded = expandedThinking.has(msg.message_id);
      const thinkingText = msg.thinking || msg.text || '';
      return (
        <div style={style} className="flex justify-start group">
          <div className="max-w-[80%] rounded-2xl px-5 py-3 bg-amber-500/5 border border-amber-500/15">
            <div
              className="flex items-center gap-2 cursor-pointer select-none"
              onClick={() => toggleThinking(msg.message_id)}
            >
              <i className="fas fa-brain text-amber-400/70 text-xs" />
              <span className="text-xs font-medium text-amber-400/80">AI 思考过程</span>
              {msg.timestamp && (
                <span className="text-[10px] text-slate-600 ml-1">{formatMessageTime(msg.timestamp)}</span>
              )}
              <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-amber-400/50 text-[10px] ml-auto`} />
            </div>
            {isExpanded && thinkingText && (
              <div className="mt-2 text-xs text-slate-400 whitespace-pre-wrap break-words leading-relaxed max-h-[300px] overflow-y-auto italic">
                {thinkingText}
              </div>
            )}
          </div>
        </div>
      );
    }

    // 工具调用渲染
    if (isToolCall && msg.tool_call) {
      const statusIcon = msg.tool_call.status === 'completed' ? 'fa-check-circle text-emerald-400' :
                         msg.tool_call.status === 'running' ? 'fa-spinner fa-spin text-blue-400' :
                         msg.tool_call.status === 'error' ? 'fa-times-circle text-red-400' :
                         'fa-wrench text-slate-400';
      return (
        <div style={style} className="flex justify-start group">
          <div className="max-w-[80%] rounded-xl px-4 py-2.5 bg-cyan-500/5 border border-cyan-500/15">
            <div className="flex items-center gap-2">
              <i className={`fas ${statusIcon} text-xs`} />
              <span className="text-xs font-medium text-cyan-400/80">
                {msg.tool_call.toolName || '工具调用'}
              </span>
              {msg.tool_call.status && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  msg.tool_call.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                  msg.tool_call.status === 'error' ? 'bg-red-500/10 text-red-400' :
                  'bg-slate-700/50 text-slate-400'
                }`}>
                  {msg.tool_call.status === 'completed' ? '完成' : msg.tool_call.status === 'error' ? '失败' : msg.tool_call.status}
                </span>
              )}
              {msg.timestamp && (
                <span className="text-[10px] text-slate-600 ml-1">{formatMessageTime(msg.timestamp)}</span>
              )}
            </div>
            {msg.text && (
              <div className="mt-1.5 text-xs text-slate-500 whitespace-pre-wrap break-words line-clamp-3">
                {msg.text}
              </div>
            )}
          </div>
        </div>
      );
    }

    // 普通消息渲染
    return (
      <div style={style} className={`flex group ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
          isUser
            ? 'bg-violet-500/20 border border-violet-500/20'
            : 'bg-slate-800/60 border border-slate-700/30'
        }`}>
          {/* 消息头：角色 + 时间 + 复制按钮 */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <i className={`fas ${isUser ? 'fa-user text-violet-400' : 'fa-robot text-emerald-400'} text-xs`} />
              <span className={`text-xs font-medium ${isUser ? 'text-violet-400' : 'text-emerald-400'}`}>
                {isUser ? '用户' : 'AI 助手'}
              </span>
              {msg.timestamp && (
                <span className="text-[10px] text-slate-600">{formatMessageTime(msg.timestamp)}</span>
              )}
            </div>
            {/* 复制按钮组（hover 显示） */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => handleCopyMessage(msg, 'text')}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition-all"
                title="复制纯文本"
              >
                <i className="fas fa-copy text-xs" />
              </button>
              {!isUser && (
                <button
                  onClick={() => handleCopyMessage(msg, 'markdown')}
                  className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition-all"
                  title="复制 Markdown"
                >
                  <i className="fas fa-file-code text-xs" />
                </button>
              )}
            </div>
          </div>
          {/* 消息内容 */}
          {isUser ? (
            <div className="text-sm text-slate-200 whitespace-pre-wrap break-words leading-relaxed">
              {msg.text}
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none text-slate-200 break-words
              prose-headings:text-white prose-headings:font-semibold
              prose-p:text-slate-300 prose-p:leading-relaxed prose-p:my-2
              prose-strong:text-white prose-em:text-cyan-300
              prose-code:text-emerald-300 prose-code:bg-slate-900/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-slate-900/80 prose-pre:border prose-pre:border-slate-700/40 prose-pre:rounded-lg prose-pre:my-3
              prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline
              prose-li:text-slate-300 prose-li:my-0.5
              prose-blockquote:border-l-violet-500 prose-blockquote:text-slate-400
              prose-table:text-sm prose-th:text-slate-300 prose-td:text-slate-400
              prose-hr:border-slate-700
            ">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {msg.text}
              </ReactMarkdown>
            </div>
          )}
          {/* 代码块 */}
          {msg.code_blocks.length > 0 && (
            <div className="mt-3 space-y-2">
              {msg.code_blocks.map((block, bi) => {
                const codeText = typeof block === 'object' ? JSON.stringify(block, null, 2) : String(block);
                return (
                  <div key={bi} className="group/code relative">
                    <pre className="bg-slate-900/80 border border-slate-700/40 rounded-lg p-3 pr-12 text-xs text-slate-300 overflow-x-auto">
                      <code>{codeText}</code>
                    </pre>
                    <button
                      onClick={() => handleCopyCodeBlock(codeText)}
                      className="absolute top-2 right-2 p-1.5 bg-slate-800/80 hover:bg-slate-700 border border-slate-600/50 rounded text-slate-400 hover:text-white opacity-0 group-hover/code:opacity-100 transition-all"
                      title="复制代码"
                    >
                      <i className="fas fa-copy text-xs" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }, [messages, handleCopyMessage, handleCopyCodeBlock, expandedThinking, toggleThinking, formatMessageTime]);

  // 初始加载项目
  useEffect(() => { loadProjects(); }, [loadProjects]);

  // 加载最近访问记录
  useEffect(() => {
    setRecentSessions(getRecentSessions());
  }, []);

  // 项目搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => loadProjects(projectSearch), 300);
    return () => clearTimeout(timer);
  }, [projectSearch, loadProjects]);

  // 会话搜索防抖
  useEffect(() => {
    if (!selectedProject) return;
    const timer = setTimeout(() => loadSessions(selectedProject.workspace_hash, sessionSearch), 300);
    return () => clearTimeout(timer);
  }, [sessionSearch, selectedProject, loadSessions]);

  // 路径输入防抖验证
  useEffect(() => {
    if (!pathInput.trim()) { setPathValid(null); return; }
    const timer = setTimeout(() => validatePath(pathInput.trim()), 500);
    return () => clearTimeout(timer);
  }, [pathInput, validatePath]);

  // 消息列表滚动加载更多
  useEffect(() => {
    const container = messageListRef.current;
    if (!container) return;
    const handleScroll = () => {
      // 距离底部 200px 时触发加载
      const { scrollTop, scrollHeight, clientHeight } = container;
      if (scrollHeight - scrollTop - clientHeight < 200 && hasMore && !loadingMore) {
        loadMoreMessages();
      }
    };
    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [hasMore, loadingMore, loadMoreMessages]);

  // ==================== 事件处理 ====================

  /** 选中项目 */
  const handleProjectClick = (project: CursorProject) => {
    setSelectedProject(project);
    setSelectedSession(null);
    setMessages([]);
    setCurrentPage(1);
    setHasMore(false);
    setTotalMessages(0);
    setSessionSearch('');
    loadSessions(project.workspace_hash);
  };

  /** 选中会话 */
  const handleSessionClick = (session: CursorSession) => {
    // 如果是选择模式，只切换选中状态
    if (selectMode) {
      toggleSessionSelect(session.composer_id);
      return;
    }

    setSelectedSession(session);
    loadMessages(session.composer_id, session.name || undefined);

    // 添加到最近访问
    if (selectedProject) {
      addRecentSession({
        composer_id: session.composer_id,
        session_name: session.name || `会话 ${session.composer_id.slice(0, 8)}`,
        project_name: selectedProject.project_name,
        workspace_hash: selectedProject.workspace_hash,
        visited_at: Date.now(),
      });
      // 重新加载最近访问列表
      setRecentSessions(getRecentSessions());
      // 检查收藏状态
      checkFavoriteStatus(session.composer_id);
    }
  };

  // 批量选择相关函数
  const toggleSessionSelect = (composerId: string) => {
    setSelectedSessionIds(prev =>
      prev.includes(composerId)
        ? prev.filter(id => id !== composerId)
        : [...prev, composerId]
    );
  };

  const clearSelection = () => {
    setSelectedSessionIds([]);
    setSelectMode(false);
  };

  const toggleSelectAll = () => {
    if (selectedSessionIds.length === sessions.length) {
      setSelectedSessionIds([]);
    } else {
      setSelectedSessionIds(sessions.map(s => s.composer_id));
    }
  };

  /** 点击搜索结果跳转 */
  const handleSearchResultClick = (item: SearchResultItem) => {
    setIsSearchMode(false);
    setGlobalSearch('');
    // 选中对应项目和会话
    const proj = projects.find(p => p.workspace_hash === item.workspace_hash);
    if (proj) {
      setSelectedProject(proj);
      loadSessions(item.workspace_hash).then(() => {
        setSelectedSession({ composer_id: item.composer_id, name: item.session_name, created_at: null, message_count: 0, workspace_hash: item.workspace_hash });
        loadMessages(item.composer_id, item.session_name || undefined);
      });
    } else {
      // 如果项目不在当前列表中，直接加载消息
      loadMessages(item.composer_id, item.session_name || undefined);
    }
  };

  /** 格式化时间戳（含年份） */
  const formatTime = (ts: number | null) => {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit',
      });
    } catch { return ''; }
  };

  // ==================== 渲染 ====================

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* 顶部导航栏 */}
      <div className="bg-slate-900/80 backdrop-blur-xl border-b border-slate-700/50 sticky top-0 z-30">
        <div className="max-w-[1920px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="text-slate-400 hover:text-white transition-colors">
              <i className="fas fa-arrow-left text-lg" />
            </button>
            <button
              onClick={() => setShowProjectPanel(prev => !prev)}
              className="text-slate-400 hover:text-white transition-colors"
              title={showProjectPanel ? '隐藏项目列表' : '显示项目列表'}
            >
              <i className={`fas ${showProjectPanel ? 'fa-indent' : 'fa-outdent'} text-lg`} />
            </button>
            {/* 最近访问按钮 */}
            <button
              onClick={() => setShowRecentPanel(prev => !prev)}
              className={`text-slate-400 hover:text-white transition-colors relative ${showRecentPanel ? 'text-violet-400' : ''}`}
              title="最近访问"
            >
              <i className="fas fa-history text-lg" />
              {recentSessions.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-violet-500 rounded-full text-[10px] flex items-center justify-center">
                  {Math.min(recentSessions.length, 9)}
                </span>
              )}
            </button>
            {/* 收藏夹按钮 */}
            <button
              onClick={() => setShowFavoritesPanel(prev => !prev)}
              className={`text-slate-400 hover:text-white transition-colors relative ${showFavoritesPanel ? 'text-amber-400' : ''}`}
              title="收藏夹"
            >
              <i className="fas fa-star text-lg" />
            </button>
            {/* 统计按钮 */}
            <button
              onClick={() => setShowStatsPanel(prev => !prev)}
              className={`text-slate-400 hover:text-white transition-colors relative ${showStatsPanel ? 'text-cyan-400' : ''}`}
              title="数据统计"
            >
              <i className="fas fa-chart-bar text-lg" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <i className="fas fa-clock-rotate-left text-violet-400 text-lg" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Cursor 对话历史</h1>
                <p className="text-xs text-slate-400">浏览和搜索 Cursor AI 历史对话</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* 全局搜索 */}
            <div className="relative w-96">
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm" />
              <input
                type="text"
                placeholder="搜索所有对话内容..."
                value={globalSearch}
                onChange={e => setGlobalSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doGlobalSearch(globalSearch)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-800/60 border border-slate-700/50 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all"
              />
              {globalSearch && (
                <button
                  onClick={() => { setGlobalSearch(''); setIsSearchMode(false); setSearchResults([]); }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                >
                  <i className="fas fa-times text-sm" />
                </button>
              )}
            </div>
            {/* 路径设置按钮 */}
            <button
              onClick={() => { setShowPathSettings(prev => !prev); setPathInput(customBasePath); }}
              className={`px-3 py-2.5 rounded-xl border text-sm transition-all ${
                customBasePath
                  ? 'bg-violet-500/20 border-violet-500/40 text-violet-400 hover:bg-violet-500/30'
                  : 'bg-slate-800/60 border-slate-700/50 text-slate-400 hover:text-white hover:border-slate-600'
              }`}
              title="设置 Cursor 数据路径"
            >
              <i className="fas fa-folder-tree" />
            </button>
          </div>
        </div>

        {/* 路径设置面板 */}
        {showPathSettings && (
          <div className="max-w-[1920px] mx-auto px-6 pb-4">
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <i className="fas fa-folder-tree text-violet-400 text-sm" />
                <span className="text-sm font-medium text-white">Cursor 数据目录</span>
                <span className="text-xs text-slate-500">（留空使用默认路径）</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="例如: ~/Library/Application Support/Cursor/User"
                    value={pathInput}
                    onChange={e => setPathInput(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-900/60 border border-slate-700/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 transition-all"
                  />
                  {/* 路径有效性提示 */}
                  {pathValid !== null && pathInput && (
                    <span className={`absolute right-3 top-1/2 -translate-y-1/2 text-sm ${pathValid ? 'text-emerald-400' : 'text-red-400'}`}>
                      <i className={`fas ${pathValid ? 'fa-check-circle' : 'fa-times-circle'}`} />
                    </span>
                  )}
                </div>
                <button
                  onClick={applyCustomPath}
                  className="px-4 py-2 bg-violet-500/20 border border-violet-500/40 rounded-lg text-sm text-violet-400 hover:bg-violet-500/30 transition-all"
                >
                  应用
                </button>
                {customBasePath && (
                  <button
                    onClick={() => { setCustomBasePath(''); setPathInput(''); setShowPathSettings(false); }}
                    className="px-4 py-2 bg-slate-700/40 border border-slate-600/50 rounded-lg text-sm text-slate-400 hover:text-white transition-all"
                  >
                    重置
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="max-w-[1920px] mx-auto px-6 py-3">
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
            <i className="fas fa-exclamation-circle" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
              <i className="fas fa-times" />
            </button>
          </div>
        </div>
      )}

      {/* 搜索结果模式 */}
      {isSearchMode ? (
        <div className="max-w-[1920px] mx-auto px-6 py-6">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-semibold text-white">搜索结果</h2>
            <span className="text-sm text-slate-400">({searchResults.length} 条)</span>
            {loading.search && <i className="fas fa-spinner fa-spin text-violet-400 text-sm" />}
          </div>
          <div className="space-y-3">
            {searchResults.map((item, idx) => (
              <div
                key={idx}
                onClick={() => handleSearchResultClick(item)}
                className="bg-slate-900/60 border border-slate-700/30 rounded-xl p-4 hover:border-violet-500/40 cursor-pointer transition-all group"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-violet-400 bg-violet-400/10 px-2 py-0.5 rounded-full">{item.project_name}</span>
                  {item.session_name && <span className="text-xs text-slate-500">/ {item.session_name}</span>}
                  <span className={`text-xs px-1.5 py-0.5 rounded ${item.message_type === 1 ? 'bg-blue-500/10 text-blue-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                    {item.message_type === 1 ? '用户' : 'AI'}
                  </span>
                </div>
                <p className="text-sm text-slate-300 line-clamp-3">{item.matched_text}</p>
              </div>
            ))}
            {!loading.search && searchResults.length === 0 && (
              <div className="text-center py-12 text-slate-500">
                <i className="fas fa-search text-3xl mb-3 block opacity-30" />
                <p>未找到匹配结果</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* 三栏布局（高度根据路径设置面板动态调整） */
        <div className="max-w-[1920px] mx-auto flex" style={{ height: showPathSettings ? 'calc(100vh - 170px)' : 'calc(100vh - 73px)' }}>

          {/* 统计面板（覆盖模式） */}
          {showStatsPanel && (
          <StatsPanel onClose={() => setShowStatsPanel(false)} />
          )}

          {/* 收藏面板（覆盖模式） */}
          {showFavoritesPanel && (
          <FavoritesPanel
            onClose={() => setShowFavoritesPanel(false)}
            onSelectSession={(composerId, workspaceHash, sessionName, projectName) => {
              // 查找并选中项目
              const proj = projects.find(p => p.workspace_hash === workspaceHash);
              if (proj) {
                setSelectedProject(proj);
                loadSessions(proj.workspace_hash);
              }
              // 选中会话
              setSelectedSession({
                composer_id: composerId,
                name: sessionName,
                created_at: null,
                message_count: 0,
                workspace_hash: workspaceHash,
              });
              loadMessages(composerId, sessionName);
              setShowFavoritesPanel(false);
            }}
          />
          )}

          {/* 最近访问面板（覆盖模式） */}
          {showRecentPanel && (
          <div className="w-72 flex-shrink-0 border-r border-slate-700/30 flex flex-col bg-slate-900/40 absolute left-0 top-0 bottom-0 z-20">
            <div className="p-3 border-b border-slate-700/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <i className="fas fa-history text-violet-400 text-sm" />
                <span className="text-sm font-semibold text-white">最近访问</span>
              </div>
              <button
                onClick={() => setShowRecentPanel(false)}
                className="text-slate-500 hover:text-white transition-colors"
              >
                <i className="fas fa-times text-xs" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {recentSessions.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">
                  <i className="fas fa-history text-2xl mb-2 block opacity-30" />
                  <p>暂无最近访问</p>
                </div>
              ) : (
                recentSessions.map((session, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      // 查找并选中项目
                      const proj = projects.find(p => p.workspace_hash === session.workspace_hash);
                      if (proj) {
                        setSelectedProject(proj);
                        loadSessions(proj.workspace_hash);
                      }
                      // 选中会话
                      setSelectedSession({
                        composer_id: session.composer_id,
                        name: session.session_name,
                        created_at: null,
                        message_count: 0,
                        workspace_hash: session.workspace_hash,
                      });
                      loadMessages(session.composer_id, session.session_name);
                      setShowRecentPanel(false);
                    }}
                    className="px-4 py-3 cursor-pointer border-b border-slate-800/50 transition-all hover:bg-slate-800/50"
                  >
                    <div className="text-sm font-medium text-white truncate">{session.session_name}</div>
                    <div className="text-xs text-slate-500 truncate mt-1">{session.project_name}</div>
                    <div className="text-xs text-violet-400 mt-1">{formatVisitedTime(session.visited_at)}</div>
                  </div>
                ))
              )}
            </div>
            {recentSessions.length > 0 && (
              <div className="p-3 border-t border-slate-700/30">
                <button
                  onClick={() => {
                    if (confirm('确定清空最近访问记录吗？')) {
                      localStorage.removeItem('cursor_history_recent_sessions');
                      setRecentSessions([]);
                    }
                  }}
                  className="w-full py-2 text-xs text-slate-400 hover:text-white transition-colors"
                >
                  <i className="fas fa-trash mr-2" />
                  清空记录
                </button>
              </div>
            )}
          </div>
          )}

          {/* 第一栏：项目列表（可折叠） */}
          {showProjectPanel && (
          <div className="w-72 flex-shrink-0 border-r border-slate-700/30 flex flex-col bg-slate-900/40">
            <div className="p-3 border-b border-slate-700/30">
              <div className="relative">
                <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs" />
                <input
                  type="text"
                  placeholder="搜索项目..."
                  value={projectSearch}
                  onChange={e => setProjectSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 transition-all"
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading.projects ? (
                <div className="flex items-center justify-center py-8">
                  <i className="fas fa-spinner fa-spin text-violet-400" />
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">
                  <i className="fas fa-folder-open text-2xl mb-2 block opacity-30" />
                  <p>暂无项目</p>
                </div>
              ) : (
                projects.map(project => (
                  <div
                    key={project.workspace_hash}
                    onClick={() => handleProjectClick(project)}
                    className={`px-4 py-3 cursor-pointer border-b border-slate-800/50 transition-all hover:bg-slate-800/50 ${
                      selectedProject?.workspace_hash === project.workspace_hash
                        ? 'bg-violet-500/10 border-l-2 border-l-violet-500'
                        : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <i className="fas fa-folder text-violet-400/70 text-sm" />
                      <span className="text-sm font-medium text-white truncate flex-1">{project.project_name}</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <i className="fas fa-comments text-[10px]" />
                      <span>{project.session_count} 个会话</span>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="p-3 border-t border-slate-700/30 text-xs text-slate-500 text-center">
              共 {projects.length} 个项目
            </div>
          </div>
          )}

          {/* 第二栏：会话列表 */}
          <div className="w-80 flex-shrink-0 border-r border-slate-700/30 flex flex-col bg-slate-900/20">
            <div className="p-3 border-b border-slate-700/30">
              {selectedProject ? (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <i className="fas fa-folder-open text-violet-400 text-sm" />
                    <span className="text-sm font-semibold text-white truncate">{selectedProject.project_name}</span>
                  </div>
                  <div className="flex flex-col gap-2">
                    <div className="relative">
                      <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs" />
                      <input
                        type="text"
                        placeholder="搜索会话..."
                        value={sessionSearch}
                        onChange={e => {
                          setSessionSearch(e.target.value);
                          // 防抖：延迟 300ms 后搜索
                          setTimeout(() => {
                            loadSessions(selectedProject.workspace_hash, e.target.value, selectedFilterTag);
                          }, 300);
                        }}
                        className="w-full pl-9 pr-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 transition-all"
                      />
                    </div>
                    <TagFilter onTagSelect={(tag) => {
                      setSelectedFilterTag(tag);
                      loadSessions(selectedProject.workspace_hash, sessionSearch || undefined, tag);
                    }} />
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-2">← 请选择一个项目</p>
              )}
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading.sessions ? (
                <div className="flex items-center justify-center py-8">
                  <i className="fas fa-spinner fa-spin text-violet-400" />
                </div>
              ) : !selectedProject ? (
                <div className="text-center py-12 text-slate-600">
                  <i className="fas fa-comments text-3xl mb-3 block opacity-20" />
                  <p className="text-sm">选择项目查看会话</p>
                </div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">
                  <p>暂无会话</p>
                </div>
              ) : (
                <>
                  {/* 批量操作工具栏 */}
                  <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800/30 bg-slate-800/30">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectMode(!selectMode)}
                        className={`px-2 py-1 rounded text-xs transition-colors ${
                          selectMode
                            ? 'bg-violet-500 text-white'
                            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                        }`}
                      >
                        {selectMode ? '退出选择' : '多选'}
                      </button>
                      {selectMode && (
                        <button
                          onClick={toggleSelectAll}
                          className="px-2 py-1 bg-slate-700 text-slate-300 hover:bg-slate-600 rounded text-xs transition-colors"
                        >
                          {selectedSessionIds.length === sessions.length ? '取消全选' : '全选'}
                        </button>
                      )}
                    </div>
                    {selectMode && selectedSessionIds.length > 0 && (
                      <span className="text-xs text-slate-400">
                        已选择 {selectedSessionIds.length} 个会话
                      </span>
                    )}
                  </div>

                  {/* 会话列表 */}
                  {sessions.map(session => (
                    <div
                      key={session.composer_id}
                      onClick={() => handleSessionClick(session)}
                      className={`px-4 py-3 cursor-pointer border-b border-slate-800/30 transition-all hover:bg-slate-800/40 flex items-start gap-3 ${
                        selectedSession?.composer_id === session.composer_id
                          ? 'bg-violet-500/10 border-l-2 border-l-violet-500'
                          : ''
                      } ${
                        selectMode && selectedSessionIds.includes(session.composer_id)
                          ? 'bg-blue-500/10'
                          : ''
                      }`}
                    >
                      {selectMode && (
                        <input
                          type="checkbox"
                          checked={selectedSessionIds.includes(session.composer_id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleSessionSelect(session.composer_id);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="mt-1 w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">{session.name || `会话 ${session.composer_id.slice(0, 8)}`}</div>
                        <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                          {session.created_at && <span>{formatTime(session.created_at)}</span>}
                          <span>{session.message_count} 条消息</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>


          {/* 第三栏：消息内容 */}
          <div className="flex-1 flex flex-col min-w-0 bg-slate-950">
            {selectedSession ? (
              <>
                {/* 会话标题 */}
                <div className="p-4 border-b border-slate-700/30 bg-slate-900/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                        <i className="fas fa-comments text-violet-400 text-sm" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-semibold text-white truncate">{selectedSession.name || `会话 ${selectedSession.composer_id.slice(0, 8)}`}</h3>
                        <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 flex-wrap">
                          <span>已加载 {messages.length} / {totalMessages} 条消息</span>
                          {selectedSession.created_at && (
                            <span><i className="fas fa-clock mr-1" />{formatTime(selectedSession.created_at)}</span>
                          )}
                          <TagManager composerId={selectedSession.composer_id} />
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {/* 收藏按钮 */}
                      <button
                        onClick={handleToggleFavorite}
                        className={`p-2 rounded-lg transition-all ${
                          isFavorite
                            ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                            : 'bg-slate-700/50 text-slate-400 hover:text-amber-400'
                        }`}
                        title={isFavorite ? '取消收藏' : '收藏会话'}
                      >
                        <i className={`fas fa-star ${isFavorite ? 'fas' : 'far'}`} />
                      </button>
                      {/* 导出按钮 */}
                      <button
                        onClick={() => setShowExportDialog(true)}
                        className="px-3 py-1.5 bg-violet-500/20 border border-violet-500/40 rounded-lg text-xs text-violet-400 hover:bg-violet-500/30 transition-all flex items-center gap-1.5"
                        title="导出会话"
                      >
                        <i className="fas fa-download" />
                        <span>导出</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 消息列表（虚拟滚动） */}
                <div className="flex-1 overflow-hidden p-6">
                  {loading.messages ? (
                    <div className="flex items-center justify-center py-12">
                      <i className="fas fa-spinner fa-spin text-violet-400 text-xl" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">
                      <i className="fas fa-inbox text-3xl mb-3 block opacity-30" />
                      <p>暂无消息</p>
                    </div>
                  ) : (
                    <AutoSizer>
                      {({ height, width }) => (
                        <List
                          ref={virtualListRef}
                          height={height}
                          width={width}
                          itemCount={messages.length}
                          itemSize={200}
                          itemData={messages}
                          overscanCount={5}
                        >
                          {MessageRow}
                        </List>
                      )}
                    </AutoSizer>
                  )}
                  {/* 加载更多提示 */}
                  {loadingMore && (
                    <div className="flex items-center justify-center py-4">
                      <i className="fas fa-spinner fa-spin text-violet-400 mr-2" />
                      <span className="text-xs text-slate-500">加载更多消息...</span>
                    </div>
                  )}
                  {!loadingMore && hasMore && (
                    <div className="text-center py-3">
                      <button
                        onClick={loadMoreMessages}
                        className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
                      >
                        <i className="fas fa-angle-down mr-1" />
                        滚动或点击加载更多（还有 {totalMessages - messages.length} 条）
                      </button>
                    </div>
                  )}
                  {!hasMore && messages.length > 0 && !loading.messages && (
                    <div className="text-center py-3 text-xs text-slate-600">
                      — 已加载全部 {totalMessages} 条消息 —
                    </div>
                  )}
                </div>
              </>
            ) : (
              /* 空状态 */
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 rounded-2xl bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
                    <i className="fas fa-clock-rotate-left text-3xl text-slate-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">选择一个会话查看内容</h3>
                  <p className="text-sm text-slate-600">从左侧选择项目和会话，或使用顶部搜索</p>
                </div>
              </div>
            )}
          </div>

        </div>
      )}

      {/* 导出对话框 */}
      {showExportDialog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <i className="fas fa-download text-violet-400 text-lg" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">导出会话</h3>
                <p className="text-xs text-slate-400">选择导出格式和选项</p>
              </div>
            </div>

            {/* 导出格式选择 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-3">导出格式</label>
              <div className="grid grid-cols-3 gap-3">
                {(['markdown', 'json', 'html'] as const).map((format) => (
                  <button
                    key={format}
                    onClick={() => setExportFormat(format)}
                    className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                      exportFormat === format
                        ? 'bg-violet-500/20 border-violet-500/50 text-violet-400'
                        : 'bg-slate-700/30 border-slate-600/50 text-slate-400 hover:border-slate-500'
                    }`}
                  >
                    {format === 'markdown' && <><i className="fas fa-file-alt mr-2" />MD</>}
                    {format === 'json' && <><i className="fas fa-file-code mr-2" />JSON</>}
                    {format === 'html' && <><i className="fas fa-file-html mr-2" />HTML</>}
                  </button>
                ))}
              </div>
            </div>

            {/* 导出选项 */}
            <div className="mb-6 space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exportOptions.includeCodeBlocks}
                  onChange={e => setExportOptions(prev => ({ ...prev, includeCodeBlocks: e.target.checked }))}
                  className="w-4 h-4 rounded border-slate-600 text-violet-500 focus:ring-violet-500/50 bg-slate-700"
                />
                <span className="text-sm text-slate-300">包含代码块</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exportOptions.includeTimestamps}
                  onChange={e => setExportOptions(prev => ({ ...prev, includeTimestamps: e.target.checked }))}
                  className="w-4 h-4 rounded border-slate-600 text-violet-500 focus:ring-violet-500/50 bg-slate-700"
                />
                <span className="text-sm text-slate-300">包含序号</span>
              </label>
              {exportFormat === 'html' && (
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeAvatars}
                    onChange={e => setExportOptions(prev => ({ ...prev, includeAvatars: e.target.checked }))}
                    className="w-4 h-4 rounded border-slate-600 text-violet-500 focus:ring-violet-500/50 bg-slate-700"
                  />
                  <span className="text-sm text-slate-300">包含头像图标 (HTML)</span>
                </label>
              )}
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowExportDialog(false)}
                disabled={exportLoading}
                className="flex-1 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700/50 text-white rounded-xl transition-all text-sm font-medium"
              >
                取消
              </button>
              <button
                onClick={handleExport}
                disabled={exportLoading}
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 disabled:opacity-50 text-white rounded-xl transition-all text-sm font-medium flex items-center justify-center gap-2"
              >
                {exportLoading ? (
                  <>
                    <i className="fas fa-spinner fa-spin" />
                    <span>导出中...</span>
                  </>
                ) : (
                  <>
                    <i className="fas fa-download" />
                    <span>导出</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 批量操作工具栏 */}
      {selectMode && (
        <BatchActions
          selectedIds={selectedSessionIds}
          onClearSelection={clearSelection}
          onRefresh={() => {
            if (selectedProject) {
              loadSessions(selectedProject.workspace_hash, sessionSearch || undefined, selectedFilterTag);
            }
          }}
        />
      )}
    </div>
  );
}

/**
 * 收藏面板组件
 */
interface FavoritesPanelProps {
  onClose: () => void;
  onSelectSession: (composerId: string, workspaceHash: string, sessionName: string, projectName: string) => void;
}

const FavoritesPanel: React.FC<FavoritesPanelProps> = ({ onClose, onSelectSession }) => {
  const [favorites, setFavorites] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { success: showSuccess, error: showError } = useToast();

  // 加载收藏列表
  useEffect(() => {
    loadFavorites();
  }, []);

  const loadFavorites = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/cursor-history/favorites`);
      if (!res.ok) throw new Error('加载收藏失败');
      const data = await res.json();
      setFavorites(data.favorites || []);
    } catch (err) {
      console.error('加载收藏失败:', err);
      showError('加载收藏失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (composerId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE_URL}/cursor-history/favorites/${composerId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('删除失败');
      showSuccess('删除成功');
      loadFavorites();
    } catch (err) {
      showError('删除失败');
    }
  };

  return (
    <div className="w-72 flex-shrink-0 border-r border-slate-700/30 flex flex-col bg-slate-900/40 absolute left-0 top-0 bottom-0 z-20">
      <div className="p-3 border-b border-slate-700/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <i className="fas fa-star text-amber-400 text-sm" />
          <span className="text-sm font-semibold text-white">收藏夹</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white transition-colors"
        >
          <i className="fas fa-times text-xs" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <i className="fas fa-spinner fa-spin text-violet-400" />
          </div>
        ) : favorites.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            <i className="fas fa-star text-2xl mb-2 block opacity-30" />
            <p>暂无收藏</p>
          </div>
        ) : (
          favorites.map((fav, idx) => (
            <div
              key={idx}
              onClick={() => onSelectSession(fav.composer_id, fav.workspace_hash || '', fav.session_name || '', fav.project_name || '')}
              className="px-4 py-3 cursor-pointer border-b border-slate-800/50 transition-all hover:bg-slate-800/50"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-amber-400 truncate">{fav.session_name || '未命名会话'}</div>
                  <div className="text-xs text-slate-500 truncate mt-1">{fav.project_name || '未知项目'}</div>
                  <div className="text-xs text-slate-600 mt-1">{new Date(fav.created_at).toLocaleDateString('zh-CN')}</div>
                </div>
                <button
                  onClick={(e) => handleDelete(fav.composer_id, e)}
                  className="text-slate-600 hover:text-red-400 transition-colors p-1"
                >
                  <i className="fas fa-trash text-xs" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="p-3 border-t border-slate-700/30 text-xs text-slate-500 text-center">
        共 {favorites.length} 个收藏
      </div>
    </div>
  );
};

/**
 * 统计面板组件
 */
interface StatsPanelProps {
  onClose: () => void;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ onClose }) => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    overview: {
      total_sessions: 0,
      total_messages: 0,
      today_sessions: 0,
      today_messages: 0,
      total_projects: 0,
    },
    trends: [] as Array<{ date: string; sessions: number; messages: number }>,
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/cursor-history/stats?days=7`);
      if (!res.ok) throw new Error('加载统计失败');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('加载统计失败:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-96 flex-shrink-0 border-r border-slate-700/30 flex flex-col bg-slate-900/40 absolute left-0 top-0 bottom-0 z-20 overflow-y-auto">
      <div className="p-3 border-b border-slate-700/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <i className="fas fa-chart-bar text-cyan-400 text-sm" />
          <span className="text-sm font-semibold text-white">数据统计</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white transition-colors"
        >
          <i className="fas fa-times text-xs" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <i className="fas fa-spinner fa-spin text-violet-400" />
          </div>
        ) : (
          <>
            {/* 概览卡片 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                <div className="text-xs text-slate-400 mb-1">总会话</div>
                <div className="text-2xl font-bold text-white">{stats.overview.total_sessions}</div>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                <div className="text-xs text-slate-400 mb-1">总消息</div>
                <div className="text-2xl font-bold text-white">{stats.overview.total_messages}</div>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                <div className="text-xs text-slate-400 mb-1">今日会话</div>
                <div className="text-2xl font-bold text-emerald-400">{stats.overview.today_sessions}</div>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                <div className="text-xs text-slate-400 mb-1">今日消息</div>
                <div className="text-2xl font-bold text-emerald-400">{stats.overview.today_messages}</div>
              </div>
            </div>

            {/* 趋势图表 */}
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
              <div className="text-xs text-slate-400 mb-3">近 7 天趋势</div>
              <div className="space-y-2">
                {stats.trends.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <div className="text-xs text-slate-500 w-12">{item.date.slice(5)}</div>
                    <div className="flex-1 h-6 bg-slate-700/30 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full"
                        style={{ width: `${Math.max(5, (item.sessions / Math.max(...stats.trends.map(t => t.sessions))) * 100)}%` }}
                      />
                    </div>
                    <div className="text-xs text-slate-400 w-8 text-right">{item.sessions}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
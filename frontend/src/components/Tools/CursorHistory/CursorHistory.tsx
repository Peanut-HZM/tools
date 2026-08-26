/**
 * Cursor 对话历史查看器 - 主组件
 * 作者：huazm
 * 描述：三栏布局的 Cursor AI 对话历史浏览和搜索工具
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { AlertCircle, AlertTriangle, ArrowLeft, BarChart3, Bot, Brain, CheckCircle, CheckSquare, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Clock, Copy, Database, Download, FileCode, FileText, Folder, FolderOpen, FolderTree, History, Inbox, Indent, Loader2, MessageSquare, Outdent, RefreshCw, Search, Star, Trash2, User, Wrench, X, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
// react-window 和 AutoSizer 已移除，改为普通滚动列表
import { API_BASE_URL } from '../../../config/api';
import { useToast } from '../../../hooks/useToast';
import { cacheSessionMessages, getCachedSessionMessages } from '../../../utils/cursorCache';
import { addRecentSession, getRecentSessions, formatVisitedTime, type RecentSession } from '../../../utils/recentSessions';
import TagManager from './TagManager';
import TagFilter from './TagFilter';
import BatchActions from './BatchActions';
import ThemeSwitcher from './ThemeSwitcher';
import ResizablePanel from './ResizablePanel';
import { Badge } from '@/components/ui/Badge';

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
  match_type: 'title' | 'content';
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
  // 搜索分页状态
  const [searchPage, setSearchPage] = useState(1);
  const [searchTotalPages, setSearchTotalPages] = useState(1);
  const [searchTotal, setSearchTotal] = useState(0);

  // 新增状态：侧边栏折叠、自定义路径、路径设置面板
  const [showProjectPanel, setShowProjectPanel] = useState(true);
  const [customBasePath, setCustomBasePath] = useState('');
  const [showPathSettings, setShowPathSettings] = useState(false);
  const [pathInput, setPathInput] = useState('');
  const [pathValid, setPathValid] = useState<boolean | null>(null);

  // 分页状态（反向加载：最新消息在底部，向上加载历史）
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [totalMessages, setTotalMessages] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);

  // 虚拟滚动已移除，使用普通滚动

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

  // 项目多选删除状态
  const [selectedProjectHashes, setSelectedProjectHashes] = useState<Set<string>>(new Set());
  const [projectSelectMode, setProjectSelectMode] = useState(false);

  // 同步状态
  const [syncStatus, setSyncStatus] = useState<{
    syncing: boolean;
    progress: number;
    total: number;
    current_step: string;
    last_sync_time: string | null;
    error: string | null;
  }>({ syncing: false, progress: 0, total: 0, current_step: '', last_sync_time: null, error: null });

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
      const res = await fetch(`${API_BASE_URL}/cursor-history/projects?${params}`);
      if (!res.ok) throw new Error('加载项目列表失败');
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, projects: false }));
    }
  }, []);

  /** 加载会话列表 */
  const loadSessions = useCallback(async (workspaceHash: string, search?: string, tag?: string) => {
    setLoading(prev => ({ ...prev, sessions: true }));
    try {
      const params = new URLSearchParams({ workspace_hash: workspaceHash });
      if (search) params.set('search', search);
      if (tag) params.set('tag', tag);
      const res = await fetch(`${API_BASE_URL}/cursor-history/sessions?${params}`);
      if (!res.ok) throw new Error('加载会话列表失败');
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, sessions: false }));
    }
  }, []);

  /** 加载消息列表（首次加载：加载最新消息，滚到底部） */
  const loadMessages = useCallback(async (composerId: string, sessionName?: string) => {
    setLoading(prev => ({ ...prev, messages: true }));
    setCurrentPage(1);

    // 尝试从缓存加载（只有非空缓存才提前返回）
    const cachedMessages = await getCachedSessionMessages(composerId);
    if (cachedMessages && cachedMessages.length > 0) {
      setMessages(cachedMessages);
      setLoading(prev => ({ ...prev, messages: false }));
      // 缓存加载后滚到底部
      setTimeout(() => {
        messageListRef.current?.scrollTo({ top: messageListRef.current.scrollHeight });
      }, 50);
      return;
    }

    try {
      // 使用 latest_first=true，page=1 返回最新的一批消息
      const params = new URLSearchParams({
        composer_id: composerId,
        page: '1',
        page_size: '50',
        latest_first: 'true',
      });
      if (sessionName) params.set('session_name', sessionName);
      const res = await fetch(`${API_BASE_URL}/cursor-history/messages?${params}`);
      if (!res.ok) throw new Error('加载消息失败');
      const data = await res.json();
      setMessages(data.messages || []);
      setTotalMessages(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setHasMore(data.has_more || false);

      // 首次加载后滚动到底部（显示最新消息）
      setTimeout(() => {
        messageListRef.current?.scrollTo({ top: messageListRef.current.scrollHeight });
      }, 50);

      // 存入缓存
      if (data.messages && data.messages.length > 0) {
        await cacheSessionMessages(composerId, data.messages, selectedProject?.project_name, sessionName);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, messages: false }));
    }
  }, [selectedProject]);

  /** 加载更多历史消息（向上滚动时触发，prepend 到列表前面） */
  const loadMoreMessages = useCallback(async () => {
    if (!selectedSession || loadingMore || !hasMore) return;
    const nextPage = currentPage + 1;
    setLoadingMore(true);

    // 记录当前滚动位置，用于 prepend 后保持视觉位置不跳
    const container = messageListRef.current;
    const prevScrollHeight = container?.scrollHeight || 0;

    try {
      const params = new URLSearchParams({
        composer_id: selectedSession.composer_id,
        page: String(nextPage),
        page_size: '50',
        latest_first: 'true',
      });
      const res = await fetch(`${API_BASE_URL}/cursor-history/messages?${params}`);
      if (!res.ok) throw new Error('加载更多消息失败');
      const data = await res.json();
      const olderMessages = data.messages || [];

      // 将更旧的消息 prepend 到现有消息前面
      setMessages(prev => [...olderMessages, ...prev]);
      setCurrentPage(nextPage);
      setHasMore(data.has_more || false);
      setTotalMessages(data.total || 0);

      // 恢复滚动位置：prepend 后 scrollHeight 增大，
      // 需要将 scrollTop 增加相应的差值
      setTimeout(() => {
        if (container) {
          const newScrollHeight = container.scrollHeight;
          container.scrollTop += (newScrollHeight - prevScrollHeight);
        }
      }, 0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }, [selectedSession, loadingMore, hasMore, currentPage]);

  /** 全局搜索（支持分页） */
  const doGlobalSearch = useCallback(async (query: string, page: number = 1) => {
    if (!query.trim()) {
      setIsSearchMode(false);
      setSearchResults([]);
      setSearchPage(1);
      setSearchTotalPages(1);
      setSearchTotal(0);
      return;
    }
    setLoading(prev => ({ ...prev, search: true }));
    setIsSearchMode(true);
    try {
      const params = new URLSearchParams({
        query,
        page: String(page),
        page_size: '20',
      });
      const res = await fetch(`${API_BASE_URL}/cursor-history/search?${params}`);
      if (!res.ok) throw new Error('搜索失败');
      const data = await res.json();
      setSearchResults(data.results || []);
      setSearchPage(data.page || 1);
      setSearchTotalPages(data.total_pages || 1);
      setSearchTotal(data.total || 0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(prev => ({ ...prev, search: false }));
    }
  }, []);

  /** 轮询同步状态 */
  const pollSyncStatus = useCallback(() => {
    let timer: ReturnType<typeof setInterval> | null = null;

    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/cursor-history/sync/status`);
        const data = await res.json();
        setSyncStatus(data);

        // 同步完成后刷新数据并停止轮询
        if (!data.syncing && timer) {
          if (data.last_sync_time) {
            loadProjects();
          }
          clearInterval(timer);
          timer = null;
        }
      } catch {
        // 忽略轮询错误
      }
    };

    // 初始检查一次
    pollStatus();

    // 每 2 秒轮询
    timer = setInterval(pollStatus, 2000);

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [loadProjects]);

  /** 触发数据同步 */
  const triggerSync = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (customBasePath) params.set('base_path', customBasePath);
      const res = await fetch(`${API_BASE_URL}/cursor-history/sync?${params}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showSuccess('同步任务已启动');
        // 立即开始轮询同步状态
        pollSyncStatus();
      } else {
        showError(data.message || '同步失败');
      }
    } catch (e) {
      showError('触发同步失败：' + (e as Error).message);
    }
  }, [customBasePath, showSuccess, showError, pollSyncStatus]);

  // 初始加载时检查同步状态
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/cursor-history/sync/status`);
        const data = await res.json();
        setSyncStatus(data);
      } catch {
        // 忽略轮询错误
      }
    };
    pollStatus();
  }, []);



  /** 删除缓存中的项目 */
  const deleteCachedProject = useCallback(async (hash: string) => {
    try {
      const params = new URLSearchParams({ workspace_hash: hash });
      const res = await fetch(`${API_BASE_URL}/cursor-history/cache/projects?${params}`, { method: 'DELETE' });
      if (res.ok) {
        showSuccess('项目已删除');
        loadProjects();
        if (selectedProject?.workspace_hash === hash) {
          setSelectedProject(null);
          setSessions([]);
          setMessages([]);
        }
      }
    } catch (e) {
      showError('删除失败: ' + (e as Error).message);
    }
  }, [loadProjects, selectedProject, showSuccess, showError]);

  /** 批量删除缓存中的项目 */
  const batchDeleteProjects = useCallback(async () => {
    if (selectedProjectHashes.size === 0) return;
    const hashList = Array.from(selectedProjectHashes);
    try {
      const res = await fetch(`${API_BASE_URL}/cursor-history/cache/projects/batchDelete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_hashes: hashList }),
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(data.message || '批量删除成功');
        setSelectedProjectHashes(new Set());
        setProjectSelectMode(false);
        loadProjects();
        // 如果删除了当前选中的项目，清空会话和消息
        if (selectedProject && hashList.includes(selectedProject.workspace_hash)) {
          setSelectedProject(null);
          setSessions([]);
          setMessages([]);
        }
      } else {
        showError('批量删除失败');
      }
    } catch (e) {
      showError('批量删除失败: ' + (e as Error).message);
    }
  }, [selectedProjectHashes, selectedProject, loadProjects, showSuccess, showError]);

  /** 切换项目的选中状态 */
  const toggleProjectSelect = useCallback((hash: string) => {
    setSelectedProjectHashes(prev => {
      const next = new Set(prev);
      if (next.has(hash)) {
        next.delete(hash);
      } else {
        next.add(hash);
      }
      return next;
    });
  }, []);

  /** 删除缓存中的会话 */
  const deleteCachedSession = useCallback(async (composerId: string) => {
    try {
      const params = new URLSearchParams({ composer_id: composerId });
      const res = await fetch(`${API_BASE_URL}/cursor-history/cache/sessions?${params}`, { method: 'DELETE' });
      if (res.ok) {
        showSuccess('会话已删除');
        if (selectedProject) {
          loadSessions(selectedProject.workspace_hash);
        }
        if (selectedSession?.composer_id === composerId) {
          setSelectedSession(null);
          setMessages([]);
        }
      }
    } catch (e) {
      showError('删除失败: ' + (e as Error).message);
    }
  }, [selectedProject, selectedSession, loadSessions, showSuccess, showError]);

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

      // 如果是 Markdown 模式，保留原始格式（AI 消息可能是 type=0 或 type=2）
      if (copyType === 'markdown' && (msg.message_type === 0 || msg.message_type === 2)) {
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

  /** 消息项渲染组件 */
  const MessageItem = useCallback(({ msg }: { msg: CursorMessage }) => {

    const isThinking = msg.capability_type === 30;
    const isToolCall = msg.capability_type === 15;
    // 消息类型：1=用户，0 或 2=AI（2 是 Cursor 原始格式，0 是后端映射后的格式）
    const isUser = msg.message_type === 1;
    const isAI = msg.message_type === 0 || msg.message_type === 2;

    // 思考块渲染
    if (isThinking) {
      const isExpanded = expandedThinking.has(msg.message_id);
      const thinkingText = msg.thinking || msg.text || '';
      return (
        <div className="flex justify-start group">
          <div className="max-w-[80%] rounded-2xl px-5 py-3 bg-amber-500/5 border border-amber-500/15">
            <div
              className="flex items-center gap-2 cursor-pointer select-none"
              onClick={() => toggleThinking(msg.message_id)}
            >
              <Brain className="w-3 h-3" />
              <span className="text-xs font-medium text-amber-400/80">AI 思考过程</span>
              {msg.timestamp && (
                <span className="text-[10px] text-ink-faint ml-1">{formatMessageTime(msg.timestamp)}</span>
              )}
              {isExpanded ? <ChevronUp className="w-2.5 h-2.5 text-amber-400/50 text-[10px] ml-auto" /> : <ChevronDown className="w-2.5 h-2.5 text-amber-400/50 text-[10px] ml-auto" />}
            </div>
            {isExpanded && thinkingText && (
              <div className="mt-2 text-xs text-ink-muted whitespace-pre-wrap break-words leading-relaxed max-h-[300px] overflow-y-auto italic">
                {thinkingText}
              </div>
            )}
          </div>
        </div>
      );
    }

    // 工具调用渲染
    if (isToolCall && msg.tool_call) {
      const StatusIcon = msg.tool_call.status === 'completed' ? CheckCircle :
                         msg.tool_call.status === 'running' ? Loader2 :
                         msg.tool_call.status === 'error' ? XCircle :
                         Wrench;
      const statusIconClass = msg.tool_call.status === 'completed' ? 'text-success' :
                         msg.tool_call.status === 'running' ? 'animate-spin text-accent-info' :
                         msg.tool_call.status === 'error' ? 'text-danger' :
                         'text-ink-muted';
      return (
        <div className="flex justify-start group">
          <div className="max-w-[80%] rounded-xl px-4 py-2.5 bg-accent/5 border border-accent/15">
            <div className="flex items-center gap-2">
              <StatusIcon className={`w-3 h-3 ${statusIconClass}`} />
              <span className="text-xs font-medium text-accent/80">
                {msg.tool_call.toolName || '工具调用'}
              </span>
              {msg.tool_call.status && (
                <Badge
                  variant={
                    msg.tool_call.status === 'completed' ? 'tint-success' :
                    msg.tool_call.status === 'error' ? 'tint-danger' :
                    'secondary'
                  }
                  className="text-[10px] px-1.5 py-0.5 font-normal"
                >
                  {msg.tool_call.status === 'completed' ? '完成' : msg.tool_call.status === 'error' ? '失败' : msg.tool_call.status}
                </Badge>
              )}
              {msg.timestamp && (
                <span className="text-[10px] text-ink-faint ml-1">{formatMessageTime(msg.timestamp)}</span>
              )}
            </div>
            {msg.text && (
              <div className="mt-1.5 text-xs text-ink-faint whitespace-pre-wrap break-words line-clamp-3">
                {msg.text}
              </div>
            )}
          </div>
        </div>
      );
    }

    // 普通消息渲染
    return (
      <div className={`flex group ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
          isUser
            ? 'bg-violet-500/20 border border-violet-500/20'
            : 'bg-surface-1/60 border border-border/30'
        }`}>
          {/* 消息头：角色 + 时间 + 复制按钮 */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              {isUser ? <User className="w-3 h-3 text-violet-400" /> : <Bot className="w-3 h-3 text-success" />}
              <span className={`text-xs font-medium ${isUser ? 'text-violet-400' : 'text-success'}`}>
                {isUser ? '用户' : 'AI 助手'}
              </span>
              {msg.timestamp && (
                <span className="text-[10px] text-ink-faint">{formatMessageTime(msg.timestamp)}</span>
              )}
            </div>
            {/* 复制按钮组（hover 显示） */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => handleCopyMessage(msg, 'text')}
                className="p-1.5 text-ink-muted hover:text-ink-inverse hover:bg-surface-2/50 rounded transition-all"
                title="复制纯文本"
              >
                <Copy className="w-3 h-3" />
              </button>
              {!isUser && (
                <button
                  onClick={() => handleCopyMessage(msg, 'markdown')}
                  className="p-1.5 text-ink-muted hover:text-ink-inverse hover:bg-surface-2/50 rounded transition-all"
                  title="复制 Markdown"
                >
                  <FileCode className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
          {/* 消息内容 */}
          {isUser ? (
            <div className="text-sm text-ink whitespace-pre-wrap break-words leading-relaxed">
              {msg.text}
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none text-ink break-words
              prose-headings:text-ink-inverse prose-headings:font-semibold
              prose-p:text-ink-muted prose-p:leading-relaxed prose-p:my-2
              prose-strong:text-ink-inverse prose-em:text-accent-info
              prose-code:text-emerald-300 prose-code:bg-canvas/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-canvas/80 prose-pre:border prose-pre:border-border/40 prose-pre:rounded-lg prose-pre:my-3
              prose-a:text-accent prose-a:no-underline hover:prose-a:underline
              prose-li:text-ink-muted prose-li:my-0.5
              prose-blockquote:border-l-violet-500 prose-blockquote:text-ink-muted
              prose-table:text-sm prose-th:text-ink-muted prose-td:text-ink-muted
              prose-hr:border-border
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
                    <pre className="bg-canvas/80 border border-border/40 rounded-lg p-3 pr-12 text-xs text-ink-muted overflow-x-auto">
                      <code>{codeText}</code>
                    </pre>
                    <button
                      onClick={() => handleCopyCodeBlock(codeText)}
                      className="absolute top-2 right-2 p-1.5 bg-surface-1/80 hover:bg-surface-2 border border-border/50 rounded text-ink-muted hover:text-ink-inverse opacity-0 group-hover/code:opacity-100 transition-all"
                      title="复制代码"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }, [handleCopyMessage, handleCopyCodeBlock, expandedThinking, toggleThinking, formatMessageTime]);

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

  // 消息列表滚动加载历史消息（滚动到顶部时触发）
  useEffect(() => {
    const container = messageListRef.current;
    if (!container) return;
    const handleScroll = () => {
      // 距离顶部 200px 时触发加载更早的消息
      if (container.scrollTop < 200 && hasMore && !loadingMore) {
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
    <div className="min-h-screen bg-canvas text-ink-inverse">
      {/* 顶部导航栏 */}
      <div className="bg-canvas/80 backdrop-blur-xl border-b border-border/50 sticky top-0 z-30">
        <div className="max-w-[1920px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="text-ink-muted hover:text-ink-inverse transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <button
              onClick={() => setShowProjectPanel(prev => !prev)}
              className="text-ink-muted hover:text-ink-inverse transition-colors"
              title={showProjectPanel ? '隐藏项目列表' : '显示项目列表'}
            >
              {showProjectPanel ? <Indent className="w-5 h-5" /> : <Outdent className="w-5 h-5" />}
            </button>
            {/* 最近访问按钮 */}
            <button
              onClick={() => setShowRecentPanel(prev => !prev)}
              className={`text-ink-muted hover:text-ink-inverse transition-colors relative ${showRecentPanel ? 'text-violet-400' : ''}`}
              title="最近访问"
            >
              <History className="w-5 h-5" />
              {recentSessions.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-violet-500 rounded-full text-[10px] flex items-center justify-center">
                  {Math.min(recentSessions.length, 9)}
                </span>
              )}
            </button>
            {/* 收藏夹按钮 */}
            <button
              onClick={() => setShowFavoritesPanel(prev => !prev)}
              className={`text-ink-muted hover:text-ink-inverse transition-colors relative ${showFavoritesPanel ? 'text-amber-400' : ''}`}
              title="收藏夹"
            >
              <Star className="w-5 h-5" />
            </button>
            {/* 统计按钮 */}
            <button
              onClick={() => setShowStatsPanel(prev => !prev)}
              className={`text-ink-muted hover:text-ink-inverse transition-colors relative ${showStatsPanel ? 'text-accent' : ''}`}
              title="数据统计"
            >
              <BarChart3 className="w-5 h-5" />
            </button>
            {/* 同步数据按钮 */}
            <button
              onClick={triggerSync}
              disabled={syncStatus.syncing}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                syncStatus.syncing
                  ? 'bg-accent-info/20 text-accent-info cursor-not-allowed'
                  : 'bg-emerald-500/20 text-success hover:bg-emerald-500/30 border border-emerald-500/30'
              }`}
              title={syncStatus.last_sync_time ? `上次同步: ${syncStatus.last_sync_time}` : '同步 Cursor 数据到本地缓存'}
            >
              {syncStatus.syncing ? <RefreshCw className="w-4 h-4 mr-1.5 inline-block animate-spin" /> : <Database className="w-4 h-4 mr-1.5 inline-block" />}
              {syncStatus.syncing ? '同步中...' : '同步数据'}
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <History className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-ink-inverse">Cursor 对话历史</h1>
                <p className="text-xs text-ink-muted">浏览和搜索 Cursor AI 历史对话</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* 全局搜索 */}
            <div className="relative w-96">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="搜索所有对话内容..."
                value={globalSearch}
                onChange={e => setGlobalSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doGlobalSearch(globalSearch)}
                className="w-full pl-10 pr-4 py-2.5 bg-surface-1/60 border border-border/50 rounded-xl text-sm text-ink-inverse placeholder-ink-faint focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all"
              />
              {globalSearch && (
                <button
                  onClick={() => { setGlobalSearch(''); setIsSearchMode(false); setSearchResults([]); setSearchPage(1); setSearchTotalPages(1); setSearchTotal(0); }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink-inverse"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            {/* 路径设置按钮 */}
            <button
              onClick={() => { setShowPathSettings(prev => !prev); setPathInput(customBasePath); }}
              className={`px-3 py-2.5 rounded-xl border text-sm transition-all ${
                customBasePath
                  ? 'bg-violet-500/20 border-violet-500/40 text-violet-400 hover:bg-violet-500/30'
                  : 'bg-surface-1/60 border-border/50 text-ink-muted hover:text-ink-inverse hover:border-border'
              }`}
              title="设置 Cursor 数据路径"
            >
              <FolderTree className="w-4 h-4" />
            </button>
            {/* 主题切换按钮 */}
            <ThemeSwitcher />
          </div>
        </div>

        {/* 同步进度条 */}
        {syncStatus.syncing && (
          <div className="max-w-[1920px] mx-auto px-6 pb-2">
            <div className="bg-accent-info/10 border border-accent-info/20 rounded-xl px-4 py-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  <span className="text-xs text-accent-info">{syncStatus.current_step}</span>
                </div>
                <span className="text-xs text-accent-info">
                  {syncStatus.total > 0 ? `${syncStatus.progress}/${syncStatus.total}` : '准备中...'}
                </span>
              </div>
              <div className="w-full h-1.5 bg-surface-2/50 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent-info rounded-full transition-all duration-300"
                  style={{ width: `${syncStatus.total > 0 ? (syncStatus.progress / syncStatus.total) * 100 : 5}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* 同步完成/错误提示 */}
        {!syncStatus.syncing && syncStatus.error && (
          <div className="max-w-[1920px] mx-auto px-6 pb-2">
            <div className="bg-danger/10 border border-danger/20 rounded-xl px-4 py-2 flex items-center gap-2">
              <AlertTriangle className="w-3 h-3" />
              <span className="text-xs text-danger">同步失败: {syncStatus.error}</span>
            </div>
          </div>
        )}

        {/* 路径设置面板 */}
        {showPathSettings && (
          <div className="max-w-[1920px] mx-auto px-6 pb-4">
            <div className="bg-surface-1/60 border border-border/50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <FolderTree className="w-3.5 h-3.5" />
                <span className="text-sm font-medium text-ink-inverse">Cursor 数据目录</span>
                <span className="text-xs text-ink-faint">（留空使用默认路径）</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="例如: ~/Library/Application Support/Cursor/User"
                    value={pathInput}
                    onChange={e => setPathInput(e.target.value)}
                    className="w-full px-4 py-2 bg-canvas/60 border border-border/50 rounded-lg text-sm text-ink-inverse placeholder-ink-faint focus:outline-none focus:border-violet-500/50 transition-all"
                  />
                  {/* 路径有效性提示 */}
                  {pathValid !== null && pathInput && (
                    <span className={`absolute right-3 top-1/2 -translate-y-1/2 text-sm ${pathValid ? 'text-success' : 'text-danger'}`}>
                      {pathValid ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
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
                    className="px-4 py-2 bg-surface-2/40 border border-border/50 rounded-lg text-sm text-ink-muted hover:text-ink-inverse transition-all"
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
          <div className="bg-danger/10 border border-danger/30 text-danger px-4 py-3 rounded-xl text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-danger hover:text-danger">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* 搜索结果模式 */}
      {isSearchMode ? (
        <div className="max-w-[1920px] mx-auto px-6 flex flex-col" style={{ height: showPathSettings ? 'calc(100vh - 170px)' : 'calc(100vh - 73px)' }}>
          {/* 搜索结果头部 */}
          <div className="flex items-center gap-2 py-4 flex-shrink-0">
            <h2 className="text-lg font-semibold text-ink-inverse">搜索结果</h2>
            <span className="text-sm text-ink-muted">
              (共 {searchTotal} 条，第 {searchPage}/{searchTotalPages} 页)
            </span>
            {loading.search && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          </div>
          {/* 搜索结果列表（可滚动） */}
          <div className="flex-1 overflow-y-auto space-y-3 pb-4">
            {searchResults.map((item, idx) => (
              <div
                key={`${item.composer_id}-${idx}`}
                onClick={() => handleSearchResultClick(item)}
                className="bg-canvas/60 border border-border/30 rounded-xl p-4 hover:border-violet-500/40 cursor-pointer transition-all group"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-violet-400 bg-violet-400/10 px-2 py-0.5 rounded-full">{item.project_name}</span>
                  {item.session_name && <span className="text-xs text-ink-faint">/ {item.session_name}</span>}
                  {item.match_type === 'title' ? (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">标题匹配</span>
                  ) : (
                    <Badge variant={item.message_type === 1 ? 'tint-info' : 'tint-success'} className="text-xs px-1.5 py-0.5 rounded">
                      {item.message_type === 1 ? '用户' : 'AI'}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-ink-muted line-clamp-3">{item.matched_text}</p>
              </div>
            ))}
            {!loading.search && searchResults.length === 0 && (
              <div className="text-center py-12 text-ink-faint">
                <Search className="w-8 h-8 mb-3 block opacity-30" />
                <p>未找到匹配结果</p>
              </div>
            )}
          </div>
          {/* 分页控件（固定在底部） */}
          {searchTotalPages > 1 && (
            <div className="flex items-center justify-center gap-2 py-3 border-t border-border/30 flex-shrink-0">
              <button
                onClick={() => doGlobalSearch(globalSearch, 1)}
                disabled={searchPage <= 1 || loading.search}
                className="px-3 py-1.5 text-xs rounded-lg bg-surface-1 text-ink-muted hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                首页
              </button>
              <button
                onClick={() => doGlobalSearch(globalSearch, searchPage - 1)}
                disabled={searchPage <= 1 || loading.search}
                className="px-3 py-1.5 text-xs rounded-lg bg-surface-1 text-ink-muted hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                <ChevronLeft className="w-3.5 h-3.5 mr-1" />上一页
              </button>
              <span className="text-xs text-ink-muted px-3">
                {searchPage} / {searchTotalPages}
              </span>
              <button
                onClick={() => doGlobalSearch(globalSearch, searchPage + 1)}
                disabled={searchPage >= searchTotalPages || loading.search}
                className="px-3 py-1.5 text-xs rounded-lg bg-surface-1 text-ink-muted hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                下一页<ChevronRight className="w-3.5 h-3.5 ml-1" />
              </button>
              <button
                onClick={() => doGlobalSearch(globalSearch, searchTotalPages)}
                disabled={searchPage >= searchTotalPages || loading.search}
                className="px-3 py-1.5 text-xs rounded-lg bg-surface-1 text-ink-muted hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                末页
              </button>
            </div>
          )}
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
          <div className="w-72 flex-shrink-0 border-r border-border/30 flex flex-col bg-canvas/40 absolute left-0 top-0 bottom-0 z-20">
            <div className="p-3 border-b border-border/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-3.5 h-3.5" />
                <span className="text-sm font-semibold text-ink-inverse">最近访问</span>
              </div>
              <button
                onClick={() => setShowRecentPanel(false)}
                className="text-ink-faint hover:text-ink-inverse transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {recentSessions.length === 0 ? (
                <div className="text-center py-8 text-ink-faint text-sm">
                  <History className="w-6 h-6 mb-2 block opacity-30" />
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
                    className="px-4 py-3 cursor-pointer border-b border-border/50 transition-all hover:bg-surface-1/50"
                  >
                    <div className="text-sm font-medium text-ink-inverse truncate">{session.session_name}</div>
                    <div className="text-xs text-ink-faint truncate mt-1">{session.project_name}</div>
                    <div className="text-xs text-violet-400 mt-1">{formatVisitedTime(session.visited_at)}</div>
                  </div>
                ))
              )}
            </div>
            {recentSessions.length > 0 && (
              <div className="p-3 border-t border-border/30">
                <button
                  onClick={() => {
                    if (confirm('确定清空最近访问记录吗？')) {
                      localStorage.removeItem('cursor_history_recent_sessions');
                      setRecentSessions([]);
                    }
                  }}
                  className="w-full py-2 text-xs text-ink-muted hover:text-ink-inverse transition-colors"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  清空记录
                </button>
              </div>
            )}
          </div>
          )}

          {/* 第一栏：项目列表（可折叠） */}
          {showProjectPanel && (
          <ResizablePanel defaultWidth={280} minWidth={220} maxWidth={450} storageKey="cursor-projects-width">
          <div className="w-full h-full border-r border-border/30 flex flex-col bg-canvas/40">
            <div className="pl-1 pr-2 py-3 border-b border-border/30">
              <div className="relative">
                <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="搜索项目..."
                  value={projectSearch}
                  onChange={e => setProjectSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 bg-surface-1/60 border border-border/50 rounded-lg text-xs text-ink-inverse placeholder-ink-faint focus:outline-none focus:border-violet-500/50 transition-all"
                />
              </div>
              {/* 多选模式切换和批量操作按钮 */}
              {projects.length > 0 && (
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => {
                      setProjectSelectMode(prev => !prev);
                      setSelectedProjectHashes(new Set());
                    }}
                    className={`px-2 py-1 text-xs rounded transition-all ${
                      projectSelectMode
                        ? 'bg-violet-600 text-ink-inverse'
                        : 'text-ink-muted hover:text-ink-inverse hover:bg-surface-2/50'
                    }`}
                    title={projectSelectMode ? '退出多选' : '多选模式'}
                  >
                    <CheckSquare className="w-4 h-4 mr-1" />
                    {projectSelectMode ? '退出多选' : '多选'}
                  </button>
                  {projectSelectMode && (
                    <>
                      <button
                        onClick={() => {
                          if (selectedProjectHashes.size === projects.length) {
                            setSelectedProjectHashes(new Set());
                          } else {
                            setSelectedProjectHashes(new Set(projects.map(p => p.workspace_hash)));
                          }
                        }}
                        className="px-2 py-1 text-xs text-ink-muted hover:text-ink-inverse hover:bg-surface-2/50 rounded transition-all"
                      >
                        {selectedProjectHashes.size === projects.length ? '取消全选' : '全选'}
                      </button>
                      <button
                        onClick={() => {
                          if (selectedProjectHashes.size > 0 && confirm(`确定删除选中的 ${selectedProjectHashes.size} 个项目吗？`)) {
                            batchDeleteProjects();
                          }
                        }}
                        disabled={selectedProjectHashes.size === 0}
                        className={`px-2 py-1 text-xs rounded transition-all ${
                          selectedProjectHashes.size > 0
                            ? 'text-danger hover:text-ink-inverse hover:bg-danger'
                            : 'text-ink-faint cursor-not-allowed'
                        }`}
                      >
                        <Trash2 className="w-4 h-4 mr-1" />
                        删除({selectedProjectHashes.size})
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading.projects ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-10 px-4">
                  <Database className="w-8 h-8 mb-3 block" />
                  <p className="text-sm text-ink-muted mb-1">暂无缓存数据</p>
                  <p className="text-xs text-ink-faint mb-4">请先同步 Cursor 对话数据到本地数据库</p>
                  <button
                    onClick={triggerSync}
                    className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-ink-inverse text-xs rounded-lg transition-all inline-flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    同步数据
                  </button>
                </div>
              ) : (
                projects.map(project => (
                  <div
                    key={project.workspace_hash}
                    onClick={() => {
                      if (projectSelectMode) {
                        toggleProjectSelect(project.workspace_hash);
                      } else {
                        handleProjectClick(project);
                      }
                    }}
                    className={`group pl-1 pr-2 py-3 cursor-pointer border-b border-border/50 transition-all hover:bg-surface-1/50 ${
                      selectedProject?.workspace_hash === project.workspace_hash
                        ? 'bg-violet-500/10'
                        : ''
                    } ${selectedProjectHashes.has(project.workspace_hash) ? 'bg-violet-500/5' : ''}`}
                  >
                    <div className="flex items-center gap-2">
                      {projectSelectMode && (
                        <input
                          type="checkbox"
                          checked={selectedProjectHashes.has(project.workspace_hash)}
                          onChange={() => toggleProjectSelect(project.workspace_hash)}
                          onClick={e => e.stopPropagation()}
                          className="w-3.5 h-3.5 rounded border-border text-violet-500 focus:ring-violet-500 focus:ring-offset-0 cursor-pointer"
                        />
                      )}
                      <Folder className="w-3.5 h-3.5" />
                      <span className="text-sm font-medium text-ink-inverse truncate flex-1">{project.project_name}</span>
                      {!projectSelectMode && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`确定删除项目「${project.project_name}」吗？`)) {
                              deleteCachedProject(project.workspace_hash);
                            }
                          }}
                          className="opacity-0 group-hover:opacity-100 text-ink-faint hover:text-danger transition-all p-1"
                          title="删除项目"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-ink-faint">
                      <MessageSquare className="w-2.5 h-2.5" />
                      <span>{project.session_count} 个会话</span>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="pl-1 pr-2 py-3 border-t border-border/30 text-xs text-ink-faint text-center">
              共 {projects.length} 个项目
            </div>
          </div>
          </ResizablePanel>
          )}

          {/* 第二栏：会话列表 */}
          <ResizablePanel defaultWidth={300} minWidth={250} maxWidth={500} storageKey="cursor-sessions-width">
          <div className="w-full h-full border-r border-border/30 flex flex-col bg-canvas/20">
            <div className="p-3 border-b border-border/30">
              {selectedProject ? (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <FolderOpen className="w-3.5 h-3.5" />
                    <span className="text-sm font-semibold text-ink-inverse truncate">{selectedProject.project_name}</span>
                  </div>
                  <div className="flex flex-col gap-2">
                    <div className="relative">
                      <Search className="w-3 h-3 absolute left-3 top-1/2 -translate-y-1/2" />
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
                        className="w-full pl-9 pr-3 py-2 bg-surface-1/60 border border-border/50 rounded-lg text-xs text-ink-inverse placeholder-ink-faint focus:outline-none focus:border-violet-500/50 transition-all"
                      />
                    </div>
                    <TagFilter onTagSelect={(tag) => {
                      setSelectedFilterTag(tag);
                      loadSessions(selectedProject.workspace_hash, sessionSearch || undefined, tag);
                    }} />
                  </div>
                </div>
              ) : (
                <p className="text-sm text-ink-faint text-center py-2">← 请选择一个项目</p>
              )}
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading.sessions ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
              ) : !selectedProject ? (
                <div className="text-center py-12 text-ink-faint">
                  <MessageSquare className="w-8 h-8 mb-3 block opacity-20" />
                  <p className="text-sm">选择项目查看会话</p>
                </div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-8 text-ink-faint text-sm">
                  <p>暂无会话</p>
                </div>
              ) : (
                <>
                  {/* 批量操作工具栏 */}
                  <div className="flex items-center justify-between px-4 py-2 border-b border-border/30 bg-surface-1/30">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectMode(!selectMode)}
                        className={`px-2 py-1 rounded text-xs transition-colors ${
                          selectMode
                            ? 'bg-violet-500 text-ink-inverse'
                            : 'bg-surface-2 text-ink-muted hover:bg-surface-3'
                        }`}
                      >
                        {selectMode ? '退出选择' : '多选'}
                      </button>
                      {selectMode && (
                        <button
                          onClick={toggleSelectAll}
                          className="px-2 py-1 bg-surface-2 text-ink-muted hover:bg-surface-3 rounded text-xs transition-colors"
                        >
                          {selectedSessionIds.length === sessions.length ? '取消全选' : '全选'}
                        </button>
                      )}
                    </div>
                    {selectMode && selectedSessionIds.length > 0 && (
                      <span className="text-xs text-ink-muted">
                        已选择 {selectedSessionIds.length} 个会话
                      </span>
                    )}
                  </div>

                  {/* 会话列表 */}
                  {sessions.map(session => (
                    <div
                      key={session.composer_id}
                      onClick={() => handleSessionClick(session)}
                      className={`group px-4 py-3 cursor-pointer border-b border-border/30 transition-all hover:bg-surface-1/40 flex items-start gap-3 ${
                        selectedSession?.composer_id === session.composer_id
                          ? 'bg-violet-500/10 border-l-2 border-l-violet-500'
                          : ''
                      } ${
                        selectMode && selectedSessionIds.includes(session.composer_id)
                          ? 'bg-accent-info/10'
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
                          className="mt-1 w-4 h-4 rounded border-border text-accent-info focus:ring-accent-info focus:ring-offset-0"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-ink-inverse truncate flex-1">{session.name || `会话 ${session.composer_id.slice(0, 8)}`}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (confirm(`确定删除会话「${session.name || session.composer_id.slice(0, 8)}」吗？`)) {
                                deleteCachedSession(session.composer_id);
                              }
                            }}
                            className="opacity-0 group-hover:opacity-100 text-ink-faint hover:text-danger transition-all p-1 flex-shrink-0"
                            title="删除会话"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                        <div className="mt-1 flex items-center gap-3 text-xs text-ink-faint">
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
          </ResizablePanel>


          {/* 第三栏：消息内容 */}
          <div className="flex-1 flex flex-col min-w-0 bg-canvas">
            {selectedSession ? (
              <>
                {/* 会话标题 */}
                <div className="p-4 border-b border-border/30 bg-canvas/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                        <MessageSquare className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-semibold text-ink-inverse truncate">{selectedSession.name || `会话 ${selectedSession.composer_id.slice(0, 8)}`}</h3>
                        <div className="flex items-center gap-3 text-xs text-ink-faint mt-1 flex-wrap">
                          <span>已加载 {messages.length} / {totalMessages} 条消息</span>
                          {selectedSession.created_at && (
                            <span><Clock className="w-4 h-4 mr-1" />{formatTime(selectedSession.created_at)}</span>
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
                            : 'bg-surface-2/50 text-ink-muted hover:text-amber-400'
                        }`}
                        title={isFavorite ? '取消收藏' : '收藏会话'}
                      >
                        <Star className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
                      </button>
                      {/* 导出按钮 */}
                      <button
                        onClick={() => setShowExportDialog(true)}
                        className="px-3 py-1.5 bg-violet-500/20 border border-violet-500/40 rounded-lg text-xs text-violet-400 hover:bg-violet-500/30 transition-all flex items-center gap-1.5"
                        title="导出会话"
                      >
                        <Download className="w-4 h-4" />
                        <span>导出</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 消息列表（普通滚动，向上加载历史） */}
                <div ref={messageListRef} className="flex-1 overflow-y-auto p-6 space-y-4">
                  {loading.messages ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-5 h-5 animate-spin" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="text-center py-12 text-ink-faint">
                      <Inbox className="w-8 h-8 mb-3 block opacity-30" />
                      <p>暂无消息</p>
                    </div>
                  ) : (
                    <>
                      {/* 顶部加载历史消息提示 */}
                      {!hasMore && messages.length > 0 && (
                        <div className="text-center py-3 text-xs text-ink-faint">
                          — 已加载全部 {totalMessages} 条消息 —
                        </div>
                      )}
                      {!loadingMore && hasMore && (
                        <div className="text-center py-3">
                          <button
                            onClick={loadMoreMessages}
                            className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
                          >
                            <ChevronUp className="w-4 h-4 mr-1" />
                            向上滚动或点击加载更早消息（还有 {totalMessages - messages.length} 条）
                          </button>
                        </div>
                      )}
                      {loadingMore && (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          <span className="text-xs text-ink-faint">加载历史消息...</span>
                        </div>
                      )}
                      {messages.map((msg, index) => (
                        <MessageItem key={msg.message_id || index} msg={msg} />
                      ))}
                    </>
                  )}
                </div>
              </>
            ) : (
              /* 空状态 */
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 rounded-2xl bg-surface-1/50 flex items-center justify-center mx-auto mb-4">
                    <History className="w-8 h-8" />
                  </div>
                  <h3 className="text-lg font-semibold text-ink-muted mb-2">选择一个会话查看内容</h3>
                  <p className="text-sm text-ink-faint">从左侧选择项目和会话，或使用顶部搜索</p>
                </div>
              </div>
            )}
          </div>

        </div>
      )}

      {/* 导出对话框 */}
      {showExportDialog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-surface-1 border border-border rounded-2xl p-6 w-full max-w-md shadow-lg">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <Download className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-ink-inverse">导出会话</h3>
                <p className="text-xs text-ink-muted">选择导出格式和选项</p>
              </div>
            </div>

            {/* 导出格式选择 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-ink-muted mb-3">导出格式</label>
              <div className="grid grid-cols-3 gap-3">
                {(['markdown', 'json', 'html'] as const).map((format) => (
                  <button
                    key={format}
                    onClick={() => setExportFormat(format)}
                    className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                      exportFormat === format
                        ? 'bg-violet-500/20 border-violet-500/50 text-violet-400'
                        : 'bg-surface-2/30 border-border/50 text-ink-muted hover:border-border'
                    }`}
                  >
                    {format === 'markdown' && <><FileText className="w-4 h-4 mr-2" />MD</>}
                    {format === 'json' && <><FileCode className="w-4 h-4 mr-2" />JSON</>}
                    {format === 'html' && <><FileCode className="w-4 h-4 mr-2" />HTML</>}
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
                  className="w-4 h-4 rounded border-border text-violet-500 focus:ring-violet-500/50 bg-surface-2"
                />
                <span className="text-sm text-ink-muted">包含代码块</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exportOptions.includeTimestamps}
                  onChange={e => setExportOptions(prev => ({ ...prev, includeTimestamps: e.target.checked }))}
                  className="w-4 h-4 rounded border-border text-violet-500 focus:ring-violet-500/50 bg-surface-2"
                />
                <span className="text-sm text-ink-muted">包含序号</span>
              </label>
              {exportFormat === 'html' && (
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeAvatars}
                    onChange={e => setExportOptions(prev => ({ ...prev, includeAvatars: e.target.checked }))}
                    className="w-4 h-4 rounded border-border text-violet-500 focus:ring-violet-500/50 bg-surface-2"
                  />
                  <span className="text-sm text-ink-muted">包含头像图标 (HTML)</span>
                </label>
              )}
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowExportDialog(false)}
                disabled={exportLoading}
                className="flex-1 px-4 py-2.5 bg-surface-2 hover:bg-surface-3 disabled:bg-surface-2/50 text-ink-inverse rounded-xl transition-all text-sm font-medium"
              >
                取消
              </button>
              <button
                onClick={handleExport}
                disabled={exportLoading}
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 disabled:opacity-50 text-ink-inverse rounded-xl transition-all text-sm font-medium flex items-center justify-center gap-2"
              >
                {exportLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>导出中...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
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
    <div className="w-72 flex-shrink-0 border-r border-border/30 flex flex-col bg-canvas/40 absolute left-0 top-0 bottom-0 z-20">
      <div className="p-3 border-b border-border/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Star className="w-3.5 h-3.5" />
          <span className="text-sm font-semibold text-ink-inverse">收藏夹</span>
        </div>
        <button
          onClick={onClose}
          className="text-ink-faint hover:text-ink-inverse transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin" />
          </div>
        ) : favorites.length === 0 ? (
          <div className="text-center py-8 text-ink-faint text-sm">
            <Star className="w-6 h-6 mb-2 block opacity-30" />
            <p>暂无收藏</p>
          </div>
        ) : (
          favorites.map((fav, idx) => (
            <div
              key={idx}
              onClick={() => onSelectSession(fav.composer_id, fav.workspace_hash || '', fav.session_name || '', fav.project_name || '')}
              className="px-4 py-3 cursor-pointer border-b border-border/50 transition-all hover:bg-surface-1/50"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-amber-400 truncate">{fav.session_name || '未命名会话'}</div>
                  <div className="text-xs text-ink-faint truncate mt-1">{fav.project_name || '未知项目'}</div>
                  <div className="text-xs text-ink-faint mt-1">{new Date(fav.created_at).toLocaleDateString('zh-CN')}</div>
                </div>
                <button
                  onClick={(e) => handleDelete(fav.composer_id, e)}
                  className="text-ink-faint hover:text-danger transition-colors p-1"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="p-3 border-t border-border/30 text-xs text-ink-faint text-center">
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
    <div className="w-96 flex-shrink-0 border-r border-border/30 flex flex-col bg-canvas/40 absolute left-0 top-0 bottom-0 z-20 overflow-y-auto">
      <div className="p-3 border-b border-border/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-3.5 h-3.5" />
          <span className="text-sm font-semibold text-ink-inverse">数据统计</span>
        </div>
        <button
          onClick={onClose}
          className="text-ink-faint hover:text-ink-inverse transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin" />
          </div>
        ) : (
          <>
            {/* 概览卡片 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-1/60 border border-border/50 rounded-xl p-3">
                <div className="text-xs text-ink-muted mb-1">总会话</div>
                <div className="text-2xl font-bold text-ink-inverse">{stats.overview.total_sessions}</div>
              </div>
              <div className="bg-surface-1/60 border border-border/50 rounded-xl p-3">
                <div className="text-xs text-ink-muted mb-1">总消息</div>
                <div className="text-2xl font-bold text-ink-inverse">{stats.overview.total_messages}</div>
              </div>
              <div className="bg-surface-1/60 border border-border/50 rounded-xl p-3">
                <div className="text-xs text-ink-muted mb-1">今日会话</div>
                <div className="text-2xl font-bold text-success">{stats.overview.today_sessions}</div>
              </div>
              <div className="bg-surface-1/60 border border-border/50 rounded-xl p-3">
                <div className="text-xs text-ink-muted mb-1">今日消息</div>
                <div className="text-2xl font-bold text-success">{stats.overview.today_messages}</div>
              </div>
            </div>

            {/* 趋势图表 */}
            <div className="bg-surface-1/60 border border-border/50 rounded-xl p-3">
              <div className="text-xs text-ink-muted mb-3">近 7 天趋势</div>
              <div className="space-y-2">
                {stats.trends.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <div className="text-xs text-ink-faint w-12">{item.date.slice(5)}</div>
                    <div className="flex-1 h-6 bg-surface-2/30 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full"
                        style={{ width: `${Math.max(5, (item.sessions / Math.max(...stats.trends.map(t => t.sessions))) * 100)}%` }}
                      />
                    </div>
                    <div className="text-xs text-ink-muted w-8 text-right">{item.sessions}</div>
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
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

  /** 虚拟滚动：消息项渲染器 */
  const MessageRow = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const msg = messages[index];
    if (!msg) return null;

    return (
      <div style={style} className={`flex group ${msg.message_type === 1 ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
          msg.message_type === 1
            ? 'bg-violet-500/20 border border-violet-500/20'
            : 'bg-slate-800/60 border border-slate-700/30'
        }`}>
          {/* 消息头和复制按钮 */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <i className={`fas ${msg.message_type === 1 ? 'fa-user text-violet-400' : 'fa-robot text-emerald-400'} text-xs`} />
              <span className={`text-xs font-medium ${msg.message_type === 1 ? 'text-violet-400' : 'text-emerald-400'}`}>
                {msg.message_type === 1 ? '用户' : 'AI 助手'}
              </span>
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
              {msg.message_type === 0 && (
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
          {msg.message_type === 1 ? (
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
  }, [messages, handleCopyMessage, handleCopyCodeBlock]);

  // 初始加载项目
  useEffect(() => { loadProjects(); }, [loadProjects]);

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
    setSelectedSession(session);
    loadMessages(session.composer_id, session.name || undefined);
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
            {/* 切换项目列表面板 */}
            <button
              onClick={() => setShowProjectPanel(prev => !prev)}
              className="text-slate-400 hover:text-white transition-colors"
              title={showProjectPanel ? '隐藏项目列表' : '显示项目列表'}
            >
              <i className={`fas ${showProjectPanel ? 'fa-indent' : 'fa-outdent'} text-lg`} />
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
                  <div className="relative">
                    <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs" />
                    <input
                      type="text"
                      placeholder="搜索会话..."
                      value={sessionSearch}
                      onChange={e => setSessionSearch(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 transition-all"
                    />
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
                sessions.map(session => (
                  <div
                    key={session.composer_id}
                    onClick={() => handleSessionClick(session)}
                    className={`px-4 py-3 cursor-pointer border-b border-slate-800/30 transition-all hover:bg-slate-800/40 ${
                      selectedSession?.composer_id === session.composer_id
                        ? 'bg-violet-500/10 border-l-2 border-l-violet-500'
                        : ''
                    }`}
                  >
                    <div className="text-sm font-medium text-white truncate">{session.name || `会话 ${session.composer_id.slice(0, 8)}`}</div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                      {session.created_at && <span>{formatTime(session.created_at)}</span>}
                      <span>{session.message_count} 条消息</span>
                    </div>
                  </div>
                ))
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
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                        <i className="fas fa-comments text-violet-400 text-sm" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-semibold text-white truncate">{selectedSession.name || `会话 ${selectedSession.composer_id.slice(0, 8)}`}</h3>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span>已加载 {messages.length} / {totalMessages} 条消息</span>
                          {selectedSession.created_at && (
                            <span><i className="fas fa-clock mr-1" />{formatTime(selectedSession.created_at)}</span>
                          )}
                        </div>
                      </div>
                    </div>
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
    </div>
  );
}
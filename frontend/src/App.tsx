import { useState, useEffect, useContext, useRef, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useOutletContext, useLocation } from 'react-router-dom';
import Header from './components/Header/Header'; // Keep import for types if needed, but remove usage
import Hero from './components/Hero/Hero';
import Layout from './components/Layout/Layout';
import AdminLayout from './components/Admin/AdminLayout';
import ToolManagement from './components/Admin/ToolManagement';
import SystemSettingsPage from './components/Admin/SystemSettings';
import Dashboard from './components/Admin/Dashboard';
import UserManagement from './components/Admin/UserManagement';
import OssManagement from './components/Admin/OssManagement';
import LLMConfigsPage from './components/Admin/LLMConfigsPage';
import CourseManagement from './components/Admin/CourseManagement';
import CourseDetail from './components/Admin/CourseDetail';
import AgentManagement from './components/Admin/AgentManagement';
import ConversationManagement from './components/Admin/ConversationManagement';
import ContactMessagesManagement from './components/Admin/ContactMessagesManagement';
import CrossShareMain from './components/Tools/CrossShare/CrossShareMain';
import { WorkspacePage } from './components/Workspace/WorkspacePage';
import OpenClawManagement from './components/Admin/OpenClawManagement';
import ImageGenerationAdmin from './components/Admin/ImageGeneration';
import CourseLearnPage from './pages/CourseLearnPage';
import CoursesPage from './pages/CoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import TechContentsPage from './pages/TechContentsPage';
import TechContentDetailPage from './pages/TechContentDetailPage';
import AccountSettings from './pages/AccountSettings';
import DevComponentsPage from './pages/DevComponentsPage';
import { AuthProvider, AuthContext, useAuth } from './stores/authStore';
import { useCategory } from './hooks/useCategory';
import { fetchTools, searchTools, fetchToolsByCategory, loadToolsByCategory, fetchCategories } from './services/api';
import { Tool } from './types';
import { useI18n } from './i18n';
import { I18nProvider } from './i18n/I18nProvider';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from './contexts/ToastContext';
import { ErrorBoundary } from './components/Common/ErrorMessages';
import LoginModal from './components/Common/LoginModal';
import LoginForm from './components/Auth/LoginForm';
import RegisterForm from './components/Auth/RegisterForm';
import { registerAuthFailureHandler } from './api/http';
import { useLoginModalStore } from './stores/loginModalStore';

// ============================================================
// 工具组件懒加载 — 避免全部打入首屏 JS bundle
// ============================================================
const ImageDownloader = lazy(() => import('./components/Tools/ImageDownloader'));
const VideoDownloader = lazy(() => import('./components/Tools/VideoDownloader'));
const JsonFormatter = lazy(() => import('./components/Tools/JsonFormatter'));
const Calendar = lazy(() => import('./components/Tools/Calendar'));
const AIAssistant = lazy(() => import('./components/Tools/AIAssistant'));
const KeyGenerator = lazy(() => import('./components/Tools/KeyGenerator'));
const MarkdownEditorTool = lazy(() => import('./components/Tools/MarkdownEditorTool'));
const MarkItDownConverter = lazy(() => import('./components/Tools/MarkItDownConverter'));
const OCRTool = lazy(() => import('./components/Tools/OCR/OCRTool'));
const ASRTool = lazy(() => import('./components/Tools/ASR/ASRTool'));
const DatabaseTool = lazy(() => import('./components/Tools/DatabaseTool/DatabaseTool'));
const RedisTool = lazy(() => import('./components/Tools/RedisTool/RedisTool'));
const SSHTool = lazy(() => import('./components/Tools/SSHTool/SSHTool'));
const ProductManagerAgent = lazy(() => import('./components/Tools/ProductManagerAgent'));
const LearningSharePlatform = lazy(() => import('./components/Tools/LearningSharePlatform'));
const OpenSpecCourse = lazy(() => import('./components/Tools/OpenSpecCourse'));
const CursorHistory = lazy(() => import('./components/Tools/CursorHistory/CursorHistory'));
const HttpApiClient = lazy(() => import('./components/Tools/HttpApiClient/HttpApiClient'));
const SystemMonitor = lazy(() => import('./components/Tools/SystemMonitor'));
const TokenUsage = lazy(() => import('./components/Tools/TokenUsage'));
const OpenClawChat = lazy(() => import('./components/Tools/OpenClawChat/OpenClawChat'));
const K8sTool = lazy(() => import('./components/Tools/K8sTool/K8sTool'));
const ImageGeneration = lazy(() => import('./components/Tools/ImageGeneration'));

// React Query 客户端实例（进程级别单例）
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // K8s 工具页面相关的合理默认值
      staleTime: 30_000,       // 30s 内视为新鲜数据
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

interface LayoutContext {
  searchValue: string;
  debouncedValue: string;
  handleSearchChange: (value: string) => void;
  handleSearch: () => void;
}

function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useContext(AuthContext);
  const { t } = useI18n();
  const [showRegister, setShowRegister] = useState(false);

  // 已登录直接回首页
  if (isAuthenticated) {
    navigate('/');
    return null;
  }

  const handleSuccess = () => {
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      {showRegister ? (
        <RegisterForm
          onSuccess={handleSuccess}
          onSwitchToLogin={() => setShowRegister(false)}
        />
      ) : (
        <LoginForm
          onSuccess={handleSuccess}
          onSwitchToRegister={() => setShowRegister(true)}
        />
      )}
    </div>
  );
}

function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [filteredTools, setFilteredTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<string[]>(["全部工具"]);
  const { t } = useI18n();
  const { isAuthenticated } = useContext(AuthContext);
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);
  const initialLoadDone = useRef(false);

  const { activeCategory, handleCategoryChange } = useCategory();
  const { debouncedValue, handleSearchChange } = useOutletContext<LayoutContext>();

  // Sync URL query with search state
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get('q');
    if (q && q !== debouncedValue) {
       handleSearchChange(q);
    }
  }, [location.search]);

  const loadCategories = async () => {
    try {
      const cats = await fetchCategories();
      const catNames = ["全部工具", ...cats.map(c => c.name)];
      setCategories(Array.from(new Set(catNames)));
    } catch (e) {
      console.error("Failed to load categories", e);
      setError(t.errors.categoryLoadFailed);
    }
  };

  const loadTools = async () => {
    try {
      setLoading(true);
      const data = await fetchTools('pc');
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      setError(t.errors.toolLoadFailed);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadToolsDataByCategory = async (category: string) => {
    try {
        setLoading(true);
        const data = await loadToolsByCategory(category, 'pc');
        setFilteredTools(data);
        setError(null);
    } catch (err) {
        setError(t.errors.toolLoadFailed);
        console.error(err);
    } finally {
        setLoading(false);
    }
  };

  const searchToolsData = async (query: string) => {
    try {
      setLoading(true);
      const data = await searchTools(query);
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      setError(t.errors.toolSearchFailed);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 首次挂载：加载分类 + 工具（仅一次）
  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    loadCategories();
    loadTools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 根据分类筛选（排除初始挂载，由上面首次 useEffect 处理）
  useEffect(() => {
    if (!initialLoadDone.current) return;
    if (debouncedValue) return; // 搜索时由搜索 effect 处理
    if (activeCategory === "全部工具") {
      loadTools();
    } else {
      loadToolsDataByCategory(activeCategory);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCategory]);

  // 根据搜索关键词筛选
  useEffect(() => {
    if (!initialLoadDone.current) return;
    if (debouncedValue) {
      searchToolsData(debouncedValue);
    } else if (activeCategory === "全部工具") {
      loadTools();
    } else {
      loadToolsDataByCategory(activeCategory);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedValue]);

  // 处理工具点击 - 使用路由导航
  const handleToolClick = (toolId: string) => {
    // 登录拦截：直接弹出登录弹框（登录成功后用户可再次点击进入）
    const tool = filteredTools.find(t => t.id === toolId);
    if (tool?.require_login && !isAuthenticated) {
      openLoginModal();
      return;
    }

    // 跳转到工作区，由工作区 Store 管理标签（使用次数由 workspaceStore.addTab 统一上报，此处不再重复上报）
    navigate('/workspace', { state: { openToolId: toolId } });
  };

  return (
    <div className="container mx-auto px-6 py-8">
      {error && (
        <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg mb-8">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16">
          <div className="text-xl text-ink-faint">{t.common.loading}</div>
        </div>
      ) : (
        <>
          <Hero
            activeCategory={activeCategory}
            onCategoryChange={handleCategoryChange}
            tools={filteredTools}
            onToolClick={handleToolClick}
            categories={categories}
          />
        </>
      )}
    </div>
  );
}

function GlobalAuthHandler() {
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);
  const { markUnauthorized } = useAuth();
  // 用 ref 保存最新函数引用，避免空依赖 useEffect 捕获过期闭包
  const markUnauthorizedRef = useRef(markUnauthorized);
  markUnauthorizedRef.current = markUnauthorized;
  const openLoginModalRef = useRef(openLoginModal);
  openLoginModalRef.current = openLoginModal;

  useEffect(() => {
    registerAuthFailureHandler(() => {
      // 401：清除失效 token 与用户态（仅已登录时递增 authVersion）
      markUnauthorizedRef.current();
      // 打开登录弹框（store 幂等：已打开时不重复触发）
      openLoginModalRef.current();
    });
  }, []);

  return <LoginModal />;
}

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <ToastProvider>
            <BrowserRouter>
              <GlobalAuthHandler />
              <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/workspace" element={<WorkspacePage />} />
              <Route path="/account-settings" element={<AccountSettings />} />
              <Route path="/courses" element={<CoursesPage />} />
              <Route path="/courses/:slug" element={<CourseDetailPage />} />
              <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
              <Route path="/tech-contents" element={<TechContentsPage />} />
              <Route path="/tech-contents/:slug" element={<TechContentDetailPage />} />
              <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
              {/* 工具页面：React.lazy 按需加载，Suspense fallback 统一处理加载态 */}
              <Route path="/tools/*" element={
                <Suspense fallback={<div className="min-h-screen bg-canvas flex items-center justify-center"><div className="text-xl text-ink-muted">加载中...</div></div>}>
                  <Routes>
                    <Route path="image-downloader" element={<ImageDownloader />} />
                    <Route path="video-downloader" element={<VideoDownloader />} />
                    <Route path="json-formatter" element={<JsonFormatter />} />
                    <Route path="calendar" element={<Calendar />} />
                    <Route path="ai-assistant" element={<AIAssistant />} />
                    <Route path="key-generator" element={<KeyGenerator />} />
                    <Route path="markdown-editor" element={<MarkdownEditorTool />} />
                    <Route path="markitdown-converter" element={<MarkItDownConverter />} />
                    <Route path="ocr" element={<OCRTool />} />
                    <Route path="asr" element={<ASRTool />} />
                    <Route path="database-tool" element={<DatabaseTool />} />
                    <Route path="redis-tool" element={<RedisTool />} />
                    <Route path="ssh-tool" element={<SSHTool />} />
                    <Route path="product-manager" element={<ProductManagerAgent />} />
                    <Route path="product-manager/:conversationId" element={<ProductManagerAgent />} />
                    <Route path="learning-share" element={<LearningSharePlatform />} />
                    <Route path="openspec-course" element={<OpenSpecCourse />} />
                    <Route path="cross-share" element={<CrossShareMain />} />
                    <Route path="cursor-history" element={<CursorHistory />} />
                    <Route path="http-api-client" element={<HttpApiClient />} />
                    <Route path="system-monitor" element={<SystemMonitor />} />
                    <Route path="token-usage" element={<TokenUsage />} />
                    <Route path="openclaw" element={<OpenClawChat />} />
                    <Route path="k8s-tool" element={<ErrorBoundary><K8sTool /></ErrorBoundary>} />
                    <Route path="image-generation" element={<ImageGeneration />} />
                  </Routes>
                </Suspense>
              } />
            </Route>

            {/* Admin Routes */}
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="tools" element={<ToolManagement />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="contact-messages" element={<ContactMessagesManagement />} />
              <Route path="conversations" element={<ConversationManagement />} />
              <Route path="agents" element={<AgentManagement />} />
              <Route path="settings" element={<SystemSettingsPage />} />
              <Route path="oss" element={<OssManagement />} />
              <Route path="llm-configs" element={<LLMConfigsPage />} />
              <Route path="course" element={<CourseManagement />} />
              <Route path="course/:id" element={<CourseDetail />} />
              <Route path="openclaw" element={<OpenClawManagement />} />
              <Route path="image-generation" element={<ImageGenerationAdmin />} />
            </Route>

            {/* 仅开发环境：设计系统 token 验证页 */}
            {import.meta.env.DEV && (
              <Route path="/dev/components" element={<DevComponentsPage />} />
            )}
          </Routes>
        </BrowserRouter>
        </ToastProvider>
        </I18nProvider>
      </QueryClientProvider>
    </AuthProvider>
  );
}

export default App;

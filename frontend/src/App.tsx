import { useState, useEffect } from 'react';
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
import ImageDownloader from './components/Tools/ImageDownloader';
import VideoDownloader from './components/Tools/VideoDownloader';
import JsonFormatter from './components/Tools/JsonFormatter';
import Calendar from './components/Tools/Calendar';
import AIAssistant from './components/Tools/AIAssistant';
import KeyGenerator from './components/Tools/KeyGenerator';
import MarkdownEditorTool from './components/Tools/MarkdownEditorTool';
import MarkItDownConverter from './components/Tools/MarkItDownConverter';
import OCRTool from './components/Tools/OCR/OCRTool';
import ASRTool from './components/Tools/ASR/ASRTool';
import DatabaseTool from './components/Tools/DatabaseTool/DatabaseTool';
import RedisTool from './components/Tools/RedisTool/RedisTool';
import SSHTool from './components/Tools/SSHTool/SSHTool';
import ProductManagerAgent from './components/Tools/ProductManagerAgent';
import LearningSharePlatform from './components/Tools/LearningSharePlatform';
import OpenSpecCourse from './components/Tools/OpenSpecCourse';
import CrossShareMain from './components/Tools/CrossShare/CrossShareMain';
import CursorHistory from './components/Tools/CursorHistory/CursorHistory';
import HttpApiClient from './components/Tools/HttpApiClient/HttpApiClient';
import CourseLearnPage from './pages/CourseLearnPage';
import CoursesPage from './pages/CoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import TechContentsPage from './pages/TechContentsPage';
import TechContentDetailPage from './pages/TechContentDetailPage';
import AccountSettings from './pages/AccountSettings';
import { AuthProvider } from './stores/authStore';
import { useCategory } from './hooks/useCategory';
import { fetchTools, searchTools, fetchToolsByCategory, loadToolsByCategory, fetchCategories } from './services/api';
import { Tool } from './types';
import { useI18n, interpolate } from './i18n';
import { I18nProvider } from './i18n/I18nProvider';
import { ToastProvider } from './contexts/ToastContext';

interface LayoutContext {
  searchValue: string;
  debouncedValue: string;
  handleSearchChange: (value: string) => void;
  handleSearch: () => void;
}

import { recordToolVisit } from './api/adminApi';

function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [filteredTools, setFilteredTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<string[]>(["全部工具"]);
  const { t } = useI18n();

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

  // 初始加载所有工具
  useEffect(() => {
    loadCategories();
    loadTools();
  }, []);

  const loadCategories = async () => {
    try {
      const cats = await fetchCategories();
      const catNames = ["全部工具", ...cats.map(c => c.name)];
      setCategories(Array.from(new Set(catNames)));
    } catch (e) {
      console.error("Failed to load categories", e);
      // Fallback to default if failed? Or keep "全部工具"
    }
  };


  const loadTools = async () => {
    try {
      setLoading(true);
      const data = await fetchTools();
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
        const data = await loadToolsByCategory(category);
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

  // 根据分类筛选
  useEffect(() => {
    if (activeCategory === "全部工具") {
      loadTools();
    } else {
      loadToolsDataByCategory(activeCategory);
    }
  }, [activeCategory]);

  // 根据搜索关键词筛选
  useEffect(() => {
    if (debouncedValue) {
      searchToolsData(debouncedValue);
    } else if (activeCategory === "全部工具") {
      loadTools();
    } else {
      loadToolsDataByCategory(activeCategory);
    }
  }, [debouncedValue]);

  // 处理工具点击 - 使用路由导航
  const handleToolClick = async (toolId: string) => {
    // Record tool visit
    try {
      const tool = filteredTools.find(t => t.id === toolId);
      if (tool) {
        await recordToolVisit(toolId, tool.title);
      }
    } catch (e) {
      console.error("Failed to record tool visit", e);
    }

    const toolRoutes: Record<string, string> = {
      'image-downloader': '/tools/image-downloader',
      'video-downloader': '/tools/video-downloader',
      'json-formatter': '/tools/json-formatter',
      'calendar': '/tools/calendar',
      'ai-assistant': '/tools/ai-assistant',
      'key-generator': '/tools/key-generator',
      'markdown-editor': '/tools/markdown-editor',
      'markitdown-converter': '/tools/markitdown-converter',
      'ocr-tool': '/tools/ocr',
      'asr-tool': '/tools/asr',
      'database-tool': '/tools/database-tool',
      'redis-tool': '/tools/redis-tool',
      'ssh-tool': '/tools/ssh-tool',
      'product-manager': '/tools/product-manager',
      'learning-share': '/tools/learning-share',
      'cross-share': '/tools/cross-share',
      'course-platform': '/courses',
      'cursor-history': '/tools/cursor-history',
      'http-api-client': '/tools/http-api-client',
    };

    const route = toolRoutes[toolId];
    if (route) {
      navigate(route);
    } else {
      alert(interpolate(t.errors.toolNotImplemented, { toolId }));
    }
  };

  return (
    <div className="container mx-auto px-6 py-8">
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded-lg mb-8">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16">
          <div className="text-xl text-slate-400">{t.common.loading}</div>
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

function App() {
  return (
    <AuthProvider>
      <I18nProvider>
        <ToastProvider>
          <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/account-settings" element={<AccountSettings />} />
              <Route path="/courses" element={<CoursesPage />} />
              <Route path="/courses/:slug" element={<CourseDetailPage />} />
              <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
              <Route path="/tech-contents" element={<TechContentsPage />} />
              <Route path="/tech-contents/:slug" element={<TechContentDetailPage />} />
              <Route path="/tools/image-downloader" element={<ImageDownloader />} />
              <Route path="/tools/video-downloader" element={<VideoDownloader />} />
              <Route path="/tools/json-formatter" element={<JsonFormatter />} />
              <Route path="/tools/calendar" element={<Calendar />} />
              <Route path="/tools/ai-assistant" element={<AIAssistant />} />
              <Route path="/tools/key-generator" element={<KeyGenerator />} />
              <Route path="/tools/markdown-editor" element={<MarkdownEditorTool />} />
              <Route path="/tools/markitdown-converter" element={<MarkItDownConverter />} />
              <Route path="/tools/ocr" element={<OCRTool />} />
              <Route path="/tools/asr" element={<ASRTool />} />
              <Route path="/tools/database-tool" element={<DatabaseTool />} />
              <Route path="/tools/redis-tool" element={<RedisTool />} />
              <Route path="/tools/ssh-tool" element={<SSHTool />} />
              <Route path="/tools/product-manager" element={<ProductManagerAgent />} />
              <Route path="/tools/product-manager/:conversationId" element={<ProductManagerAgent />} />
              <Route path="/tools/learning-share" element={<LearningSharePlatform />} />
              <Route path="/tools/openspec-course" element={<OpenSpecCourse />} />
              <Route path="/courses/:slug/learn" element={<CourseLearnPage />} />
              <Route path="/tools/cross-share" element={<CrossShareMain />} />
              <Route path="/tools/cursor-history" element={<CursorHistory />} />
              <Route path="/tools/http-api-client" element={<HttpApiClient />} />
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
            </Route>
          </Routes>
        </BrowserRouter>
        </ToastProvider>
      </I18nProvider>
    </AuthProvider>
  );
}

export default App;

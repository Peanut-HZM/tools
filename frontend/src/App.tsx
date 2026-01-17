import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Header from './components/Header/Header';
import Hero from './components/Hero/Hero';
import Features from './components/Features/Features';
import Statistics from './components/Statistics/Statistics';
import Recommendations from './components/Recommendations/Recommendations';
import Footer from './components/Footer/Footer';
import ImageDownloader from './components/Tools/ImageDownloader';
import VideoDownloader from './components/Tools/VideoDownloader';
import JsonFormatter from './components/Tools/JsonFormatter';
import Calendar from './components/Tools/Calendar';
import AIAssistant from './components/Tools/AIAssistant';
import KeyGenerator from './components/Tools/KeyGenerator';
import MarkdownEditorTool from './components/Tools/MarkdownEditorTool';
import { AuthProvider } from './stores/authStore';
import { useCategory } from './hooks/useCategory';
import { useSearch } from './hooks/useSearch';
import { fetchTools, searchTools, fetchToolsByCategory } from './services/api';
import { Tool } from './types';

function HomePage() {
  const navigate = useNavigate();
  const [filteredTools, setFilteredTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { activeCategory, handleCategoryChange } = useCategory();
  const { searchValue, debouncedValue, handleSearchChange, handleSearch } = useSearch();

  // 初始加载所有工具
  useEffect(() => {
    loadTools();
  }, []);

  // 根据分类筛选
  useEffect(() => {
    if (activeCategory === "全部工具") {
      loadTools();
    } else {
      loadToolsByCategory(activeCategory);
    }
  }, [activeCategory]);

  // 根据搜索关键词筛选
  useEffect(() => {
    if (debouncedValue) {
      searchToolsData(debouncedValue);
    } else if (activeCategory === "全部工具") {
      loadTools();
    } else {
      loadToolsByCategory(activeCategory);
    }
  }, [debouncedValue]);

  const loadTools = async () => {
    try {
      setLoading(true);
      const data = await fetchTools();
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      setError('加载工具失败，请稍后重试');
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
      setError('搜索失败，请稍后重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadToolsByCategory = async (category: string) => {
    try {
      setLoading(true);
      const data = await fetchToolsByCategory(category);
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      setError('加载分类工具失败，请稍后重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 处理工具点击 - 使用路由导航
  const handleToolClick = (toolId: string) => {
    const toolRoutes: Record<string, string> = {
      'image-downloader': '/tools/image-downloader',
      'video-downloader': '/tools/video-downloader',
      'json-formatter': '/tools/json-formatter',
      'calendar': '/tools/calendar',
      'ai-assistant': '/tools/ai-assistant',
      'key-generator': '/tools/key-generator',
      'markdown-editor': '/tools/markdown-editor',
    };

    const route = toolRoutes[toolId];
    if (route) {
      navigate(route);
    } else {
      alert(`工具 ${toolId} 暂未实现`);
    }
  };

  return (
    <div className="bg-slate-900 text-slate-100">
      <Header
        searchValue={searchValue}
        onSearchChange={handleSearchChange}
        onSearch={handleSearch}
      />
      
      <main className="container mx-auto px-6 py-8">
        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded-lg mb-8">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-16">
            <div className="text-xl text-slate-400">加载中...</div>
          </div>
        ) : (
          <>
            <Hero
              activeCategory={activeCategory}
              onCategoryChange={handleCategoryChange}
              tools={filteredTools}
              onToolClick={handleToolClick}
            />
            <Features />
            <Statistics />
            <Recommendations />
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/tools/image-downloader" element={<ImageDownloader />} />
          <Route path="/tools/video-downloader" element={<VideoDownloader />} />
          <Route path="/tools/json-formatter" element={<JsonFormatter />} />
          <Route path="/tools/calendar" element={<Calendar />} />
          <Route path="/tools/ai-assistant" element={<AIAssistant />} />
          <Route path="/tools/key-generator" element={<KeyGenerator />} />
          <Route path="/tools/markdown-editor" element={<MarkdownEditorTool />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

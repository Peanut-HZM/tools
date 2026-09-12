import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Inbox } from 'lucide-react';
import TechContentCard from '../components/TechContent/TechContentCard.tsx';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { useI18n } from '../i18n/index.ts';
import { API_BASE_URL } from '../config/api.ts';

interface TechContent {
  id: number;
  slug: string;
  coverImage?: string;
  contentType: 'analysis' | 'sharing' | 'case_study';
  contentTypeLabel?: string;
  tags?: string[];
  title: string;
  description: string;
  author?: string;
  readingTime: number;
  publishedAt: string;
  views?: number;
  likes?: number;
}

interface ApiResponse {
  contents: TechContent[];
  total: number;
  page: number;
  limit: number;
}

export default function TechContentsPage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [contents, setContents] = useState<TechContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 9;

  // 从 URL 获取筛选参数
  const contentType = searchParams.get('type') || '';
  const currentType = contentType as 'analysis' | 'sharing' | 'case_study' | '';

  useEffect(() => {
    fetchContents();
  }, [currentType, page]);

  const fetchContents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });

      if (currentType) {
        params.append('content_type', currentType);
      }

      const response = await fetch(`${API_BASE_URL}/tech-contents?${params}`);
      const data: ApiResponse = await response.json();

      setContents(data.contents);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to fetch contents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTypeChange = (type: string) => {
    const newParams = new URLSearchParams();
    if (type) {
      newParams.set('type', type);
    }
    setSearchParams(newParams);
    setPage(1);
  };

  const totalPages = Math.ceil(total / limit);

  const contentTypes = [
    { value: '', label: '全部' },
    { value: 'analysis', label: '技术分析' },
    { value: 'sharing', label: '技术分享' },
    { value: 'case_study', label: '项目案例' },
  ];

  return (
    <div className="bg-canvas min-h-screen">
      {/* Hero Section：结构化玻璃 hero（贴边玻璃面板替换整宽彩色渐变），与 CoursesPage/Header 同构 */}
      <div className="glass-panel border-x-0 border-t-0 rounded-none">
        <div className="container mx-auto px-6 py-12">
          <h1 className="text-4xl font-bold text-ink mb-4">
            {/* gradient-text 会置 color: transparent，故只包文字词组，避免图标（currentColor）被透明化 */}
            <span className="gradient-text">技术分析</span>
          </h1>
          <p className="text-ink-muted text-lg max-w-3xl">
            深入探讨技术趋势、架构决策和工程实践，分享团队内部的技术经验和项目案例
          </p>
        </div>
      </div>

      {/* 筛选栏：玻璃胶囊容器 + 单个胶囊 Tab（同 Hero/CategoryTabs 模式） */}
      <div className="container mx-auto px-6 py-6">
        <div className="glass-card rounded-full p-1 inline-flex overflow-x-auto flex-nowrap max-w-full">
          {contentTypes.map((type) => (
            <button
              key={type.value}
              onClick={() => handleTypeChange(type.value)}
              className={cn(
                // 公共胶囊样式：不换行 + 过渡动画；focus-visible 焦点环与设计系统 Button 基类保持一致
                'rounded-full px-4 py-1.5 text-sm whitespace-nowrap transition-all duration-200',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-canvas',
                currentType === type.value
                  ? // 激活态：品牌渐变底 + 品牌色发光阴影
                    'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]'
                  : // 非激活态：弱化文字色，hover 增强并提亮玻璃底
                    'text-ink-muted hover:text-ink hover:bg-glass-bg'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* 内容列表 */}
      <div className="container mx-auto px-6 pb-12">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-ink-muted">加载中...</div>
          </div>
        ) : contents.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center text-ink-muted">
              <Inbox className="w-8 h-8 mb-4 mx-auto" />
              <p>暂无内容</p>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {contents.map((content) => (
                <TechContentCard key={content.id} {...content} />
              ))}
            </div>

            {/* 分页 */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                {/* 分页按钮走设计系统 outline 变体（disabled 态由 Button 基类统一处理） */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="px-4 py-2 text-ink-muted">
                  第 {page} 页，共 {totalPages} 页，{total} 篇文章
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                >
                  下一页
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

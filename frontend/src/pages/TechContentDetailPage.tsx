import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useI18n } from '../i18n/index.ts';
import { API_BASE_URL } from '../config/api.ts';

interface TechContent {
  id: number;
  slug: string;
  contentType: 'analysis' | 'sharing' | 'case_study';
  contentTypeLabel?: string;
  tags?: string[];
  title: string;
  description: string;
  coverImage?: string;
  author?: string;
  readingTime: number;
  publishedAt: string;
  updatedAt?: string;
  views: number;
  likes: number;
  bookmarks: number;
  chapters?: Chapter[];
  content: string;
}

interface Chapter {
  id: number;
  slug: string;
  title: string;
  order: number;
  chapterType: string;
  readingTime: number;
}

export default function TechContentDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { t } = useI18n();

  const [content, setContent] = useState<TechContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (slug) {
      fetchContent();
    }
  }, [slug]);

  const fetchContent = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/tech-contents/${slug}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('内容不存在');
        }
        throw new Error('加载失败');
      }
      const data = await response.json();
      setContent(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // 内容类型标签配色
  const contentTypeColors = {
    analysis: 'bg-accent-info/20 text-accent-info border-accent-info/30',
    sharing: 'bg-green-500/20 text-green-400 border-green-500/30',
    case_study: 'bg-accent-secondary/20 text-accent-secondary border-accent-secondary/30',
  };

  if (loading) {
    return (
      <div className="bg-canvas min-h-screen flex items-center justify-center">
        <div className="text-ink-muted">加载中...</div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="bg-canvas min-h-screen flex items-center justify-center">
        <div className="text-center text-ink-muted">
          <i className="fas fa-exclamation-circle text-4xl mb-4"></i>
          <p className="mb-4">{error || '内容不存在'}</p>
          <button
            onClick={() => navigate('/tech-contents')}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-accent-hover transition-colors"
          >
            返回列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-canvas min-h-screen">
      {/* 面包屑导航 */}
      <div className="border-b border-border">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center gap-2 text-sm text-ink-muted">
            <Link to="/" className="hover:text-ink-inverse transition-colors">
              首页
            </Link>
            <span>/</span>
            <Link to="/tech-contents" className="hover:text-ink-inverse transition-colors">
              技术分析
            </Link>
            <span>/</span>
            <span className="text-ink-faint">{content.title}</span>
          </div>
        </div>
      </div>

      {/* 文章头部 */}
      <div className="border-b border-border">
        <div className="container mx-auto px-6 py-8">
          {/* 标签 */}
          <div className="flex gap-2 mb-4">
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium border ${
                contentTypeColors[content.contentType]
              }`}
            >
              {content.contentTypeLabel || content.contentType}
            </span>
            {content.tags &&
              content.tags.map((tag, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-surface-1 text-ink-muted text-sm rounded-full"
                >
                  {tag}
                </span>
              ))}
          </div>

          {/* 标题 */}
          <h1 className="text-3xl md:text-4xl font-bold text-ink-inverse mb-6">
            {content.title}
          </h1>

          {/* 作者信息 */}
          <div className="flex items-center gap-4 pb-6 border-b border-border">
            {content.author && (
              <>
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-accent-info to-accent-secondary flex items-center justify-center text-white text-lg font-bold">
                  {content.author.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="text-ink-inverse font-medium">{content.author}</div>
                  <div className="text-ink-muted text-sm">
                    发布于 {formatDate(content.publishedAt)} · 预计阅读 {content.reading_time} 分钟
                  </div>
                </div>
              </>
            )}
          </div>

          {/* 统计信息 */}
          <div className="flex gap-6 pt-4 text-ink-muted text-sm">
            <span className="flex items-center gap-1.5">
              <i className="fas fa-eye"></i>
              {content.views} 阅读
            </span>
            <span className="flex items-center gap-1.5">
              <i className="fas fa-thumbs-up"></i>
              {content.likes} 点赞
            </span>
            <span className="flex items-center gap-1.5">
              <i className="fas fa-bookmark"></i>
              {content.bookmarks} 收藏
            </span>
          </div>
        </div>
      </div>

      {/* 封面图 */}
      {content.coverImage && (
        <div className="container mx-auto px-6 py-8">
          <img
            src={content.coverImage}
            alt={content.title}
            className="w-full h-auto rounded-xl"
          />
        </div>
      )}

      {/* 章节导航 */}
      {content.chapters && content.chapters.length > 0 && (
        <div className="container mx-auto px-6 py-8">
          <h2 className="text-xl font-semibold text-ink-inverse mb-4">章节导航</h2>
          <div className="flex flex-wrap gap-2">
            {content.chapters.map((chapter) => (
              <div
                key={chapter.id}
                className="px-4 py-2 bg-surface-1 rounded-lg text-ink-muted text-sm hover:bg-surface-2 cursor-pointer transition-colors"
              >
                {chapter.order}. {chapter.title}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 正文内容 */}
      <div className="container mx-auto px-6 py-8">
        <div className="max-w-4xl mx-auto">
          <article className="prose prose-invert prose-lg max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content.content}
            </ReactMarkdown>
          </article>

          {/* 互动区 */}
          <div className="flex items-center gap-4 mt-12 pt-8 border-t border-border">
            <button className="flex items-center gap-2 px-4 py-2 bg-surface-1 text-ink-muted rounded-lg hover:bg-surface-2 transition-colors">
              <i className="fas fa-thumbs-up"></i>
              点赞 ({content.likes})
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-surface-1 text-ink-muted rounded-lg hover:bg-surface-2 transition-colors">
              <i className="fas fa-bookmark"></i>
              收藏 ({content.bookmarks})
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-surface-1 text-ink-muted rounded-lg hover:bg-surface-2 transition-colors">
              <i className="fas fa-share"></i>
              分享
            </button>
          </div>
        </div>
      </div>

      {/* 相关推荐 */}
      <div className="container mx-auto px-6 py-12">
        <h2 className="text-2xl font-bold text-ink-inverse mb-6">相关推荐</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* TODO: 加载相关内容 */}
          <div className="text-ink-muted text-center py-8">
            暂无相关内容
          </div>
        </div>
      </div>
    </div>
  );
}

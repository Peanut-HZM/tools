import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n/index.ts';
import { API_BASE_URL } from '../../config/api.ts';

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
  views?: number;
  likes?: number;
}

export default function Recommendations() {
  const { t } = useI18n();
  const [contents, setContents] = useState<TechContent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContents();
  }, []);

  const fetchContents = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/tech-contents?limit=3`);
      const data = await response.json();
      setContents(data.contents || []);
    } catch (error) {
      console.error('Failed to fetch tech contents:', error);
    } finally {
      setLoading(false);
    }
  };

  // 内容类型标签配色
  const contentTypeColors = {
    analysis: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    sharing: 'bg-green-500/20 text-green-400 border-green-500/30',
    case_study: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };

  return (
    <section className="mb-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-4">技术分析</h2>
        <p className="text-slate-400">深入探讨技术趋势、架构决策和工程实践</p>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-slate-400">加载中...</div>
        </div>
      ) : contents.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          暂无内容
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {contents.map((content) => (
            <Link
              key={content.id}
              to={`/tech-contents/${content.slug}`}
              className="bg-slate-800 rounded-xl overflow-hidden border border-slate-700 hover:border-slate-600 transition-all group"
            >
              {/* 封面图 */}
              {content.coverImage ? (
                <div className="relative h-40 overflow-hidden">
                  <img
                    src={content.coverImage}
                    alt={content.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                </div>
              ) : (
                <div className="relative h-40 bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
                  <div className="text-slate-600 text-5xl">
                    <i className="fas fa-file-alt"></i>
                  </div>
                </div>
              )}

              {/* 内容区 */}
              <div className="p-4">
                {/* 标签 */}
                <div className="flex gap-2 mb-3">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                      contentTypeColors[content.contentType]
                    }`}
                  >
                    {content.contentTypeLabel || content.contentType}
                  </span>
                </div>

                {/* 标题 */}
                <h3 className="text-lg font-semibold text-slate-100 mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                  {content.title}
                </h3>

                {/* 描述 */}
                <p className="text-slate-400 text-sm mb-4 line-clamp-2">
                  {content.description.replace(/[#*`]/g, '').substring(0, 80)}...
                </p>

                {/* 作者和阅读时长 */}
                <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-700">
                  <div className="flex items-center gap-2">
                    {content.author && (
                      <>
                        <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xs font-medium">
                          {content.author.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-slate-400 truncate max-w-[100px]">{content.author}</span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span>{content.readingTime} min</span>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
      <div className="text-center mt-8">
        <Link
          to="/tech-contents"
          className="inline-block px-6 py-3 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
        >
          查看更多 →
        </Link>
      </div>
    </section>
  );
}

import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n/index.ts';

export interface TechContentCardProps {
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

export default function TechContentCard({
  id,
  slug,
  coverImage,
  contentType,
  contentTypeLabel,
  tags = [],
  title,
  description,
  author,
  readingTime,
  publishedAt,
  views = 0,
  likes = 0,
}: TechContentCardProps) {
  const navigate = useNavigate();
  const { t } = useI18n();

  const handleClick = () => {
    navigate(`/tech-contents/${slug}`);
  };

  // 内容类型标签配色
  const contentTypeColors = {
    analysis: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    sharing: 'bg-green-500/20 text-green-400 border-green-500/30',
    case_study: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // 移除 Markdown 语法获取纯文本描述
  const getPlainText = (text: string) => {
    return text
      .replace(/#{1,6}\s/g, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`{3,}[\s\S]*?`{3,}/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/-{3,}/g, '—')
      .trim();
  };

  return (
    <div
      onClick={handleClick}
      className="bg-slate-800 rounded-xl overflow-hidden border border-slate-700 hover:border-slate-600 transition-all cursor-pointer group"
    >
      {/* 封面图 */}
      {coverImage ? (
        <div className="relative h-48 overflow-hidden">
          <img
            src={coverImage}
            alt={title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute top-3 left-3 flex gap-2">
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                contentTypeColors[contentType]
              }`}
            >
              {contentTypeLabel || contentType}
            </span>
          </div>
        </div>
      ) : (
        <div className="relative h-48 bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
          <div className="text-slate-600 text-6xl">
            <i className="fas fa-file-alt"></i>
          </div>
          <div className="absolute top-3 left-3 flex gap-2">
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                contentTypeColors[contentType]
              }`}
            >
              {contentTypeLabel || contentType}
            </span>
          </div>
        </div>
      )}

      {/* 内容区 */}
      <div className="p-5">
        {/* 标签列表 */}
        {tags.length > 0 && tags.slice(0, 3).length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-0.5 bg-slate-700 text-slate-400 text-xs rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* 标题 */}
        <h3 className="text-lg font-semibold text-slate-100 mb-2 line-clamp-2 group-hover:text-primary transition-colors">
          {title}
        </h3>

        {/* 描述 */}
        <p className="text-slate-400 text-sm mb-4 line-clamp-3">
          {getPlainText(description)}
        </p>

        {/* 作者和阅读时长 */}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-700">
          <div className="flex items-center gap-2">
            {author && (
              <>
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xs font-medium">
                  {author.charAt(0).toUpperCase()}
                </div>
                <span className="text-slate-400">{author}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span>{readingTime} min read</span>
            {views > 0 && (
              <span className="flex items-center gap-1">
                <i className="fas fa-eye text-xs"></i>
                {views}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n/index.ts';
import { FileText, Eye } from 'lucide-react';

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
    analysis: 'bg-accent-info/20 text-accent-info border-accent-info/30',
    sharing: 'bg-success/20 text-success border-success/30',
    case_study: 'bg-accent-secondary/20 text-accent-secondary border-accent-secondary/30',
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
      className="bg-surface-1 rounded-xl overflow-hidden border border-border hover:border-border transition-all cursor-pointer group"
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
        <div className="relative h-48 bg-gradient-to-br from-surface-2 to-surface-1 flex items-center justify-center">
          <div className="text-ink-faint text-6xl">
            <FileText className="w-16 h-16" />
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
                className="px-2 py-0.5 bg-surface-2 text-ink-muted text-xs rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* 标题 */}
        <h3 className="text-lg font-semibold text-ink mb-2 line-clamp-2 group-hover:text-primary transition-colors">
          {title}
        </h3>

        {/* 描述 */}
        <p className="text-ink-muted text-sm mb-4 line-clamp-3">
          {getPlainText(description)}
        </p>

        {/* 作者和阅读时长 */}
        <div className="flex items-center justify-between text-xs text-ink-faint pt-3 border-t border-border">
          <div className="flex items-center gap-2">
            {author && (
              <>
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent-info to-accent-secondary flex items-center justify-center text-ink-inverse text-xs font-medium">
                  {author.charAt(0).toUpperCase()}
                </div>
                <span className="text-ink-muted">{author}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span>{readingTime} min read</span>
            {views > 0 && (
              <span className="flex items-center gap-1">
                <Eye className="w-3 h-3 text-xs" />
                {views}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

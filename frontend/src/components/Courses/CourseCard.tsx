/**
 * 课程卡片组件
 * 与首页工具卡片风格一致
 */
import React from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/Tooltip';

interface CourseCardProps {
  id: number;
  slug: string;
  title: string;
  description: string;
  cover_image?: string | null;
  category?: {
    name: string;
    slug: string;
  } | null;
  statistics?: {
    view_count: number;
    like_count: number;
    bookmark_count: number;
    review_count: number;
    avg_rating: number;
  } | null;
  progress?: {
    completed_chapters: number;
    total_chapters: number;
    percent: number;
  };
  onClick?: (course: { id: number; slug: string }) => void;
}

const CourseCard: React.FC<CourseCardProps> = ({
  id,
  slug,
  title,
  description,
  cover_image,
  category,
  statistics,
  progress,
  onClick,
}) => {
  const handleClick = () => {
    onClick?.({ id, slug });
  };

  // 默认封面图（渐变背景）
  const defaultCover = (
    <div className="w-full aspect-video bg-gradient-to-br from-accent/20 to-accent-hover/20 flex items-center justify-center">
      <i className="fas fa-graduation-cap text-6xl text-accent/50"></i>
    </div>
  );

  return (
    <div
      onClick={handleClick}
      className="group cursor-pointer bg-surface-1/50 rounded-2xl overflow-hidden border border-border/50 hover:border-accent/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-md hover:shadow-accent/10"
    >
      {/* 封面图 */}
      <div className="relative overflow-hidden">
        {cover_image ? (
          <img
            src={cover_image}
            alt={title}
            className="w-full aspect-video object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          defaultCover
        )}

        {/* 分类标签 */}
        {category && (
          <span className="absolute top-3 left-3 px-3 py-1 bg-canvas/80 backdrop-blur-sm text-accent text-xs font-medium rounded-full">
            {category.name}
          </span>
        )}

        {/* 进度条（我的课程） */}
        {progress && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-surface-2">
            <div
              className="h-full bg-gradient-to-r from-accent to-accent-info transition-all duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        )}
      </div>

      {/* 内容 */}
      <div className="p-5">
        {/* 标题 */}
        <h3 className="text-lg font-semibold text-ink-inverse mb-2 line-clamp-1 group-hover:text-accent transition-colors">
          {title}
        </h3>

        {/* 描述 */}
        <p className="text-ink-muted text-sm mb-4 line-clamp-2">
          {description}
        </p>

        {/* 统计信息 */}
        {statistics && (
          <div className="flex items-center justify-between text-xs text-ink-faint">
            <div className="flex items-center space-x-3">
              <span className="flex items-center">
                <i className="fas fa-star text-accent-warning mr-1"></i>
                {statistics.avg_rating.toFixed(1)}
              </span>
              <span className="flex items-center">
                <i className="fas fa-user mr-1"></i>
                {statistics.enroll_count >= 1000
                  ? `${(statistics.enroll_count / 1000).toFixed(1)}k`
                  : statistics.enroll_count}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="flex items-center">
                <i className="fas fa-heart text-pink-400 mr-1"></i>
                {statistics.like_count}
              </span>
              <span className="flex items-center">
                <i className="fas fa-bookmark text-accent-info mr-1"></i>
                {statistics.bookmark_count}
              </span>
            </div>
          </div>
        )}

        {/* 进度信息（我的课程） */}
        {progress && (
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-ink-muted">
              已学 {progress.completed_chapters}/{progress.total_chapters} 章节
            </span>
            <span className="text-accent font-medium">
              {progress.percent}%
            </span>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="mt-4 flex items-center justify-between">
          <button className="px-4 py-2 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent-hover text-white text-sm font-medium rounded-lg transition-all duration-200 hover:shadow-lg hover:shadow-accent/25">
            {progress ? '继续学习' : '立即学习'}
          </button>
          <div className="flex items-center space-x-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="p-2 text-ink-muted hover:text-pink-400 hover:bg-pink-400/10 rounded-lg transition-all"
                    aria-label="点赞"
                  >
                    <i className="fas fa-heart"></i>
                  </button>
                </TooltipTrigger>
                <TooltipContent>点赞</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="p-2 text-ink-muted hover:text-accent-info hover:bg-accent-info/10 rounded-lg transition-all"
                    aria-label="收藏"
                  >
                    <i className="fas fa-bookmark"></i>
                  </button>
                </TooltipTrigger>
                <TooltipContent>收藏</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CourseCard;

/**
 * OpenSpec 课程入口卡片组件
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';

interface OpenSpecCourseCardProps {
  progress?: number;
  completedChapters?: number;
  totalChapters?: number;
  courseId?: number;
  courseSlug?: string;
}

const OpenSpecCourseCard: React.FC<OpenSpecCourseCardProps> = ({
  progress = 0,
  completedChapters = 0,
  totalChapters = 5,
  courseId,
  courseSlug = 'openspec-vibecoding', // 默认 slug
}) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (courseSlug) {
      navigate(`/courses/${courseSlug}`);
    } else {
      navigate('/tools/openspec-course');
    }
  };

  return (
    <div
      onClick={handleClick}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 cursor-pointer transform transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/30"
    >
      {/* Animated Background Pattern */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-0 left-0 w-40 h-40 bg-white rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-0 w-60 h-60 bg-yellow-400 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      {/* Content */}
      <div className="relative p-8">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Badge */}
            <div className="inline-flex items-center px-3 py-1 bg-yellow-500/20 border border-yellow-400 text-yellow-300 rounded-full text-xs font-semibold mb-4">
              ✨ 热门课程
            </div>

            {/* Title */}
            <h3 className="text-3xl font-bold text-white mb-2">
              🎓 OpenSpec VibeCoding 课程
            </h3>
            <p className="text-white/80 mb-4 max-w-xl">
              从 AI 小白到 Spec 高手的进阶之路 | 故事驱动 × 互动学习 × 实战练习
            </p>

            {/* Features */}
            <div className="flex flex-wrap gap-3 mb-6">
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-white rounded-full text-sm">
                📖 故事驱动
              </span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-white rounded-full text-sm">
                📝 互动测验
              </span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-white rounded-full text-sm">
                💻 实战编辑
              </span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-white rounded-full text-sm">
                🎬 视频讲解
              </span>
            </div>

            {/* Progress Bar */}
            {progress > 0 && (
              <div className="mb-4">
                <div className="flex items-center justify-between text-sm text-white/60 mb-2">
                  <span>学习进度</span>
                  <span>{completedChapters}/{totalChapters} 章节完成</span>
                </div>
                <div className="w-full h-2 bg-white/20 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-yellow-400 to-orange-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* CTA Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleClick();
              }}
              className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-black font-semibold rounded-xl transition-colors inline-flex items-center space-x-2"
            >
              <span>{progress > 0 ? '继续学习' : '开始学习'}</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>

          {/* Decorative Icon */}
          <div className="hidden lg:block text-8xl opacity-50">
            🚀
          </div>
        </div>
      </div>
    </div>
  );
};

export default OpenSpecCourseCard;

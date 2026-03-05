/**
 * 章节导航组件
 */
import React from 'react';
import { Chapter, UserProgress } from '../../services/openspecCourse';

interface ChapterNavigationProps {
  chapters: Chapter[];
  progress: UserProgress[];
  currentChapterId: number;
  onSelectChapter: (chapterId: number) => void;
}

const ChapterNavigation: React.FC<ChapterNavigationProps> = ({
  chapters,
  progress,
  currentChapterId,
  onSelectChapter,
}) => {
  const getChapterStatus = (chapterId: number) => {
    const p = progress.find((prog) => prog.chapter_id === chapterId);
    if (!p) return 'locked';
    if (p.status === 'completed') return 'completed';
    if (p.status === 'in_progress') return 'in_progress';
    return 'not_started';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✅';
      case 'in_progress':
        return '📖';
      case 'locked':
        return '🔒';
      default:
        return '⭕';
    }
  };

  return (
    <aside className="w-80 bg-black/20 backdrop-blur-sm border-r border-white/10 overflow-y-auto">
      <div className="p-6">
        <h2 className="text-lg font-semibold text-white mb-4">📚 课程章节</h2>
        <div className="space-y-2">
          {chapters.map((chapter, index) => {
            const status = getChapterStatus(chapter.id);
            const isLocked = chapter.is_locked && status !== 'completed';
            const isActive = chapter.id === currentChapterId;

            return (
              <button
                key={chapter.id}
                onClick={() => !isLocked && onSelectChapter(chapter.id)}
                disabled={isLocked}
                className={`w-full text-left p-4 rounded-xl transition-all ${
                  isActive
                    ? 'bg-yellow-500/20 border-2 border-yellow-500'
                    : isLocked
                    ? 'bg-gray-800/30 border border-gray-700 opacity-50 cursor-not-allowed'
                    : 'bg-white/5 border border-white/10 hover:bg-white/10'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <span className="text-xl">{getStatusIcon(status)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-white/40">#{index + 1}</span>
                      {isLocked && <span className="text-xs text-white/40">🔒 需完成前章</span>}
                    </div>
                    <h3 className="text-white font-medium truncate mt-1">{chapter.title}</h3>
                    {status === 'completed' && (
                      <div className="text-xs text-green-400 mt-1">已完成</div>
                    )}
                    {status === 'in_progress' && (
                      <div className="text-xs text-yellow-400 mt-1">学习中...</div>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
};

export default ChapterNavigation;

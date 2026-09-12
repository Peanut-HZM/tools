/**
 * 章节导航组件
 */
import React from 'react';
import { Chapter, UserProgress } from '../../../services/openspecCourse';

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
    if (!p) return 'not_started';
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
      default:
        return '⭕';
    }
  };

  return (
    // 侧栏为全高玻璃面板：去上/下/左描边，仅保留右侧玻璃描边与主内容区分隔（同 CourseLearnPage 写法）
    <aside className="w-80 glass-panel rounded-none border-y-0 border-l-0 overflow-y-auto">
      <div className="p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">📚 课程章节</h2>
        <div className="space-y-2">
          {chapters.map((chapter, index) => {
            const status = getChapterStatus(chapter.id);
            const isActive = chapter.id === currentChapterId;

            return (
              <button
                key={chapter.id}
                onClick={() => onSelectChapter(chapter.id)}
                className={`w-full text-left p-4 rounded-xl transition-all ${
                  isActive
                    ? 'bg-accent/20 border-2 border-accent'
                    : 'bg-surface-2/30 border border-border/50 hover:bg-surface-2/50'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <span className="text-xl">{getStatusIcon(status)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-ink-muted">#{index + 1}</span>
                    </div>
                    <h3 className="text-ink font-medium truncate mt-1">{chapter.title}</h3>
                    {status === 'completed' && (
                      <div className="text-xs text-success mt-1">已完成</div>
                    )}
                    {status === 'in_progress' && (
                      <div className="text-xs text-accent-warning mt-1">学习中...</div>
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

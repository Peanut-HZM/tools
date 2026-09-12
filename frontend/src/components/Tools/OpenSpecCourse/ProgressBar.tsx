/**
 * 进度条组件
 */
import React from 'react';
import { UserProgress } from '../../../services/openspecCourse';

interface ProgressBarProps {
  progress: UserProgress[];
  total: number;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, total }) => {
  const completedCount = progress.filter((p) => p.status === 'completed').length;
  const percentage = total > 0 ? (completedCount / total) * 100 : 0;

  return (
    <div className="flex items-center space-x-3">
      <div className="text-right">
        <div className="text-sm text-ink-muted">学习进度</div>
        <div className="text-ink font-semibold">
          {completedCount} / {total} 章节
        </div>
      </div>
      <div className="w-48 h-3 bg-surface-2 rounded-full overflow-hidden">
        {/* 进度条渐变走品牌 accent 渐变（同 CourseLearnPage 进度条范式） */}
        <div
          className="h-full bg-gradient-to-r from-accent to-accent-hover transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-accent-warning font-semibold">{percentage.toFixed(0)}%</div>
    </div>
  );
};

export default ProgressBar;

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
        <div className="text-sm text-white/60">学习进度</div>
        <div className="text-white font-semibold">
          {completedCount} / {total} 章节
        </div>
      </div>
      <div className="w-48 h-3 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-yellow-400 to-orange-500 transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-yellow-400 font-semibold">{percentage.toFixed(0)}%</div>
    </div>
  );
};

export default ProgressBar;

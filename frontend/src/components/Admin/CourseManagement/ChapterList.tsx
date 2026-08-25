/**
 * 章节列表组件
 */
import React, { useState } from 'react';
import { useChapterStore } from '../../../stores/courseAdminStore';
import type { CourseChapter as Chapter } from '../../../services/coursePlatform';
import { Button } from "@/components/ui/Button";

interface ChapterListProps {
  chapters: Chapter[];
  onEdit: (chapterId: number) => void;
  onSelect: (chapterId: number) => void;
  selectedChapterId: number | null;
}

const ChapterList: React.FC<ChapterListProps> = ({
  chapters,
  onEdit,
  onSelect,
  selectedChapterId,
}) => {
  const { deleteChapter } = useChapterStore();
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleDelete = async (chapterId: number) => {
    if (confirm('确定要删除这个章节吗？此操作不可撤销。')) {
      await deleteChapter(chapterId);
    }
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === targetIndex) return;
    setDraggedIndex(null);
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      story: 'fa-book',
      code: 'fa-code',
      quiz: 'fa-clipboard-check',
      video: 'fa-video',
    };
    return icons[type] || 'fa-file';
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      story: '故事',
      code: '代码',
      quiz: '测验',
      video: '视频',
    };
    return labels[type] || type;
  };

  return (
    <div className="overflow-y-auto h-full">
      <div className="rounded-xl border border-border/50 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gradient-to-r from-surface-2/50 to-surface-1/50">
            <tr>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">
                <i className="fas fa-sort mr-2"></i>顺序
              </th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">标题</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">类型</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">标识符</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">状态</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {chapters.map((chapter, index) => (
              <tr
                key={chapter.id}
                draggable
                onDragStart={() => handleDragStart(index)}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, index)}
                onClick={() => onSelect(chapter.id)}
                className={`cursor-pointer transition-all duration-200 ${
                  selectedChapterId === chapter.id
                    ? 'bg-cyan-500/10 border-l-2 border-cyan-500'
                    : 'hover:bg-surface-2/30 border-l-2 border-transparent'
                }`}
              >
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <i className="fas fa-grip-vertical text-ink-faint mr-3 cursor-grab"></i>
                    <span className="inline-flex items-center justify-center w-8 h-8 bg-surface-2/50 rounded-lg text-white font-medium">
                      {chapter.order}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-lg flex items-center justify-center mr-3">
                      <i className={`fas ${getTypeIcon(chapter.chapter_type)} text-cyan-400`}></i>
                    </div>
                    <span className="text-white font-medium">{chapter.title}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-3 py-1 bg-surface-2/50 rounded-full text-xs text-ink-muted">
                    {getTypeLabel(chapter.chapter_type)}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <code className="text-ink-muted text-sm bg-surface-2/30 px-2 py-1 rounded">{chapter.slug}</code>
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                      chapter.is_locked
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {chapter.is_locked ? (
                      <>
                        <i className="fas fa-lock mr-1"></i>锁定
                      </>
                    ) : (
                      <>
                        <i className="fas fa-lock-open mr-1"></i>未锁定
                      </>
                    )}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center justify-end space-x-2">
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        onEdit(chapter.id);
                      }}
                      variant="outline"
                      className="px-4 py-2 rounded-lg text-sm transition-all"
                    >
                      <i className="fas fa-edit mr-1"></i>编辑
                    </Button>
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(chapter.id);
                      }}
                      variant="destructive"
                      className="px-4 py-2 rounded-lg text-sm transition-all"
                    >
                      <i className="fas fa-trash mr-1"></i>删除
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {chapters.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-20 h-20 bg-surface-2/30 rounded-full flex items-center justify-center mb-4">
            <i className="fas fa-book text-4xl text-ink-faint"></i>
          </div>
          <p className="text-ink-muted text-lg mb-2">暂无章节</p>
          <p className="text-ink-faint text-sm">点击右上角"新增章节"创建第一个章节</p>
        </div>
      )}
    </div>
  );
};

export default ChapterList;

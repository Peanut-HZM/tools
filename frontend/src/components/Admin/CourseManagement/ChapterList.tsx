/**
 * 章节列表组件
 */
import React, { useState, type ReactNode } from 'react';
import { ArrowUpDown, GripVertical, Lock, Unlock, Pencil, Trash2, BookOpen, Code, ClipboardCheck, Video, File } from 'lucide-react';
import { useChapterStore } from '../../../stores/courseAdminStore';
import type { CourseChapter as Chapter } from '../../../services/coursePlatform';
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

interface ChapterListProps {
  chapters: Chapter[];
  onEdit: (chapterId: number) => void;
  onSelect: (chapterId: number) => void;
  selectedChapterId: number | null;
}

// 章节类型语义色标：图标底色与图标色共用同一语义 token（亮/暗主题均可读）
// 注意：类名必须写全字面量，Tailwind JIT 才能生成对应样式
const CHAPTER_TYPE_STYLE: Record<string, { box: string; icon: ReactNode }> = {
  story: {
    box: 'bg-accent-info/10 border-accent-info/25',
    icon: <BookOpen className="w-4 h-4 text-accent-info" />,
  },
  code: {
    box: 'bg-accent-secondary/10 border-accent-secondary/25',
    icon: <Code className="w-4 h-4 text-accent-secondary" />,
  },
  quiz: {
    box: 'bg-accent-warm/10 border-accent-warm/25',
    icon: <ClipboardCheck className="w-4 h-4 text-accent-warm" />,
  },
  video: {
    box: 'bg-accent-cyan/10 border-accent-cyan/25',
    icon: <Video className="w-4 h-4 text-accent-cyan" />,
  },
  default: {
    box: 'bg-accent/10 border-accent/25',
    icon: <File className="w-4 h-4 text-accent" />,
  },
};

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

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === targetIndex) return;
    setDraggedIndex(null);
  };

  const getTypeStyle = (type: string) =>
    CHAPTER_TYPE_STYLE[type] || CHAPTER_TYPE_STYLE.default;

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
      <div className="rounded-xl border border-border/50 overflow-x-auto">
        <table className="w-full min-w-[880px] text-left">
          <thead className="bg-surface-2/60 border-b border-border/60">
            <tr>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm whitespace-nowrap">
                <span className="inline-flex items-center gap-2">
                  <ArrowUpDown className="w-4 h-4" />顺序
                </span>
              </th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm">标题</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm">类型</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm">标识符</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm">状态</th>
              <th className="px-6 py-4 text-ink-muted font-medium text-sm text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {chapters.map((chapter, index) => {
              const typeStyle = getTypeStyle(chapter.chapter_type);
              return (
                <tr
                  key={chapter.id}
                  draggable
                  onDragStart={() => handleDragStart(index)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, index)}
                  onClick={() => onSelect(chapter.id)}
                  className={`cursor-pointer transition-colors duration-200 ${
                    selectedChapterId === chapter.id
                      ? 'bg-accent-info/10 border-l-2 border-accent-info'
                      : 'hover:bg-surface-2/40 border-l-2 border-transparent'
                  }`}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <GripVertical className="w-4 h-4 text-ink-faint hover:text-ink-muted cursor-grab shrink-0" />
                      <span className="inline-flex items-center justify-center w-8 h-8 bg-surface-2 border border-border/50 rounded-lg text-ink font-medium text-sm tabular-nums shrink-0">
                        {chapter.order}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 max-w-[380px]">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-10 h-10 ${typeStyle.box} border rounded-lg flex items-center justify-center shrink-0`}>
                        {typeStyle.icon}
                      </div>
                      <span className="text-ink font-medium truncate" title={chapter.title}>
                        {chapter.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant="secondary">
                      {getTypeLabel(chapter.chapter_type)}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <code className="text-ink-muted text-sm bg-surface-2/50 px-2 py-1 rounded border border-border/40">{chapter.slug}</code>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={chapter.is_locked ? 'warning' : 'success'}>
                      {chapter.is_locked ? (
                        <>
                          <Lock className="w-3 h-3 mr-1" />锁定
                        </>
                      ) : (
                        <>
                          <Unlock className="w-3 h-3 mr-1" />未锁定
                        </>
                      )}
                    </Badge>
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
                        <Pencil className="w-4 h-4 mr-1" />编辑
                      </Button>
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(chapter.id);
                        }}
                        variant="destructive"
                        className="px-4 py-2 rounded-lg text-sm transition-all"
                      >
                        <Trash2 className="w-4 h-4 mr-1" />删除
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {chapters.length === 0 && (
        <div className="glass-card rounded-xl px-6 py-10 flex flex-col items-center justify-center">
          <div className="w-20 h-20 bg-surface-2/30 rounded-full flex items-center justify-center mb-4">
            <BookOpen className="w-16 h-16 text-ink-faint" />
          </div>
          <p className="text-ink-muted text-lg mb-2">暂无章节</p>
          <p className="text-ink-faint text-sm">点击右上角"新增章节"创建第一个章节</p>
        </div>
      )}
    </div>
  );
};

export default ChapterList;

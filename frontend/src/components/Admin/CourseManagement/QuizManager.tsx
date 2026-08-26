/**
 * 测验管理组件
 */
import React, { useState } from 'react';
import { BookOpen, Code as CodeIcon, Video, CheckCircle, Circle, ClipboardCheck, Plus, ClipboardList, Pencil, CircleHelp, ArrowLeft, ReactNode } from 'lucide-react';
import { useQuizStore } from '../../../stores/courseAdminStore';
import type { CourseChapter as Chapter } from '../../../services/coursePlatform';
import QuizForm from './QuizForm';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface QuizManagerProps {
  chapters: Chapter[];
  selectedChapterId: number | null;
  onSelectChapter: (chapterId: number) => void;
}

const QuizManager: React.FC<QuizManagerProps> = ({
  chapters,
  selectedChapterId,
  onSelectChapter,
}) => {
  const { quizzes, fetchQuiz } = useQuizStore();
  const [showQuizForm, setShowQuizForm] = useState(false);
  const [editingQuizId, setEditingQuizId] = useState<number | null>(null);
  const [loadingQuizId, setLoadingQuizId] = useState<number | null>(null);

  const handleSelectChapter = async (chapterId: number) => {
    onSelectChapter(chapterId);
    setLoadingQuizId(chapterId);
    try {
      await fetchQuiz(chapterId);
    } catch (error) {
      console.error('获取测验失败:', error);
    } finally {
      setLoadingQuizId(null);
    }
  };

  const handleCreateQuiz = () => {
    if (!selectedChapterId) {
      alert('请先选择一个章节');
      return;
    }
    setEditingQuizId(null);
    setShowQuizForm(true);
  };

  const handleEditQuiz = (quizId: number) => {
    setEditingQuizId(quizId);
    setShowQuizForm(true);
  };

  const handleCloseForm = () => {
    setShowQuizForm(false);
    setEditingQuizId(null);
  };

  const selectedQuiz = selectedChapterId ? quizzes[selectedChapterId] : null;

  return (
    <div className="h-full flex">
      {/* Chapter List */}
      <div className="w-80 border-r border-border/50 pr-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-ink flex items-center">
            <BookOpen className="w-4 h-4 mr-2 text-accent" />
            选择章节
          </h3>
          <p className="text-ink-faint text-sm mt-1">点击章节加载对应测验</p>
        </div>
        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-300px)]">
          {chapters.map((chapter) => {
            const hasQuiz = quizzes[chapter.id];
            return (
              <button
                key={chapter.id}
                onClick={() => handleSelectChapter(chapter.id)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-200 ${
                  selectedChapterId === chapter.id
                    ? 'bg-gradient-to-r from-accent-info/20 to-accent-info/10 border border-accent shadow-lg shadow-accent-info/10'
                    : 'bg-surface-2/30 border border-border/50 hover:bg-surface-2/50 hover:border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      {chapter.chapter_type === 'story' ? (
                    <BookOpen className="w-4 h-4 text-ink-faint" />
                  ) : chapter.chapter_type === 'code' ? (
                    <CodeIcon className="w-4 h-4 text-ink-faint" />
                  ) : (
                    <Video className="w-4 h-4 text-ink-faint" />
                  )}
                      <span className="text-ink font-medium truncate">{chapter.title}</span>
                    </div>
                  </div>
                  {hasQuiz ? (
                    <span className="inline-flex items-center px-2 py-1 bg-success/20 text-success border border-success/30 rounded text-xs">
                      <CheckCircle className="w-4 h-4 mr-1" />已创建
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-1 bg-surface-3/50 text-ink-muted border border-border/50 rounded text-xs">
                      <Circle className="w-4 h-4 mr-1" />未创建
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Quiz Content */}
      <div className="flex-1 pl-4">
        {selectedChapterId ? (
          <>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-bold text-ink flex items-center">
                  <ClipboardCheck className="w-5 h-5 text-accent mr-3" />
                  测验：{chapters.find((c) => c.id === selectedChapterId)?.title}
                </h3>
                <p className="text-ink-muted text-sm mt-1">管理和编辑章节测验</p>
              </div>
              <Button
                onClick={handleCreateQuiz}
                variant="default"
                className="px-6 py-3 bg-gradient-to-r from-accent to-accent-hover rounded-xl transition-all font-medium shadow-lg shadow-accent-info/20 hover:shadow-accent-info/30 flex items-center"
              >
                <Plus className="w-4 h-4 mr-2" />
                {selectedQuiz ? '编辑测验' : '创建测验'}
              </Button>
            </div>

            {loadingQuizId === selectedChapterId ? (
              <div className="flex items-center justify-center py-16">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-info mx-auto mb-4"></div>
                  <p className="text-ink-muted">加载中...</p>
                </div>
              </div>
            ) : selectedQuiz ? (
              <Card className="rounded-2xl p-6 border-border/50 shadow-md">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-accent to-accent-hover rounded-2xl flex items-center justify-center">
                      <ClipboardList className="w-8 h-8 text-ink" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-ink">{selectedQuiz.title}</h4>
                      <p className="text-ink-muted text-sm">测验基本信息</p>
                    </div>
                  </div>
                  <div className="flex space-x-6">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-accent">{selectedQuiz.questions.length}</div>
                      <div className="text-ink-faint text-sm mt-1">题目数量</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-accent-secondary">{selectedQuiz.passing_score}%</div>
                      <div className="text-ink-faint text-sm mt-1">及格分数</div>
                    </div>
                  </div>
                </div>

                <div className="bg-surface-2/30 rounded-xl p-4 border border-border/50">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-ink-muted text-sm mb-1">及格分数</p>
                      <p className="text-ink font-medium">{selectedQuiz.passing_score}%</p>
                    </div>
                    <div>
                      <p className="text-ink-muted text-sm mb-1">题目数量</p>
                      <p className="text-ink font-medium">{selectedQuiz.questions.length} 题</p>
                    </div>
                  </div>
                </div>

                <Button
                  onClick={() => handleEditQuiz(selectedQuiz.id)}
                  variant="outline"
                  className="mt-6 px-6 py-3 rounded-xl transition-all font-medium flex items-center"
                >
                  <Pencil className="w-4 h-4 mr-2" />
                  编辑测验
                </Button>
              </Card>
            ) : (
              <div className="flex items-center justify-center py-16">
                <div className="text-center max-w-md">
                  <div className="w-24 h-24 bg-surface-2/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CircleHelp className="w-20 h-20 text-ink-faint" />
                  </div>
                  <p className="text-ink text-lg font-medium mb-2">该章节还没有测验</p>
                  <p className="text-ink-muted text-sm mb-6">创建一个测验来检验学习成果吧</p>
                  <Button
                    onClick={handleCreateQuiz}
                    variant="default"
                    className="px-8 py-3 bg-gradient-to-r from-accent to-accent-hover rounded-xl transition-all font-medium shadow-lg shadow-accent-info/20 hover:shadow-accent-info/30 inline-flex items-center"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    创建测验
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <div className="w-20 h-20 bg-surface-2/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <ArrowLeft className="w-12 h-12 text-ink-faint" />
              </div>
              <p className="text-ink-muted">请从左侧选择一个章节</p>
            </div>
          </div>
        )}
      </div>

      {/* Quiz Form Modal */}
      {showQuizForm && (
        <QuizForm
          chapterId={selectedChapterId!}
          quizId={editingQuizId}
          onClose={handleCloseForm}
        />
      )}
    </div>
  );
};

export default QuizManager;

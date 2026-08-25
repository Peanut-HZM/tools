/**
 * 测验管理组件
 */
import React, { useState } from 'react';
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
          <h3 className="text-lg font-semibold text-ink-inverse flex items-center">
            <i className="fas fa-book mr-2 text-accent"></i>
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
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 border border-accent shadow-lg shadow-cyan-500/10'
                    : 'bg-surface-2/30 border border-border/50 hover:bg-surface-2/50 hover:border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <i className={`fas ${chapter.chapter_type === 'story' ? 'fa-book' : chapter.chapter_type === 'code' ? 'fa-code' : 'fa-video'} text-ink-faint`}></i>
                      <span className="text-ink-inverse font-medium truncate">{chapter.title}</span>
                    </div>
                  </div>
                  {hasQuiz ? (
                    <span className="inline-flex items-center px-2 py-1 bg-success/20 text-success border border-success/30 rounded text-xs">
                      <i className="fas fa-check-circle mr-1"></i>已创建
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-1 bg-surface-3/50 text-ink-muted border border-border/50 rounded text-xs">
                      <i className="fas fa-circle mr-1"></i>未创建
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
                <h3 className="text-2xl font-bold text-ink-inverse flex items-center">
                  <i className="fas fa-clipboard-check text-accent mr-3"></i>
                  测验：{chapters.find((c) => c.id === selectedChapterId)?.title}
                </h3>
                <p className="text-ink-muted text-sm mt-1">管理和编辑章节测验</p>
              </div>
              <Button
                onClick={handleCreateQuiz}
                variant="default"
                className="px-6 py-3 bg-gradient-to-r from-accent to-accent-hover rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 flex items-center"
              >
                <i className="fas fa-plus mr-2"></i>
                {selectedQuiz ? '编辑测验' : '创建测验'}
              </Button>
            </div>

            {loadingQuizId === selectedChapterId ? (
              <div className="flex items-center justify-center py-16">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500 mx-auto mb-4"></div>
                  <p className="text-ink-muted">加载中...</p>
                </div>
              </div>
            ) : selectedQuiz ? (
              <Card className="rounded-2xl p-6 border-border/50 shadow-md">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-accent to-accent-hover rounded-2xl flex items-center justify-center">
                      <i className="fas fa-clipboard-list text-ink-inverse text-2xl"></i>
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-ink-inverse">{selectedQuiz.title}</h4>
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
                      <p className="text-ink-inverse font-medium">{selectedQuiz.passing_score}%</p>
                    </div>
                    <div>
                      <p className="text-ink-muted text-sm mb-1">题目数量</p>
                      <p className="text-ink-inverse font-medium">{selectedQuiz.questions.length} 题</p>
                    </div>
                  </div>
                </div>

                <Button
                  onClick={() => handleEditQuiz(selectedQuiz.id)}
                  variant="outline"
                  className="mt-6 px-6 py-3 rounded-xl transition-all font-medium flex items-center"
                >
                  <i className="fas fa-edit mr-2"></i>
                  编辑测验
                </Button>
              </Card>
            ) : (
              <div className="flex items-center justify-center py-16">
                <div className="text-center max-w-md">
                  <div className="w-24 h-24 bg-surface-2/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <i className="fas fa-clipboard-question text-5xl text-ink-faint"></i>
                  </div>
                  <p className="text-ink-inverse text-lg font-medium mb-2">该章节还没有测验</p>
                  <p className="text-ink-muted text-sm mb-6">创建一个测验来检验学习成果吧</p>
                  <Button
                    onClick={handleCreateQuiz}
                    variant="default"
                    className="px-8 py-3 bg-gradient-to-r from-accent to-accent-hover rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 inline-flex items-center"
                  >
                    <i className="fas fa-plus mr-2"></i>
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
                <i className="fas fa-arrow-left text-3xl text-ink-faint"></i>
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

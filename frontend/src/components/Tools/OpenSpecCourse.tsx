/**
 * OpenSpec VibeCoding 互动课程
 * 故事驱动的互动学习方式，让同事掌握 OpenSpec 编程
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getChapters,
  getChapterDetail,
  getCourseProgress,
  updateChapterProgress,
  Chapter,
  UserProgress,
} from '../../services/openspecCourse';
import ChapterNavigation from './ChapterNavigation';
import ChapterContent from './ChapterContent';
import QuizView from './QuizView';
import SpecEditor from './SpecEditor';
import ProgressBar from './ProgressBar';

const OpenSpecCourse: React.FC = () => {
  const navigate = useNavigate();

  // State
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null);
  const [currentChapterId, setCurrentChapterId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<UserProgress[]>([]);
  const [showQuiz, setShowQuiz] = useState(false);
  const [showSpecEditor, setShowSpecEditor] = useState(false);
  const [completedChapters, setCompletedChapters] = useState<number[]>([]);

  // Load chapters on mount
  useEffect(() => {
    loadChapters();
    loadProgress();
  }, []);

  const loadChapters = async () => {
    try {
      setLoading(true);
      const data = await getChapters();
      setChapters(data);
      if (data.length > 0 && !currentChapterId) {
        // 默认加载第一章
        loadChapter(data[0].id);
      }
      setError(null);
    } catch (err) {
      setError('加载课程失败，请稍后重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadProgress = async () => {
    try {
      const summary = await getCourseProgress();
      setProgress(summary.chapters);
      setCompletedChapters(
        summary.chapters
          .filter((p) => p.status === 'completed')
          .map((p) => p.chapter_id)
      );
    } catch (err) {
      console.error('Failed to load progress:', err);
    }
  };

  const loadChapter = async (chapterId: number) => {
    try {
      setLoading(true);
      const chapter = await getChapterDetail(chapterId);
      setCurrentChapter(chapter);
      setCurrentChapterId(chapterId);
      setShowQuiz(false);
      setShowSpecEditor(false);

      // 更新进度为进行中
      if (chapter.user_progress?.status === 'not_started') {
        await updateChapterProgress(chapterId, { status: 'in_progress' });
        loadProgress();
      }
    } catch (err) {
      setError('加载章节失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChapterSelect = (chapterId: number) => {
    const chapter = chapters.find((c) => c.id === chapterId);
    const chapterProgress = progress.find((p) => p.chapter_id === chapterId);

    // 检查章节是否已解锁
    if (chapter?.is_locked && chapterProgress?.status !== 'completed') {
      // 显示锁定提示
      return;
    }

    loadChapter(chapterId);
  };

  const handleQuizComplete = (passed: boolean, chapterId: number) => {
    setShowQuiz(false);
    if (passed) {
      // 更新章节为已完成
      updateChapterProgress(chapterId, {
        status: 'completed',
        completed_at: new Date().toISOString(),
      });
      loadProgress();
    }
  };

  const handleContinueToNextChapter = () => {
    if (!currentChapterId) return;

    const currentIndex = chapters.findIndex((c) => c.id === currentChapterId);
    if (currentIndex < chapters.length - 1) {
      const nextChapter = chapters[currentIndex + 1];
      loadChapter(nextChapter.id);
    }
  };

  if (loading && chapters.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-800 to-blue-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <div className="text-white text-xl">正在加载课程...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-800 to-blue-900 flex items-center justify-center">
        <div className="text-center bg-red-500/20 border border-red-500 text-red-300 px-6 py-4 rounded-xl">
          <div className="text-xl mb-2">😕 {error}</div>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-800 to-blue-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="text-white/80 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-2xl font-bold text-white">🎓 OpenSpec VibeCoding 课程</h1>
                <p className="text-sm text-white/60">从 AI 小白到 Spec 高手的进阶之路</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <ProgressBar progress={progress} total={chapters.length} />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Sidebar - Chapter Navigation */}
        <ChapterNavigation
          chapters={chapters}
          progress={progress}
          currentChapterId={currentChapterId || 0}
          onSelectChapter={handleChapterSelect}
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-8 py-8">
            {showSpecEditor ? (
              <SpecEditor onClose={() => setShowSpecEditor(false)} />
            ) : showQuiz && currentChapter ? (
              <QuizView
                chapter={currentChapter}
                onComplete={handleQuizComplete}
                onCancel={() => setShowQuiz(false)}
              />
            ) : currentChapter ? (
              <ChapterContent
                chapter={currentChapter}
                onNextChapter={handleContinueToNextChapter}
                onStartQuiz={() => setShowQuiz(true)}
                onOpenSpecEditor={() => setShowSpecEditor(true)}
                isCompleted={completedChapters.includes(currentChapter.id)}
              />
            ) : (
              <div className="text-center text-white/60 py-16">
                请选择一个章节开始学习
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default OpenSpecCourse;

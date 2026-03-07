/**
 * 课程学习页面 - 通用课程学习组件
 * 支持多课程切换和学习进度追踪
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getCourseDetail,
  enrollCourse,
  getMyCourses,
  type CourseDetail,
  type CourseChapter,
} from '../services/coursePlatform';

interface ChapterProgress {
  chapter_id: number;
  status: 'not_started' | 'in_progress' | 'completed';
  completed_at?: string;
}

const CourseLearnPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [currentChapter, setCurrentChapter] = useState<CourseChapter | null>(null);
  const [chapterProgress, setChapterProgress] = useState<ChapterProgress[]>([]);
  const [enrolled, setEnrolled] = useState(false);
  const [showContent, setShowContent] = useState<'intro' | 'content'>('intro');

  // Load course on mount
  useEffect(() => {
    loadCourse();
    checkEnrollment();
  }, [slug]);

  const loadCourse = async () => {
    if (!slug) return;
    setLoading(true);
    try {
      const data = await getCourseDetail(slug);
      setCourse(data);
      // 初始化章节进度
      const progress = data.chapters.map((ch) => ({
        chapter_id: ch.id,
        status: 'not_started' as const,
      }));
      setChapterProgress(progress);

      // 默认选择第一个章节
      if (data.chapters.length > 0) {
        setCurrentChapter(data.chapters[0]);
      }
    } catch (error) {
      console.error('加载课程失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkEnrollment = async () => {
    try {
      const data = await getMyCourses();
      const isEnrolled = data.courses.some((item: any) => item.course.slug === slug);
      setEnrolled(isEnrolled);
    } catch (error) {
      console.error('检查报名状态失败:', error);
    }
  };

  const handleEnroll = async () => {
    if (!course) return;
    try {
      await enrollCourse(course.id);
      setEnrolled(true);
      alert('报名成功！开始学习吧～');
    } catch (error) {
      console.error('报名失败:', error);
      alert('报名失败，请重试');
    }
  };

  const handleSelectChapter = (chapter: CourseChapter) => {
    setCurrentChapter(chapter);
    setShowContent('content');
    updateChapterProgress(chapter.id, 'in_progress');
  };

  const updateChapterProgress = (chapterId: number, status: 'not_started' | 'in_progress' | 'completed') => {
    setChapterProgress((prev) =>
      prev.map((p) =>
        p.chapter_id === chapterId
          ? { ...p, status, completed_at: status === 'completed' ? new Date().toISOString() : undefined }
          : p
      )
    );
  };

  const handleCompleteChapter = (chapterId: number) => {
    updateChapterProgress(chapterId, 'completed');

    // 自动跳转到下一章
    if (!course) return;
    const currentIndex = course.chapters.findIndex((ch) => ch.id === chapterId);
    if (currentIndex < course.chapters.length - 1) {
      const nextChapter = course.chapters[currentIndex + 1];
      setCurrentChapter(nextChapter);
    }
  };

  const getChapterStatus = (chapterId: number) => {
    const p = chapterProgress.find((prog) => prog.chapter_id === chapterId);
    return p?.status || 'not_started';
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

  const completedCount = chapterProgress.filter((p) => p.status === 'completed').length;
  const progressPercent = course?.chapters.length ? (completedCount / course.chapters.length) * 100 : 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-4xl text-cyan-400 mb-4"></i>
          <p className="text-slate-400">正在加载课程...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-exclamation-circle text-6xl text-red-400 mb-4"></i>
          <p className="text-white text-xl">课程不存在</p>
          <button
            onClick={() => navigate('/courses')}
            className="mt-4 px-6 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors"
          >
            返回课程列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700/50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(`/courses/${slug}`)}
                className="text-white/80 hover:text-white transition-colors"
              >
                <i className="fas fa-arrow-left"></i>
              </button>
              <div>
                <h1 className="text-xl font-bold text-white">{course.title}</h1>
                <p className="text-sm text-slate-400">
                  进度：{completedCount}/{course.chapters.length} 章节
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Progress Bar */}
              <div className="w-64">
                <div className="flex items-center justify-between text-sm text-slate-400 mb-1">
                  <span>学习进度</span>
                  <span>{Math.round(progressPercent)}%</span>
                </div>
                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Sidebar - Chapter Navigation */}
        <aside className="w-80 bg-slate-800/30 backdrop-blur-sm border-r border-slate-700/50 overflow-y-auto">
          <div className="p-4">
            <h2 className="text-lg font-semibold text-white mb-4">📚 课程章节</h2>
            <div className="space-y-2">
              {course.chapters.map((chapter, index) => {
                const status = getChapterStatus(chapter.id);
                const isActive = currentChapter?.id === chapter.id;
                // 移除锁定逻辑，所有章节都可以自由访问

                return (
                  <button
                    key={chapter.id}
                    onClick={() => handleSelectChapter(chapter)}
                    className={`w-full text-left p-3 rounded-xl transition-all ${
                      isActive
                        ? 'bg-cyan-500/20 border-2 border-cyan-500'
                        : 'bg-slate-700/30 border border-slate-600/50 hover:bg-slate-700/50'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <span className="text-xl">{getStatusIcon(status)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-slate-400">#{index + 1}</span>
                        </div>
                        <h3 className="text-white font-medium truncate">{chapter.title}</h3>
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

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-8 py-8">
            {!enrolled ? (
              /* 未报名状态 - 显示课程详情和报名表单 */
              <div className="max-w-3xl mx-auto">
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-8 text-center">
                  <div className="mb-6">
                    <i className="fas fa-graduation-cap text-6xl text-cyan-400"></i>
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-4">
                    报名课程以开始学习
                  </h2>
                  <p className="text-slate-400 mb-6">
                    {course.description}
                  </p>
                  <div className="flex items-center justify-center space-x-6 mb-6">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">
                        {course.chapters.length}
                      </div>
                      <div className="text-sm text-slate-400">章节</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">
                        {course.statistics?.enroll_count || 0}
                      </div>
                      <div className="text-sm text-slate-400">人在学</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">
                        {course.statistics?.avg_rating?.toFixed(1) || '0.0'}
                      </div>
                      <div className="text-sm text-slate-400">评分</div>
                    </div>
                  </div>
                  <button
                    onClick={handleEnroll}
                    className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold rounded-xl transition-all hover:shadow-lg hover:shadow-cyan-500/25"
                  >
                    <i className="fas fa-book-open mr-2"></i>
                    免费报名开始学习
                  </button>
                </div>
              </div>
            ) : currentChapter ? (
              /* 已报名 - 显示章节内容 */
              <div className="max-w-4xl mx-auto">
                {/* Chapter Header */}
                <div className="mb-8">
                  <div className="flex items-center space-x-3 mb-4">
                    <span className="text-4xl">
                      {currentChapter.chapter_type === 'story' && '📖'}
                      {currentChapter.chapter_type === 'code' && '💻'}
                      {currentChapter.chapter_type === 'quiz' && '📝'}
                      {currentChapter.chapter_type === 'video' && '🎬'}
                    </span>
                    <h2 className="text-3xl font-bold text-white">{currentChapter.title}</h2>
                  </div>
                </div>

                {/* Video Section (if available) */}
                {currentChapter.video_url && (
                  <div className="mb-8 bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                    <div className="aspect-video bg-slate-900 rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <i className="fas fa-play-circle text-6xl text-cyan-400 mb-4"></i>
                        <div className="text-white/60">视频区域</div>
                        <div className="text-sm text-slate-500 mt-2">{currentChapter.video_url}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Content */}
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-8 border border-slate-700/50 mb-8">
                  <div className="prose prose-invert prose-lg max-w-none">
                    <div
                      className="text-white/80 leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: currentChapter.content }}
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setShowContent('intro')}
                    className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-colors font-medium"
                  >
                    <i className="fas fa-arrow-left mr-2"></i>
                    返回章节列表
                  </button>
                  <button
                    onClick={() => handleCompleteChapter(currentChapter.id)}
                    className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-xl transition-all font-medium"
                  >
                    <i className="fas fa-check mr-2"></i>
                    完成本章
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center text-slate-400 py-16">
                请选择一个章节开始学习
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default CourseLearnPage;

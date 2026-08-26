/**
 * 课程学习页面 - 通用课程学习组件
 * 支持多课程切换和学习进度追踪
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Loader2, AlertCircle, ArrowLeft, GraduationCap, BookOpen, PlayCircle, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeSanitize from 'rehype-sanitize';
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
  const location = useLocation();

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

  // 监听 URL 参数变化（chapterId）
  useEffect(() => {
    if (!course) return; // 课程未加载时不处理

    const urlParams = new URLSearchParams(window.location.search);
    const chapterIdParam = urlParams.get('chapterId');

    if (chapterIdParam) {
      // 找到对应章节
      const chapter = course.chapters.find((ch) => ch.id.toString() === chapterIdParam);
      if (chapter && currentChapter?.id !== chapter.id) {
        setCurrentChapter(chapter);
      }
    } else if (course.chapters.length > 0 && !currentChapter) {
      // 没有参数，默认选择第一个章节
      setCurrentChapter(course.chapters[0]);
    }
  }, [location.search, course, currentChapter]);

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

      // 从 URL 参数获取章节 ID（如果存在）
      const urlParams = new URLSearchParams(window.location.search);
      const chapterIdParam = urlParams.get('chapterId');

      if (chapterIdParam && data.chapters.length > 0) {
        // 找到对应章节
        const chapter = data.chapters.find((ch) => ch.id.toString() === chapterIdParam);
        setCurrentChapter(chapter || data.chapters[0]);
      } else if (data.chapters.length > 0) {
        // 没有参数，默认选择第一个章节
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
    // 同步更新 URL 参数
    navigate(`/courses/${slug}/learn?chapterId=${chapter.id}`, { replace: true });
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
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent mb-4 mx-auto" />
          <p className="text-ink-muted">正在加载课程...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-danger mb-4 mx-auto" />
          <p className="text-ink text-xl">课程不存在</p>
          <button
            onClick={() => navigate('/courses')}
            className="mt-4 px-6 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors"
          >
            返回课程列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas">
      {/* Header */}
      <header className="bg-surface-1/50 backdrop-blur-sm border-b border-border/50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(`/courses/${slug}`)}
                className="text-ink/80 hover:text-ink transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-ink">{course.title}</h1>
                <p className="text-sm text-ink-muted">
                  进度：{completedCount}/{course.chapters.length} 章节
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Progress Bar */}
              <div className="w-64">
                <div className="flex items-center justify-between text-sm text-ink-muted mb-1">
                  <span>学习进度</span>
                  <span>{Math.round(progressPercent)}%</span>
                </div>
                <div className="w-full h-2 bg-surface-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent to-accent-hover transition-all duration-300"
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
        <aside className="w-80 bg-surface-1/30 backdrop-blur-sm border-r border-border/50 overflow-y-auto">
          <div className="p-4">
            <h2 className="text-lg font-semibold text-ink mb-4">📚 课程章节</h2>
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
                        <h3 className="text-ink font-medium truncate">{chapter.title}</h3>
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

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-8 py-8">
            {!enrolled ? (
              /* 未报名状态 - 显示课程详情和报名表单 */
              <div className="max-w-3xl mx-auto">
                <div className="bg-surface-1/50 backdrop-blur-sm rounded-2xl border border-border/50 p-8 text-center">
                  <div className="mb-6">
                    <GraduationCap className="w-12 h-12 text-accent mx-auto" />
                  </div>
                  <h2 className="text-2xl font-bold text-ink mb-4">
                    报名课程以开始学习
                  </h2>
                  <p className="text-ink-muted mb-6">
                    {course.description}
                  </p>
                  <div className="flex items-center justify-center space-x-6 mb-6">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-ink">
                        {course.chapters.length}
                      </div>
                      <div className="text-sm text-ink-muted">章节</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-ink">
                        {course.statistics?.enroll_count || 0}
                      </div>
                      <div className="text-sm text-ink-muted">人在学</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-ink">
                        {course.statistics?.avg_rating?.toFixed(1) || '0.0'}
                      </div>
                      <div className="text-sm text-ink-muted">评分</div>
                    </div>
                  </div>
                  <button
                    onClick={handleEnroll}
                    className="px-8 py-4 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent-hover text-ink-inverse font-semibold rounded-xl transition-all hover:shadow-lg hover:shadow-accent/25"
                  >
                    <BookOpen className="w-4 h-4 mr-2 inline" />
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
                    <h2 className="text-3xl font-bold text-ink">{currentChapter.title}</h2>
                  </div>
                </div>

                {/* Video Section (if available) */}
                {currentChapter.video_url && (
                  <div className="mb-8 bg-surface-1/50 rounded-xl p-6 border border-border/50">
                    <div className="aspect-video bg-canvas rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <PlayCircle className="w-12 h-12 text-accent mb-4 mx-auto" />
                        <div className="text-ink/60">视频区域</div>
                        <div className="text-sm text-ink-faint mt-2">{currentChapter.video_url}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Content */}
                <div className="bg-surface-1/50 backdrop-blur-sm rounded-xl p-8 border border-border/50 mb-8">
                  <div className="prose prose-invert prose-lg max-w-none text-ink/80">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeHighlight, rehypeSanitize]}
                      components={{
                        // 自定义代码块渲染
                        code({ node, inline, className, children, ...props }: any) {
                          return inline ? (
                            <code className="px-1.5 py-0.5 bg-surface-2 rounded text-sm" {...props}>
                              {children}
                            </code>
                          ) : (
                            <code className="block p-4 bg-canvas rounded-lg overflow-x-auto text-sm" {...props}>
                              {children}
                            </code>
                          );
                        },
                        // 自定义链接渲染
                        a({ node, ...props }: any) {
                          return <a className="text-accent hover:text-accent underline" {...props} />;
                        },
                        // 自定义表格渲染
                        table({ node, ...props }: any) {
                          return <table className="min-w-full border border-border my-4" {...props} />;
                        },
                        th({ node, ...props }: any) {
                          return <th className="border border-border px-4 py-2 bg-surface-2 text-left" {...props} />;
                        },
                        td({ node, ...props }: any) {
                          return <td className="border border-border px-4 py-2" {...props} />;
                        },
                        // 自定义引用块渲染
                        blockquote({ node, ...props }: any) {
                          return <blockquote className="border-l-4 border-accent pl-4 italic my-4" {...props} />;
                        },
                      }}
                    >
                      {currentChapter.content}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setShowContent('intro')}
                    className="px-6 py-3 bg-surface-2 hover:bg-surface-3 text-ink rounded-xl transition-colors font-medium"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2 inline" />
                    返回章节列表
                  </button>
                  <button
                    onClick={() => handleCompleteChapter(currentChapter.id)}
                    className="px-6 py-3 bg-accent-success hover:bg-accent-success/90 text-ink-inverse rounded-xl transition-all font-medium"
                  >
                    <Check className="w-4 h-4 mr-2 inline" />
                    完成本章
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center text-ink-muted py-16">
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

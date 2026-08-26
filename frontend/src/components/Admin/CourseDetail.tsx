/**
 * 课程详情页 - 章节/测验/资源管理
 * UI 优化版本：改进视觉设计、Markdown 渲染、分离导入导出按钮
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Loader2, ArrowLeft, GraduationCap, Download, Upload, Pencil, Plus, Users, Star, BookOpen, ChevronRight, ClipboardCheck, FolderOpen } from 'lucide-react';
import { useChapterStore, useQuizStore, useResourceStore, useCourseAdminStore } from '../../stores/courseAdminStore';
import ChapterList from './CourseManagement/ChapterList';
import ChapterForm from './CourseManagement/ChapterForm';
import QuizManager from './CourseManagement/QuizManager';
import ResourceManager from './CourseManagement/ResourceManager';
import CourseEditor from './CourseManagement/CourseEditor';
import ImportExportDialog from './CourseManagement/ImportExportDialog';
import { useToast } from '../../hooks/useToast';
import 'highlight.js/styles/atom-one-dark.css';

type TabType = 'chapters' | 'quiz' | 'resources';

export default function CourseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast, error, success } = useToast();

  const { fetchChapters, chapters, selectedChapterId, selectChapter } = useChapterStore();
  const { courses, fetchCourses } = useCourseAdminStore();

  const [activeTab, setActiveTab] = useState<TabType>('chapters');
  const [showChapterForm, setShowChapterForm] = useState(false);
  const [showCourseEditor, setShowCourseEditor] = useState(false);
  const [showImportExportDialog, setShowImportExportDialog] = useState(false);
  const [importExportMode, setImportExportMode] = useState<'import' | 'export'>('export');
  const [editingChapterId, setEditingChapterId] = useState<number | null>(null);
  const [editingCourseId, setEditingCourseId] = useState<number | null>(null);
  // 课程介绍折叠状态，默认折叠
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);

  const courseId = id ? parseInt(id, 10) : null;
  const course = courses.find(c => c.id === courseId);

  useEffect(() => {
    if (courseId) {
      // 将课程 ID 存储到 localStorage，供 store 中的 API 调用使用
      localStorage.setItem('currentCourseId', courseId.toString());
      fetchChapters(courseId);
      fetchCourses({ page: 1, limit: 100 }); // 加载所有课程用于查找
    }
  }, [courseId]);

  const handleCreateChapter = () => {
    setEditingChapterId(null);
    setShowChapterForm(true);
  };

  const handleEditChapter = (chapterId: number) => {
    setEditingChapterId(chapterId);
    setShowChapterForm(true);
  };

  const handleEditCourse = () => {
    if (courseId) {
      setEditingCourseId(courseId);
      setShowCourseEditor(true);
    }
  };

  const handleCloseChapterForm = () => {
    setShowChapterForm(false);
    setEditingChapterId(null);
  };

  const handleCloseCourseEditor = () => {
    setShowCourseEditor(false);
    setEditingCourseId(null);
  };

  const handleCloseImportExportDialog = () => {
    setShowImportExportDialog(false);
    setImportExportMode('export');
  };

  const handleOpenExportDialog = () => {
    setImportExportMode('export');
    setShowImportExportDialog(true);
  };

  const handleOpenImportDialog = () => {
    setImportExportMode('import');
    setShowImportExportDialog(true);
  };

  const handleSelectChapter = (chapterId: number) => {
    selectChapter(chapterId);
  };

  const handleBackToList = () => {
    navigate('/admin/course');
  };

  const getTabIcon = (tab: TabType) => {
    switch (tab) {
      case 'chapters': return <BookOpen className="w-4 h-4" />;
      case 'quiz': return <ClipboardCheck className="w-4 h-4" />;
      case 'resources': return <FolderOpen className="w-4 h-4" />;
    }
  };

  const getTabLabel = (tab: TabType) => {
    switch (tab) {
      case 'chapters': return '章节管理';
      case 'quiz': return '测验管理';
      case 'resources': return '资源管理';
    }
  };

  if (!course) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-ink-muted">
        <Loader2 className="w-16 h-16 mb-4 animate-spin" />
        <p>加载中...</p>
      </div>
    );
  }

  return (
    <div className="bg-canvas">
      {/* ===== 优化后的 Header 区域 ===== */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-5">
          {/* 返回按钮 */}
          <button
            onClick={handleBackToList}
            className="group p-2.5 rounded-xl bg-surface-1/50 border border-border/50 hover:bg-surface-2/50 hover:border-accent/50 transition-all duration-200"
            title="返回课程列表"
          >
            <ArrowLeft className="w-5 h-5 text-ink-muted group-hover:text-accent transition-colors" />
          </button>

          {/* 课程标题 */}
          <div className="flex flex-col">
            <h1 className="text-3xl font-bold text-ink flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-hover flex items-center justify-center shadow-lg shadow-accent/20">
                <GraduationCap className="w-5 h-5 text-white" />
              </div>
              {course.title}
            </h1>
            <p className="text-ink-muted text-sm mt-1.5 ml-13 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-accent"></span>
              课程管理后台
            </p>
          </div>
        </div>

        {/* 操作按钮组 */}
        <div className="flex items-center gap-3">
          {/* 导出按钮 */}
          <button
            onClick={handleOpenExportDialog}
            className="group px-5 py-2.5 bg-gradient-to-r from-success/10 to-success/10 hover:from-success/20 hover:to-success/20 border border-success/30 hover:border-success/50 text-success rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-success/10 hover:shadow-success/20"
          >
            <Download className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span>导出</span>
          </button>

          {/* 导入按钮 */}
          <button
            onClick={handleOpenImportDialog}
            className="group px-5 py-2.5 bg-gradient-to-r from-warning/10 to-accent-warm/10 hover:from-warning/20 hover:to-accent-warm/20 border border-warning/30 hover:border-warning/50 text-warning rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-warning/10 hover:shadow-warning/20"
          >
            <Upload className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span>导入</span>
          </button>

          <div className="w-px h-8 bg-surface-2 mx-1"></div>

          {/* 编辑课程按钮 */}
          <button
            onClick={handleEditCourse}
            className="group px-5 py-2.5 bg-gradient-to-r from-accent-secondary/10 to-pink-500/10 hover:from-accent-secondary/20 hover:to-pink-500/20 border border-accent-secondary/30 hover:border-accent-secondary text-accent-secondary rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-accent-secondary/10 hover:shadow-accent-secondary/20"
          >
            <Pencil className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span>编辑课程</span>
          </button>

          {/* 新增章节按钮 - 主要操作 */}
          <button
            onClick={handleCreateChapter}
            className="group px-5 py-2.5 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent-hover text-white rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-accent/30 hover:shadow-accent/50 hover:-translate-y-0.5"
          >
            <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-200" />
            <span>新增章节</span>
          </button>
        </div>
      </div>

      {/* ===== 优化后的课程信息卡片 ===== */}
      <div className="bg-gradient-to-br bg-surface-1/80 to-bg-surface-1/40 rounded-2xl border border-border/50 p-4 mb-4 backdrop-blur-sm">
        <div className="flex items-start gap-6">
          {/* 课程封面 */}
          {course.cover_image && (
            <div className="relative group flex-shrink-0">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-accent to-accent-hover rounded-xl opacity-30 group-hover:opacity-50 transition-opacity blur"></div>
              <img
                src={course.cover_image}
                alt={course.title}
                className="relative w-48 h-32 object-cover rounded-xl shadow-lg"
              />
            </div>
          )}

          {/* 课程信息 */}
          <div className="flex-1 min-w-0">
            {/* 状态和统计指标 */}
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <span
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-medium ${
                  course.status === 'published'
                    ? 'bg-success/20 text-success border border-success/30'
                    : course.status === 'draft'
                    ? 'bg-surface-3/20 text-ink-muted border border-surface-3/30'
                    : 'bg-accent-warm/20 text-accent-warm border border-accent-warm/30'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${
                  course.status === 'published' ? 'bg-success animate-pulse' :
                  course.status === 'draft' ? 'bg-surface-3' : 'bg-accent-warm'
                }`}></span>
                {course.status === 'published' ? '已发布' : course.status === 'draft' ? '草稿' : '已归档'}
              </span>

              <div className="flex items-center gap-4 text-ink-muted text-sm">
                <span className="flex items-center gap-1.5 hover:text-accent transition-colors">
                  <div className="w-5 h-5 rounded-lg bg-surface-2/50 flex items-center justify-center">
                    <Users className="w-3 h-3" />
                  </div>
                  {course.statistics?.enroll_count || 0} 人学习
                </span>
                <span className="flex items-center gap-1.5 hover:text-warning transition-colors">
                  <div className="w-5 h-5 rounded-lg bg-surface-2/50 flex items-center justify-center">
                    <Star className="w-3 h-3" />
                  </div>
                  {course.statistics?.avg_rating ? course.statistics.avg_rating.toFixed(1) : '0.0'} 分
                </span>
                <span className="flex items-center gap-1.5 hover:text-accent-secondary transition-colors">
                  <div className="w-5 h-5 rounded-lg bg-surface-2/50 flex items-center justify-center">
                    <BookOpen className="w-3 h-3" />
                  </div>
                  {chapters.length} 个章节
                </span>
              </div>
            </div>

            {/* 课程简介 - 可折叠区域 */}
            <div>
              {/* 折叠/展开按钮 */}
              <button
                onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
                className="flex items-center gap-2 text-sm text-ink-muted hover:text-accent transition-colors mb-2"
              >
                <ChevronRight className={`w-3 h-3 transition-transform duration-200 ${isDescriptionExpanded ? 'rotate-90' : ''}`} />
                <span className="font-medium">课程简介</span>
              </button>

              {/* 可折叠的简介内容 */}
              {isDescriptionExpanded && (
                <div className="prose prose-invert prose-sm max-w-none pl-5">
                  <div className="text-ink-muted leading-relaxed">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeHighlight]}
                      components={{
                        p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                        strong: ({children}) => <strong className="text-ink font-semibold">{children}</strong>,
                        em: ({children}) => <em className="text-accent">{children}</em>,
                        h1: ({children}) => <h1 className="text-xl font-bold text-ink mb-3">{children}</h1>,
                        h2: ({children}) => <h2 className="text-lg font-semibold text-ink mb-2">{children}</h2>,
                        h3: ({children}) => <h3 className="text-base font-medium text-ink mb-1">{children}</h3>,
                        ul: ({children}) => <ul className="list-disc list-inside space-y-1 my-2 text-ink-muted">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal list-inside space-y-1 my-2 text-ink-muted">{children}</ol>,
                        li: ({children}) => <li className="text-ink-muted">{children}</li>,
                        code: ({children}) => <code className="px-1.5 py-0.5 bg-surface-2/50 rounded text-danger text-xs">{children}</code>,
                        pre: ({children}) => <pre className="bg-canvas/50 rounded-lg p-3 my-2 overflow-x-auto border border-border/30">{children}</pre>,
                        blockquote: ({children}) => <blockquote className="border-l-4 border-accent/50 pl-4 my-2 text-ink-muted italic">{children}</blockquote>,
                      }}
                    >
                      {course.description || '_暂无课程简介_'}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ===== 优化后的 Tabs 标签页 ===== */}
      <div className="flex items-center gap-2 border-b border-border/50 mb-4">
        {(['chapters', 'quiz', 'resources'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`group relative px-5 py-3 font-medium transition-all duration-200 rounded-t-lg ${
              activeTab === tab
                ? 'text-accent'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            {/* 选中背景 */}
            {activeTab === tab && (
              <div className="absolute inset-0 bg-gradient-to-r from-accent/10 to-accent-hover/10 rounded-t-lg"></div>
            )}

            {/* 选中指示线 */}
            {activeTab === tab && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-accent to-accent-hover rounded-t-full"></div>
            )}

            {/* 标签内容 */}
            <span className={`relative flex items-center gap-2 ${
                activeTab === tab ? 'text-accent' : 'group-hover:text-ink transition-colors'
              }`}>
                {getTabIcon(tab)}
                {getTabLabel(tab)}
              </span>
          </button>
        ))}
      </div>

      {/* ===== Content 内容区域 ===== */}
      <div className="bg-surface-1/30 rounded-2xl border border-border/50 p-4 backdrop-blur-sm">
        {activeTab === 'chapters' && (
          <ChapterList
            chapters={chapters}
            onEdit={handleEditChapter}
            onSelect={handleSelectChapter}
            selectedChapterId={selectedChapterId}
          />
        )}
        {activeTab === 'quiz' && (
          <QuizManager
            chapters={chapters}
            selectedChapterId={selectedChapterId}
            onSelectChapter={handleSelectChapter}
          />
        )}
        {activeTab === 'resources' && (
          <ResourceManager
            chapters={chapters}
            selectedChapterId={selectedChapterId}
            onSelectChapter={handleSelectChapter}
          />
        )}
      </div>

      {/* Chapter Form Modal */}
      {showChapterForm && (
        <ChapterForm
          chapterId={editingChapterId}
          onClose={handleCloseChapterForm}
        />
      )}

      {/* Course Editor Modal */}
      {showCourseEditor && (
        <CourseEditor
          courseId={editingCourseId || undefined}
          onClose={handleCloseCourseEditor}
        />
      )}

      {/* Import/Export Dialog Modal */}
      {showImportExportDialog && (
        <ImportExportDialog
          courseId={courseId || undefined}
          courseTitle={course?.title}
          mode={importExportMode}
          onClose={handleCloseImportExportDialog}
          onImportSuccess={() => {
            fetchChapters();
            success('导入成功，章节列表已更新');
          }}
        />
      )}
    </div>
  );
}

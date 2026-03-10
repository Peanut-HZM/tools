/**
 * 课程详情页 - 章节/测验/资源管理
 * UI 优化版本：改进视觉设计、Markdown 渲染、分离导入导出按钮
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { useChapterStore, useQuizStore, useResourceStore, useCourseAdminStore } from '../../stores/courseAdminStore';
import ChapterList from './CourseManagement/ChapterList';
import ChapterForm from './CourseManagement/ChapterForm';
import QuizManager from './CourseManagement/QuizManager';
import ResourceManager from './CourseManagement/ResourceManager';
import CourseEditor from './CourseManagement/CourseEditor';
import ImportExportDialog from './CourseManagement/ImportExportDialog';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';
import 'highlight.js/styles/atom-one-dark.css';

type TabType = 'chapters' | 'quiz' | 'resources';

export default function CourseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toasts, addToast, removeToast, error, success } = useToast();

  const { fetchChapters, chapters, selectedChapterId, selectChapter } = useChapterStore();
  const { courses, fetchCourses } = useCourseAdminStore();

  const [activeTab, setActiveTab] = useState<TabType>('chapters');
  const [showChapterForm, setShowChapterForm] = useState(false);
  const [showCourseEditor, setShowCourseEditor] = useState(false);
  const [showImportExportDialog, setShowImportExportDialog] = useState(false);
  const [importExportMode, setImportExportMode] = useState<'import' | 'export'>('export');
  const [editingChapterId, setEditingChapterId] = useState<number | null>(null);
  const [editingCourseId, setEditingCourseId] = useState<number | null>(null);

  const courseId = id ? parseInt(id, 10) : null;
  const course = courses.find(c => c.id === courseId);

  useEffect(() => {
    if (courseId) {
      fetchChapters();
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
      case 'chapters': return 'fa-book';
      case 'quiz': return 'fa-clipboard-check';
      case 'resources': return 'fa-folder-open';
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
      <div className="h-full flex flex-col items-center justify-center text-slate-400">
        <i className="fas fa-spinner fa-spin text-4xl mb-4"></i>
        <p>加载中...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-900">
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />

      {/* ===== 优化后的 Header 区域 ===== */}
      <div className="flex items-center justify-between mb-8 px-2">
        <div className="flex items-center gap-5">
          {/* 返回按钮 */}
          <button
            onClick={handleBackToList}
            className="group p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 hover:border-cyan-500/50 transition-all duration-200"
            title="返回课程列表"
          >
            <i className="fas fa-arrow-left text-slate-400 group-hover:text-cyan-400 transition-colors"></i>
          </button>

          {/* 课程标题 */}
          <div className="flex flex-col">
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <i className="fas fa-graduation-cap text-white text-lg"></i>
              </div>
              {course.title}
            </h1>
            <p className="text-slate-400 text-sm mt-1.5 ml-13 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500"></span>
              课程管理后台
            </p>
          </div>
        </div>

        {/* 操作按钮组 */}
        <div className="flex items-center gap-3">
          {/* 导出按钮 */}
          <button
            onClick={handleOpenExportDialog}
            className="group px-5 py-2.5 bg-gradient-to-r from-emerald-500/10 to-green-500/10 hover:from-emerald-500/20 hover:to-green-500/20 border border-emerald-500/30 hover:border-emerald-400/50 text-emerald-400 rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-emerald-500/10 hover:shadow-emerald-500/20"
          >
            <i className="fas fa-download group-hover:scale-110 transition-transform"></i>
            <span>导出</span>
          </button>

          {/* 导入按钮 */}
          <button
            onClick={handleOpenImportDialog}
            className="group px-5 py-2.5 bg-gradient-to-r from-amber-500/10 to-orange-500/10 hover:from-amber-500/20 hover:to-orange-500/20 border border-amber-500/30 hover:border-amber-400/50 text-amber-400 rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-amber-500/10 hover:shadow-amber-500/20"
          >
            <i className="fas fa-upload group-hover:scale-110 transition-transform"></i>
            <span>导入</span>
          </button>

          <div className="w-px h-8 bg-slate-700 mx-1"></div>

          {/* 编辑课程按钮 */}
          <button
            onClick={handleEditCourse}
            className="group px-5 py-2.5 bg-gradient-to-r from-purple-500/10 to-pink-500/10 hover:from-purple-500/20 hover:to-pink-500/20 border border-purple-500/30 hover:border-purple-400/50 text-purple-400 rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-purple-500/10 hover:shadow-purple-500/20"
          >
            <i className="fas fa-pen-to-square group-hover:scale-110 transition-transform"></i>
            <span>编辑课程</span>
          </button>

          {/* 新增章节按钮 - 主要操作 */}
          <button
            onClick={handleCreateChapter}
            className="group px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-xl transition-all duration-200 font-medium flex items-center gap-2 shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 hover:-translate-y-0.5"
          >
            <i className="fas fa-plus group-hover:rotate-90 transition-transform duration-200"></i>
            <span>新增章节</span>
          </button>
        </div>
      </div>

      {/* ===== 优化后的课程信息卡片 ===== */}
      <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl border border-slate-700/50 p-6 mb-6 backdrop-blur-sm">
        <div className="flex items-start gap-6">
          {/* 课程封面 */}
          {course.cover_image && (
            <div className="relative group flex-shrink-0">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl opacity-30 group-hover:opacity-50 transition-opacity blur"></div>
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
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                    : course.status === 'draft'
                    ? 'bg-slate-600/20 text-slate-400 border border-slate-500/30'
                    : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${
                  course.status === 'published' ? 'bg-green-400 animate-pulse' :
                  course.status === 'draft' ? 'bg-slate-400' : 'bg-orange-400'
                }`}></span>
                {course.status === 'published' ? '已发布' : course.status === 'draft' ? '草稿' : '已归档'}
              </span>

              <div className="flex items-center gap-4 text-slate-400 text-sm">
                <span className="flex items-center gap-1.5 hover:text-cyan-400 transition-colors">
                  <div className="w-5 h-5 rounded-lg bg-slate-700/50 flex items-center justify-center">
                    <i className="fas fa-users text-xs"></i>
                  </div>
                  {course.statistics?.enroll_count || 0} 人学习
                </span>
                <span className="flex items-center gap-1.5 hover:text-amber-400 transition-colors">
                  <div className="w-5 h-5 rounded-lg bg-slate-700/50 flex items-center justify-center">
                    <i className="fas fa-star text-xs"></i>
                  </div>
                  {course.statistics?.avg_rating ? course.statistics.avg_rating.toFixed(1) : '0.0'} 分
                </span>
                <span className="flex items-center gap-1.5 hover:text-purple-400 transition-colors">
                  <div className="w-5 h-5 rounded-lg bg-slate-700/50 flex items-center justify-center">
                    <i className="fas fa-book text-xs"></i>
                  </div>
                  {chapters.length} 个章节
                </span>
              </div>
            </div>

            {/* 课程简介 - Markdown 渲染 */}
            <div className="prose prose-invert prose-sm max-w-none">
              <div className="text-slate-300 leading-relaxed">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                    strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
                    em: ({children}) => <em className="text-cyan-300">{children}</em>,
                    h1: ({children}) => <h1 className="text-xl font-bold text-white mb-3">{children}</h1>,
                    h2: ({children}) => <h2 className="text-lg font-semibold text-white mb-2">{children}</h2>,
                    h3: ({children}) => <h3 className="text-base font-medium text-white mb-1">{children}</h3>,
                    ul: ({children}) => <ul className="list-disc list-inside space-y-1 my-2 text-slate-400">{children}</ul>,
                    ol: ({children}) => <ol className="list-decimal list-inside space-y-1 my-2 text-slate-400">{children}</ol>,
                    li: ({children}) => <li className="text-slate-300">{children}</li>,
                    code: ({children}) => <code className="px-1.5 py-0.5 bg-slate-700/50 rounded text-pink-400 text-xs">{children}</code>,
                    pre: ({children}) => <pre className="bg-slate-900/50 rounded-lg p-3 my-2 overflow-x-auto border border-slate-700/30">{children}</pre>,
                    blockquote: ({children}) => <blockquote className="border-l-4 border-cyan-500/50 pl-4 my-2 text-slate-400 italic">{children}</blockquote>,
                  }}
                >
                  {course.description || '_暂无课程简介_'}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ===== 优化后的 Tabs 标签页 ===== */}
      <div className="flex items-center gap-2 border-b border-slate-700/50 mb-6">
        {(['chapters', 'quiz', 'resources'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`group relative px-5 py-3 font-medium transition-all duration-200 rounded-t-lg ${
              activeTab === tab
                ? 'text-cyan-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {/* 选中背景 */}
            {activeTab === tab && (
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-t-lg"></div>
            )}

            {/* 选中指示线 */}
            {activeTab === tab && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-400 to-blue-400 rounded-t-full"></div>
            )}

            {/* 标签内容 */}
            <span className="relative flex items-center gap-2">
              <i className={`fas ${getTabIcon(tab)} ${
                activeTab === tab ? 'text-cyan-400' : 'group-hover:text-white transition-colors'
              }`}></i>
              {getTabLabel(tab)}
            </span>
          </button>
        ))}
      </div>

      {/* ===== Content 内容区域 ===== */}
      <div className="flex-1 overflow-hidden bg-slate-800/30 rounded-2xl border border-slate-700/50 p-5 backdrop-blur-sm">
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

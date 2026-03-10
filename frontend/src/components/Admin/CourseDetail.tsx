/**
 * 课程详情页 - 章节/测验/资源管理
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChapterStore, useQuizStore, useResourceStore, useCourseAdminStore } from '../../stores/courseAdminStore';
import ChapterList from './CourseManagement/ChapterList';
import ChapterForm from './CourseManagement/ChapterForm';
import QuizManager from './CourseManagement/QuizManager';
import ResourceManager from './CourseManagement/ResourceManager';
import CourseEditor from './CourseManagement/CourseEditor';
import ImportExportDialog from './CourseManagement/ImportExportDialog';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';

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
    <div className="h-full flex flex-col">
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBackToList}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <i className="fas fa-arrow-left text-slate-400 hover:text-white"></i>
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <i className="fas fa-graduation-cap text-cyan-400"></i>
              {course.title}
            </h1>
            <p className="text-slate-400 text-sm mt-1">{course.description}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowImportExportDialog(true)}
            className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-green-500/20 hover:shadow-green-500/30 hover:-translate-y-0.5 flex items-center"
          >
            <i className="fas fa-file-import mr-2"></i>
            导入/导出
          </button>
          <button
            onClick={handleEditCourse}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 hover:-translate-y-0.5 flex items-center"
          >
            <i className="fas fa-edit mr-2"></i>
            编辑课程
          </button>
          <button
            onClick={handleCreateChapter}
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 hover:-translate-y-0.5 flex items-center"
          >
            <i className="fas fa-plus mr-2"></i>
            新增章节
          </button>
        </div>
      </div>

      {/* 课程信息卡片 */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 mb-6">
        <div className="flex items-start gap-6">
          {course.cover_image && (
            <img
              src={course.cover_image}
              alt={course.title}
              className="w-48 h-32 object-cover rounded-lg"
            />
          )}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <span
                className={`px-3 py-1 rounded-full text-sm ${
                  course.status === 'published'
                    ? 'bg-green-500/20 text-green-400'
                    : course.status === 'draft'
                    ? 'bg-slate-600/20 text-slate-400'
                    : 'bg-orange-500/20 text-orange-400'
                }`}
              >
                {course.status === 'published' ? '已发布' : course.status === 'draft' ? '草稿' : '已归档'}
              </span>
              <span className="text-slate-400 text-sm">
                <i className="fas fa-users mr-1"></i>
                {course.statistics?.enroll_count || 0} 人学习
              </span>
              <span className="text-slate-400 text-sm">
                <i className="fas fa-star mr-1"></i>
                {course.statistics?.avg_rating ? course.statistics.avg_rating.toFixed(1) : '0.0'} 分
              </span>
              <span className="text-slate-400 text-sm">
                <i className="fas fa-book mr-1"></i>
                {chapters.length} 个章节
              </span>
            </div>
            <p className="text-slate-300">{course.description}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-700/50 mb-6">
        {(['chapters', 'quiz', 'resources'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 font-medium transition-all duration-200 rounded-t-lg ${
              activeTab === tab
                ? 'bg-gradient-to-r from-cyan-500/10 to-blue-500/10 text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/30'
            }`}
          >
            <i className={`fas ${getTabIcon(tab)} mr-2`}></i>
            {getTabLabel(tab)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden bg-slate-800/30 rounded-xl border border-slate-700/50 p-4">
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

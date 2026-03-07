/**
 * 课程管理主页面
 */
import React, { useState, useEffect } from 'react';
import { useChapterStore, useQuizStore, useResourceStore, useCourseAdminStore } from '../../stores/courseAdminStore';
import ChapterList from './CourseManagement/ChapterList';
import ChapterForm from './CourseManagement/ChapterForm';
import QuizManager from './CourseManagement/QuizManager';
import ResourceManager from './CourseManagement/ResourceManager';
import CourseEditor from './CourseManagement/CourseEditor';

type TabType = 'chapters' | 'quiz' | 'resources';

const CourseManagement: React.FC = () => {
  const { fetchChapters, chapters, selectedChapterId, selectChapter } = useChapterStore();
  const { fetchCourses, courses } = useCourseAdminStore();
  const [activeTab, setActiveTab] = useState<TabType>('chapters');
  const [showChapterForm, setShowChapterForm] = useState(false);
  const [showCourseEditor, setShowCourseEditor] = useState(false);
  const [editingChapterId, setEditingChapterId] = useState<number | null>(null);
  const [editingCourseId, setEditingCourseId] = useState<number | null>(null);

  useEffect(() => {
    fetchChapters();
    fetchCourses();
  }, []);

  const handleCreateChapter = () => {
    setEditingChapterId(null);
    setShowChapterForm(true);
  };

  const handleEditChapter = (chapterId: number) => {
    setEditingChapterId(chapterId);
    setShowChapterForm(true);
  };

  const handleCreateCourse = () => {
    setEditingCourseId(null);
    setShowCourseEditor(true);
  };

  const handleEditCourse = (courseId: number) => {
    setEditingCourseId(courseId);
    setShowCourseEditor(true);
  };

  const handleCloseChapterForm = () => {
    setShowChapterForm(false);
    setEditingChapterId(null);
  };

  const handleCloseCourseEditor = () => {
    setShowCourseEditor(false);
    setEditingCourseId(null);
  };

  const handleSelectChapter = (chapterId: number) => {
    selectChapter(chapterId);
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center">
            <i className="fas fa-graduation-cap text-cyan-400 mr-3"></i>
            课程管理
          </h1>
          <p className="text-slate-400 text-sm mt-1">管理课程内容和章节</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleCreateCourse}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 hover:-translate-y-0.5 flex items-center"
          >
            <i className="fas fa-plus mr-2"></i>
            新增课程
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

      {/* Course List */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white mb-3">课程列表</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map((course) => (
            <div
              key={course.id}
              className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 hover:border-cyan-500/50 transition-all cursor-pointer group"
              onClick={() => handleEditCourse(course.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-white font-semibold mb-2 group-hover:text-cyan-400 transition-colors">
                    {course.title}
                  </h3>
                  <p className="text-slate-400 text-sm line-clamp-2 mb-3">
                    {course.description}
                  </p>
                  <div className="flex items-center space-x-3 text-xs">
                    <span className={`px-2 py-1 rounded-full ${
                      course.is_published
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-slate-600/20 text-slate-400'
                    }`}>
                      {course.is_published ? '已发布' : '未发布'}
                    </span>
                    <span className="text-slate-500">
                      <i className="fas fa-book mr-1"></i>
                      {course.statistics?.enroll_count || 0} 人学习
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEditCourse(course.id);
                  }}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  <i className="fas fa-edit text-slate-400 hover:text-cyan-400"></i>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-700/50 mb-6">
        {(Object.keys(['chapters', 'quiz', 'resources']) as TabType[]).map((tab) => (
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
    </div>
  );
};

export default CourseManagement;

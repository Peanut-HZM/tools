/**
 * 课程管理主页面
 */
import React, { useState, useEffect } from 'react';
import { useChapterStore, useQuizStore, useResourceStore } from '../../stores/courseAdminStore';
import ChapterList from './CourseManagement/ChapterList';
import ChapterForm from './CourseManagement/ChapterForm';
import QuizManager from './CourseManagement/QuizManager';
import ResourceManager from './CourseManagement/ResourceManager';

type TabType = 'chapters' | 'quiz' | 'resources';

const CourseManagement: React.FC = () => {
  const { fetchChapters, chapters, selectedChapterId, selectChapter } = useChapterStore();
  const [activeTab, setActiveTab] = useState<TabType>('chapters');
  const [showChapterForm, setShowChapterForm] = useState(false);
  const [editingChapterId, setEditingChapterId] = useState<number | null>(null);

  useEffect(() => {
    fetchChapters();
  }, []);

  const handleCreateChapter = () => {
    setEditingChapterId(null);
    setShowChapterForm(true);
  };

  const handleEditChapter = (chapterId: number) => {
    setEditingChapterId(chapterId);
    setShowChapterForm(true);
  };

  const handleCloseForm = () => {
    setShowChapterForm(false);
    setEditingChapterId(null);
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
          <p className="text-slate-400 text-sm mt-1">管理 OpenSpec VibeCoding 课程内容</p>
        </div>
        <button
          onClick={handleCreateChapter}
          className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 hover:-translate-y-0.5 flex items-center"
        >
          <i className="fas fa-plus mr-2"></i>
          新增章节
        </button>
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
          onClose={handleCloseForm}
        />
      )}
    </div>
  );
};

export default CourseManagement;

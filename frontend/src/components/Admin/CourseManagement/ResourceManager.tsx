/**
 * 资源管理组件
 */
import React, { useState } from 'react';
import { useResourceStore } from '../../../stores/courseAdminStore';
import type { Chapter } from '../../../services/openspecCourseAdmin';
import ResourceForm from './ResourceForm';

interface ResourceManagerProps {
  chapters: Chapter[];
  selectedChapterId: number | null;
  onSelectChapter: (chapterId: number) => void;
}

const ResourceManager: React.FC<ResourceManagerProps> = ({
  chapters,
  selectedChapterId,
  onSelectChapter,
}) => {
  const { resources, fetchResources } = useResourceStore();
  const [showResourceForm, setShowResourceForm] = useState(false);
  const [editingResourceId, setEditingResourceId] = useState<number | null>(null);
  const [loadingResourceId, setLoadingResourceId] = useState<number | null>(null);

  const handleSelectChapter = async (chapterId: number) => {
    onSelectChapter(chapterId);
    setLoadingResourceId(chapterId);
    try {
      await fetchResources(chapterId);
    } catch (error) {
      console.error('获取资源失败:', error);
    } finally {
      setLoadingResourceId(null);
    }
  };

  const handleCreateResource = () => {
    if (!selectedChapterId) {
      alert('请先选择一个章节');
      return;
    }
    setEditingResourceId(null);
    setShowResourceForm(true);
  };

  const handleEditResource = (resourceId: number) => {
    setEditingResourceId(resourceId);
    setShowResourceForm(true);
  };

  const handleCloseForm = () => {
    setShowResourceForm(false);
    setEditingResourceId(null);
  };

  const selectedResources = selectedChapterId ? (resources[selectedChapterId] || []) : [];

  const getResourceIcon = (type: string) => {
    const icons: Record<string, string> = {
      code_sample: 'fa-code',
      contrast: 'fa-scale-balanced',
      video: 'fa-video',
      template: 'fa-file-lines',
    };
    return icons[type] || 'fa-file';
  };

  const getResourceColor = (type: string) => {
    const colors: Record<string, string> = {
      code_sample: 'from-blue-500 to-cyan-500',
      contrast: 'from-purple-500 to-pink-500',
      video: 'from-red-500 to-orange-500',
      template: 'from-green-500 to-emerald-500',
    };
    return colors[type] || 'from-slate-500 to-gray-500';
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      code_sample: '代码示例',
      contrast: '对比材料',
      video: '视频',
      template: '模板',
    };
    return labels[type] || type;
  };

  return (
    <div className="h-full flex">
      {/* Chapter List */}
      <div className="w-80 border-r border-slate-700/50 pr-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center">
            <i className="fas fa-book mr-2 text-cyan-400"></i>
            选择章节
          </h3>
          <p className="text-slate-500 text-sm mt-1">点击章节加载对应资源</p>
        </div>
        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-300px)]">
          {chapters.map((chapter) => {
            const resourceCount = resources[chapter.id]?.length || 0;
            return (
              <button
                key={chapter.id}
                onClick={() => handleSelectChapter(chapter.id)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-200 ${
                  selectedChapterId === chapter.id
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 border border-cyan-500/50 shadow-lg shadow-cyan-500/10'
                    : 'bg-slate-700/30 border border-slate-700/50 hover:bg-slate-700/50 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium truncate">{chapter.title}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center px-2 py-1 bg-slate-600/50 text-slate-400 border border-slate-600/30 rounded text-xs">
                    <i className="fas fa-folder mr-1"></i>
                    {resourceCount} 个资源
                  </span>
                  <span className="text-slate-500 text-xs">{chapter.chapter_type}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Resource Content */}
      <div className="flex-1 pl-4">
        {selectedChapterId ? (
          <>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-bold text-white flex items-center">
                  <i className="fas fa-folder-open text-cyan-400 mr-3"></i>
                  资源：{chapters.find((c) => c.id === selectedChapterId)?.title}
                </h3>
                <p className="text-slate-400 text-sm mt-1">管理和编辑章节学习资源</p>
              </div>
              <button
                onClick={handleCreateResource}
                className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 flex items-center"
              >
                <i className="fas fa-plus mr-2"></i>
                添加资源
              </button>
            </div>

            {loadingResourceId === selectedChapterId ? (
              <div className="flex items-center justify-center py-16">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500 mx-auto mb-4"></div>
                  <p className="text-slate-400">加载中...</p>
                </div>
              </div>
            ) : selectedResources.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedResources.map((resource) => (
                  <div
                    key={resource.id}
                    className="group bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-5 border border-slate-700/50 hover:border-slate-600 transition-all duration-200 hover:shadow-lg"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <div className={`w-12 h-12 bg-gradient-to-br ${getResourceColor(resource.resource_type)} rounded-xl flex items-center justify-center`}>
                          <i className={`fas ${getResourceIcon(resource.resource_type)} text-white text-lg`}></i>
                        </div>
                        <div>
                          <h4 className="text-white font-semibold">{resource.title}</h4>
                          <p className="text-slate-400 text-sm">{getTypeLabel(resource.resource_type)}</p>
                        </div>
                      </div>
                    </div>
                    <p className="text-slate-500 text-sm line-clamp-2 mb-4">{resource.content.substring(0, 100)}...</p>
                    <div className="flex items-center space-x-2 pt-3 border-t border-slate-700/50">
                      <button
                        onClick={() => handleEditResource(resource.id)}
                        className="flex-1 px-3 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-sm transition-all text-center"
                      >
                        <i className="fas fa-edit mr-1"></i>编辑
                      </button>
                      <button
                        onClick={async () => {
                          if (confirm('确定要删除这个资源吗？')) {
                            // TODO: 调用 deleteResource
                          }
                        }}
                        className="px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg text-sm transition-all"
                      >
                        <i className="fas fa-trash"></i>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center py-16">
                <div className="text-center max-w-md">
                  <div className="w-24 h-24 bg-slate-700/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <i className="fas fa-folder-open text-5xl text-slate-500"></i>
                  </div>
                  <p className="text-white text-lg font-medium mb-2">该章节还没有资源</p>
                  <p className="text-slate-400 text-sm mb-6">添加学习资源来帮助理解课程内容</p>
                  <button
                    onClick={handleCreateResource}
                    className="px-8 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 inline-flex items-center"
                  >
                    <i className="fas fa-plus mr-2"></i>
                    添加资源
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <div className="w-20 h-20 bg-slate-700/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-arrow-left text-3xl text-slate-500"></i>
              </div>
              <p className="text-slate-400">请从左侧选择一个章节</p>
            </div>
          </div>
        )}
      </div>

      {/* Resource Form Modal */}
      {showResourceForm && (
        <ResourceForm
          chapterId={selectedChapterId!}
          resourceId={editingResourceId}
          onClose={handleCloseForm}
        />
      )}
    </div>
  );
};

export default ResourceManager;

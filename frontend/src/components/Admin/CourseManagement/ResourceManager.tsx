/**
 * 资源管理组件
 */
import React, { useState } from 'react';
import { useResourceStore } from '../../../stores/courseAdminStore';
import type { CourseChapter as Chapter } from '../../../services/coursePlatform';
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
      <div className="w-80 border-r border-border/50 pr-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-ink-inverse flex items-center">
            <i className="fas fa-book mr-2 text-accent"></i>
            选择章节
          </h3>
          <p className="text-ink-faint text-sm mt-1">点击章节加载对应资源</p>
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
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 border border-accent shadow-lg shadow-cyan-500/10'
                    : 'bg-surface-2/30 border border-border/50 hover:bg-surface-2/50 hover:border-border'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-ink-inverse font-medium truncate">{chapter.title}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center px-2 py-1 bg-surface-3/50 text-ink-muted border border-border/50 rounded text-xs">
                    <i className="fas fa-folder mr-1"></i>
                    {resourceCount} 个资源
                  </span>
                  <span className="text-ink-faint text-xs">{chapter.chapter_type}</span>
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
                <h3 className="text-2xl font-bold text-ink-inverse flex items-center">
                  <i className="fas fa-folder-open text-accent mr-3"></i>
                  资源：{chapters.find((c) => c.id === selectedChapterId)?.title}
                </h3>
                <p className="text-ink-muted text-sm mt-1">管理和编辑章节学习资源</p>
              </div>
              <button
                onClick={handleCreateResource}
                className="px-6 py-3 bg-gradient-to-r from-accent to-accent-hover text-ink-inverse rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 flex items-center"
              >
                <i className="fas fa-plus mr-2"></i>
                添加资源
              </button>
            </div>

            {loadingResourceId === selectedChapterId ? (
              <div className="flex items-center justify-center py-16">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500 mx-auto mb-4"></div>
                  <p className="text-ink-muted">加载中...</p>
                </div>
              </div>
            ) : selectedResources.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedResources.map((resource) => (
                  <div
                    key={resource.id}
                    className="group bg-gradient-to-br bg-surface-1 rounded-xl p-5 border border-border/50 hover:border-border transition-all duration-200 hover:shadow-lg"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <div className={`w-12 h-12 bg-gradient-to-br ${getResourceColor(resource.resource_type)} rounded-xl flex items-center justify-center`}>
                          <i className={`fas ${getResourceIcon(resource.resource_type)} text-ink-inverse text-lg`}></i>
                        </div>
                        <div>
                          <h4 className="text-ink-inverse font-semibold">{resource.title}</h4>
                          <p className="text-ink-muted text-sm">{getTypeLabel(resource.resource_type)}</p>
                        </div>
                      </div>
                    </div>
                    <p className="text-ink-faint text-sm line-clamp-2 mb-4">{resource.content.substring(0, 100)}...</p>
                    <div className="flex items-center space-x-2 pt-3 border-t border-border/50">
                      <button
                        onClick={() => handleEditResource(resource.id)}
                        className="flex-1 px-3 py-2 bg-accent/10 hover:bg-accent/20 text-accent border border-accent/30 rounded-lg text-sm transition-all text-center"
                      >
                        <i className="fas fa-edit mr-1"></i>编辑
                      </button>
                      <button
                        onClick={async () => {
                          if (confirm('确定要删除这个资源吗？')) {
                            // TODO: 调用 deleteResource
                          }
                        }}
                        className="px-3 py-2 bg-danger/10 hover:bg-danger/20 text-danger border border-danger/30 rounded-lg text-sm transition-all"
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
                  <div className="w-24 h-24 bg-surface-2/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <i className="fas fa-folder-open text-5xl text-ink-faint"></i>
                  </div>
                  <p className="text-ink-inverse text-lg font-medium mb-2">该章节还没有资源</p>
                  <p className="text-ink-muted text-sm mb-6">添加学习资源来帮助理解课程内容</p>
                  <button
                    onClick={handleCreateResource}
                    className="px-8 py-3 bg-gradient-to-r from-accent to-accent-hover text-ink-inverse rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 inline-flex items-center"
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
              <div className="w-20 h-20 bg-surface-2/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="fas fa-arrow-left text-3xl text-ink-faint"></i>
              </div>
              <p className="text-ink-muted">请从左侧选择一个章节</p>
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

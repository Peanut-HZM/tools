/**
 * 资源表单组件
 */
import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { useResourceStore } from '../../../stores/courseAdminStore';
import type { ResourceCreate, ResourceUpdate, CourseResource as Resource } from '../../../services/coursePlatform';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface ResourceFormProps {
  chapterId: number;
  resourceId: number | null;
  onClose: () => void;
}

const ResourceForm: React.FC<ResourceFormProps> = ({ chapterId, resourceId, onClose }) => {
  const { createResource, updateResource, resources } = useResourceStore();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<Partial<ResourceCreate>>({
    chapter_id: chapterId,
    resource_type: 'code_sample',
    title: '',
    content: '',
    extra_data: {},
  });

  useEffect(() => {
    if (resourceId) {
      // TODO: 从 store 获取资源详情
      const chapterResources = resources[chapterId] || [];
      const resource = chapterResources.find((r) => r.id === resourceId);
      if (resource) {
        setFormData({
          chapter_id: chapterId,
          resource_type: resource.resource_type,
          title: resource.title,
          content: resource.content,
          extra_data: resource.extra_data,
        });
      }
    }
  }, [resourceId, chapterId, resources]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleContentChange = (value: string | undefined) => {
    setFormData((prev) => ({
      ...prev,
      content: value || '',
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (resourceId) {
        await updateResource(resourceId, formData as ResourceUpdate);
      } else {
        await createResource(formData as ResourceCreate);
      }
      onClose();
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      code_sample: '💻 代码示例',
      contrast: '⚖️ 对比材料',
      video: '🎬 视频',
      template: '📄 模板',
    };
    return labels[type] || type;
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-8">
      <Card className="rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-xl font-bold text-ink">
            {resourceId ? '编辑资源' : '添加资源'}
          </h2>
          <button onClick={onClose} className="text-ink-muted hover:text-ink transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">
                资源类型 *
              </label>
              <Select
                value={formData.resource_type}
                onValueChange={(v) => setFormData((prev) => ({ ...prev, resource_type: v as any }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="code_sample">💻 代码示例</SelectItem>
                  <SelectItem value="contrast">⚖️ 对比材料</SelectItem>
                  <SelectItem value="video">🎬 视频</SelectItem>
                  <SelectItem value="template">📄 模板</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">
                资源标题 *
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink focus:outline-none focus:border-accent"
                placeholder="资源标题"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-muted mb-1">
                资源内容 (Markdown) *
              </label>
              <div className="border border-border rounded-lg overflow-hidden h-96">
                <Editor
                  height="100%"
                  defaultLanguage="markdown"
                  value={formData.content}
                  onChange={handleContentChange}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    wordWrap: 'on',
                  }}
                />
              </div>
            </div>

            {formData.resource_type === 'video' && (
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-1">
                  视频链接
                </label>
                <input
                  type="url"
                  name="video_url"
                  value={(formData.extra_data as any)?.video_url || ''}
                  onChange={(e) => setFormData((prev) => ({
                    ...prev,
                    extra_data: { ...prev.extra_data, video_url: e.target.value },
                  }))}
                  className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink focus:outline-none focus:border-accent"
                  placeholder="https://..."
                />
              </div>
            )}
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-border space-x-4">
          <Button
            type="button"
            onClick={onClose}
            variant="secondary"
            className="px-6 py-2 rounded-lg transition-colors"
          >
            取消
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={loading}
            variant="default"
            className="px-6 py-2 disabled:bg-surface-3 rounded-lg transition-colors"
          >
            {loading ? '保存中...' : '保存'}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default ResourceForm;

/**
 * 课程编辑器组件
 * 用于创建/编辑课程基本信息
 */
import React, { useState, useEffect } from 'react';
import { useCourseAdminStore } from '../../../stores/courseAdminStore';
import { Pencil, Plus, Eye, X, GraduationCap, Link as LinkIcon, Info, Folder, Image as ImageIcon, AlignLeft, Code, CheckCircle, Loader2, Save } from 'lucide-react';
import type { Course, CourseCategory } from '../../../services/coursePlatform';
import { MarkdownEditor } from './MarkdownEditor';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface CourseEditorProps {
  courseId?: number;
  onClose: () => void;
}

const CourseEditor: React.FC<CourseEditorProps> = ({ courseId, onClose }) => {
  const { saveCourse, loading } = useCourseAdminStore();
  const [showPreview, setShowPreview] = useState(false);
  const [formData, setFormData] = useState<Partial<Course>>({
    title: '',
    slug: '',
    description: '',
    category_id: undefined,
    cover_image: '',
    is_published: false,
  });

  // 加载课程数据（编辑模式）
  useEffect(() => {
    if (courseId) {
      // 从 Zustand store 获取课程数据
      const course = useCourseAdminStore.getState().courses.find((c) => c.id === courseId);
      if (course) {
        setFormData(course);
      }
    }
  }, [courseId]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // 自动生成 slug
    const value = e.target.value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    setFormData((prev) => ({
      ...prev,
      slug: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await saveCourse(formData, courseId);
      onClose();
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败，请重试');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8">
      <Card className="rounded-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col shadow-lg border-border/50 animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-surface-1/50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-accent to-accent-hover rounded-lg flex items-center justify-center">
              {courseId ? <Pencil className="w-5 h-5 text-white" /> : <Plus className="w-5 h-5 text-white" />}
            </div>
            <div>
              <h2 className="text-xl font-bold text-ink-inverse">
                {courseId ? '编辑课程' : '新增课程'}
              </h2>
              <p className="text-ink-muted text-xs">填写课程基本信息</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() => setShowPreview(!showPreview)}
              className={`px-4 py-2 rounded-lg transition-all font-medium ${
                showPreview
                  ? 'bg-accent/20 text-accent border border-accent/30'
                  : 'bg-surface-2 text-ink-muted hover:bg-surface-3'
              }`}
            >
              <Eye className="w-4 h-4 mr-2" />
              {showPreview ? '隐藏预览' : '显示预览'}
            </button>
            <button
              onClick={onClose}
              className="w-10 h-10 flex items-center justify-center rounded-lg bg-surface-2 hover:bg-danger/20 text-ink-muted hover:text-danger transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-hidden flex">
          {/* Left: Form Fields */}
          <div className={`flex-1 overflow-y-auto p-6 ${showPreview ? 'w-1/2 border-r border-border/50' : 'w-full'}`}>
            <div className="space-y-5">
              {/* 课程标题和标识符 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <GraduationCap className="w-4 h-4 mr-2 text-accent" />
                    课程标题 *
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    required
                    className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink-inverse placeholder-slate-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                    placeholder="OpenSpec VibeCoding 课程"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <LinkIcon className="w-4 h-4 mr-2 text-accent" />
                    课程标识符 (slug) *
                  </label>
                  <input
                    type="text"
                    name="slug"
                    value={formData.slug}
                    onChange={handleSlugChange}
                    required
                    className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink-inverse placeholder-slate-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                    placeholder="openspec-vibecoding"
                  />
                  <p className="text-xs text-ink-faint mt-1">
                    <Info className="w-4 h-4 mr-1" />
                    根据标题自动生成，用于 URL 访问
                  </p>
                </div>
              </div>

              {/* 分类和封面图 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <Folder className="w-4 h-4 mr-2 text-accent" />
                    课程分类
                  </label>
                  <Select
                    value={String(formData.category_id || '')}
                    onValueChange={(v) =>
                      setFormData((prev) => ({
                        ...prev,
                        category_id: v ? Number(v) : undefined,
                      }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择分类" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">选择分类</SelectItem>
                      <SelectItem value="1">💻 编程开发</SelectItem>
                      <SelectItem value="2">📊 数据分析</SelectItem>
                      <SelectItem value="3">🎨 设计创意</SelectItem>
                      <SelectItem value="4">📈 产品运营</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <ImageIcon className="w-4 h-4 mr-2 text-accent" />
                    封面图片 URL
                  </label>
                  <input
                    type="url"
                    name="cover_image"
                    value={formData.cover_image}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink-inverse placeholder-slate-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                    placeholder="https://example.com/cover.jpg"
                  />
                </div>
              </div>

              {/* 课程描述 - Markdown 编辑器 */}
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  <AlignLeft className="w-4 h-4 mr-2 text-accent" />
                  课程描述 *
                </label>
                <MarkdownEditor
                  value={formData.description || ''}
                  onChange={(val) => setFormData((prev) => ({ ...prev, description: val }))}
                  placeholder="## 课程简介

在此编写课程描述，支持 **Markdown** 格式...

### 内容大纲
- 第一点
- 第二点"
                  height="300px"
                />
                <p className="text-xs text-ink-faint mt-2">
                  <Code className="w-4 h-4 mr-1" />
                  支持 Markdown 格式，点击"并排预览"查看实时效果
                </p>
              </div>

              {/* 发布状态 */}
              <div className="bg-surface-2/30 rounded-xl p-4 border border-border/50">
                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    name="is_published"
                    id="is_published"
                    checked={formData.is_published}
                    onChange={handleChange}
                    className="w-5 h-5 mt-0.5 bg-surface-2 border border-border rounded text-accent focus:ring-accent/50"
                  />
                  <label htmlFor="is_published" className="flex-1 cursor-pointer">
                    <div className="font-medium text-ink-inverse flex items-center">
                      <CheckCircle className="w-4 h-4 text-green-400 mr-2" />
                      发布课程
                    </div>
                    <p className="text-ink-muted text-sm mt-1">
                      启用后课程将对用户可见，未发布时仅管理员可查看
                    </p>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Preview */}
          {showPreview && (
            <div className="w-1/2 border-l border-border/50 overflow-y-auto p-6 bg-canvas/50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-ink-inverse flex items-center">
                  <Eye className="w-4 h-4 text-accent mr-2" />
                  预览效果
                </h3>
                <span className="text-xs text-ink-faint">课程卡片展示效果</span>
              </div>
              <div className="bg-surface-1/50 rounded-xl overflow-hidden border border-border/50">
                {/* 封面图预览 */}
                <div className="aspect-video bg-gradient-to-br from-cyan-500/20 to-blue-600/20 flex items-center justify-center relative overflow-hidden">
                  {formData.cover_image ? (
                    <img
                      src={formData.cover_image}
                      alt={formData.title}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <GraduationCap className="w-24 h-24 text-accent/50" />
                  )}
                </div>
                {/* 课程信息预览 */}
                <div className="p-4">
                  <h4 className="text-lg font-bold text-ink-inverse mb-2 line-clamp-2">
                    {formData.title || '课程标题'}
                  </h4>
                  <p className="text-ink-muted text-sm line-clamp-3">
                    {formData.description || '课程描述将在这里显示...'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border/50 bg-surface-1/50">
          <p className="text-ink-faint text-sm">
            <Info className="w-4 h-4 mr-2" />
            带 * 的字段为必填项
          </p>
          <div className="flex items-center space-x-3">
            <Button
              type="button"
              onClick={onClose}
              variant="secondary"
              className="px-6 py-2.5 rounded-xl transition-all font-medium"
            >
              取消
            </Button>
            <Button
              type="submit"
              onClick={handleSubmit}
              disabled={loading}
              variant="default"
              className="px-6 py-2.5 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent-hover disabled:from-surface-3 disabled:to-surface-3 rounded-xl transition-all font-medium shadow-lg shadow-accent/20 hover:shadow-accent/30 disabled:shadow-none flex items-center"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  保存
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default CourseEditor;

/**
 * 章节表单组件（含 Monaco Markdown 编辑器）
 */
import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Pencil, Plus, Eye, X, Tag, Heading, Shapes, ArrowUpDown, Video, Lock, Info, Loader2, Save, Code } from 'lucide-react';
import { useChapterStore } from '../../../stores/courseAdminStore';
import type { CourseChapter as Chapter, CourseChapter, CourseChapterCreate as ChapterCreate, CourseChapterUpdate as ChapterUpdate } from '../../../services/coursePlatform';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface ChapterFormProps {
  chapterId: number | null;
  onClose: () => void;
}

const ChapterForm: React.FC<ChapterFormProps> = ({ chapterId, onClose }) => {
  const { createChapter, updateChapter, chapters } = useChapterStore();
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [formData, setFormData] = useState<Partial<CourseChapter>>({
    slug: '',
    title: '',
    content: '',
    chapter_type: 'story',
    video_url: '',
    is_locked: false,
    order: 0,
  });

  useEffect(() => {
    if (chapterId) {
      const chapter = chapters.find((c) => c.id === chapterId);
      if (chapter) {
        setFormData({
          slug: chapter.slug,
          title: chapter.title,
          content: chapter.content,
          chapter_type: chapter.chapter_type,
          video_url: chapter.video_url || '',
          is_locked: chapter.is_locked,
          order: chapter.order,
        });
      }
    }
  }, [chapterId, chapters]);

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
      if (chapterId) {
        await updateChapter(chapterId, formData as ChapterUpdate);
      } else {
        await createChapter(formData as ChapterCreate);
      }
      onClose();
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8">
      <Card className="rounded-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col shadow-lg border-border/50 animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-surface-1/50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-accent to-accent-hover rounded-lg flex items-center justify-center">
              {chapterId ? <Pencil className="w-5 h-5 text-white" /> : <Plus className="w-5 h-5 text-white" />}
            </div>
            <div>
              <h2 className="text-xl font-bold text-ink">
                {chapterId ? '编辑章节' : '新增章节'}
              </h2>
              <p className="text-ink-muted text-xs">填写章节信息</p>
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
              {/* 标题和标识符 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <Tag className="w-4 h-4 mr-2 text-accent" />
                    标识符 (slug) *
                  </label>
                  <input
                    type="text"
                    name="slug"
                    value={formData.slug}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink placeholder-ink-faint focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                    placeholder="chapter-1-intro"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <Heading className="w-4 h-4 mr-2 text-accent" />
                    标题 *
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink placeholder-ink-faint focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                    placeholder="章节标题"
                  />
                </div>
              </div>

              {/* 类型和顺序 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <Shapes className="w-4 h-4 mr-2 text-accent" />
                    类型
                  </label>
                  <Select
                    value={formData.chapter_type}
                    onValueChange={(v) => setFormData((prev) => ({ ...prev, chapter_type: v as any }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="story">📖 故事</SelectItem>
                      <SelectItem value="code">💻 代码</SelectItem>
                      <SelectItem value="quiz">📝 测验</SelectItem>
                      <SelectItem value="video">🎬 视频</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink-muted mb-2">
                    <ArrowUpDown className="w-4 h-4 mr-2 text-accent" />
                    顺序
                  </label>
                  <input
                    type="number"
                    name="order"
                    value={formData.order}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                  />
                </div>
              </div>

              {/* 视频链接 */}
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  <Video className="w-4 h-4 mr-2 text-accent" />
                  视频链接
                </label>
                <input
                  type="url"
                  name="video_url"
                  value={formData.video_url}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-surface-2/50 border border-border rounded-xl text-ink placeholder-ink-faint focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                  placeholder="https://example.com/video.mp4"
                />
              </div>

              {/* 锁定选项 */}
              <div className="bg-surface-2/30 rounded-xl p-4 border border-border/50">
                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    name="is_locked"
                    id="is_locked"
                    checked={formData.is_locked}
                    onChange={handleChange}
                    className="w-5 h-5 mt-0.5 bg-surface-2 border border-border rounded text-accent focus:ring-accent/50"
                  />
                  <label htmlFor="is_locked" className="flex-1 cursor-pointer">
                    <div className="font-medium text-ink flex items-center">
                      <Lock className="w-4 h-4 text-warning mr-2" />
                      锁定章节
                    </div>
                    <p className="text-ink-muted text-sm mt-1">启用后，用户需要完成前一章节才能学习本章</p>
                  </label>
                </div>
              </div>

              {/* Markdown 编辑器 */}
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  <Code className="w-4 h-4 mr-2 text-accent" />
                  章节内容 (Markdown) *
                </label>
                <div className="border border-border rounded-xl overflow-hidden shadow-lg">
                  <Editor
                    height="400px"
                    defaultLanguage="markdown"
                    value={formData.content}
                    onChange={handleContentChange}
                    theme="vs-dark"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      lineNumbers: 'on',
                      wordWrap: 'on',
                      padding: { top: 16, bottom: 16 },
                      scrollBeyondLastLine: false,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right: Preview */}
          {showPreview && (
            <div className="w-1/2 border-l border-border/50 overflow-y-auto p-6 bg-canvas/50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-ink flex items-center">
                  <Eye className="w-4 h-4 text-accent mr-2" />
                  预览
                </h3>
                <span className="text-xs text-ink-faint">Markdown 渲染效果</span>
              </div>
              <div className="prose prose-invert prose-lg max-w-none bg-surface-1/50 rounded-xl p-6 border border-border/50">
                <div dangerouslySetInnerHTML={{ __html: renderMarkdownPreview(formData.content || '') }} />
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

// 简单的 Markdown 转 HTML 预览
function renderMarkdownPreview(markdown: string): string {
  let html = markdown
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-ink mb-4">$1</h1>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold text-ink mb-3">$1</h2>')
    .replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold text-ink mb-2">$1</h3>')
    .replace(/\*\*(.*)\*\*/gim, '<strong class="text-ink">$1</strong>')
    .replace(/\*(.*)\*/gim, '<em class="text-ink-muted">$1</em>')
    .replace(/```(\w+)?\n([\s\S]*?)```/gim, '<pre class="bg-surface-1 rounded-lg p-4 my-4 overflow-x-auto"><code class="text-success">$2</code></pre>')
    .replace(/`([^`]+)`/gim, '<code class="bg-surface-2 px-2 py-1 rounded text-danger">$1</code>')
    .replace(/^- (.*$)/gim, '<li class="text-ink-muted ml-4">$1</li>')
    .replace(/\n/gim, '<br>');
  return html;
}

export default ChapterForm;

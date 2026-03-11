/**
 * 章节表单组件（含 Monaco Markdown 编辑器）
 */
import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { useChapterStore } from '../../../stores/courseAdminStore';
import type { CourseChapter as Chapter, CourseChapter } from '../../../services/coursePlatform';

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
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-slate-700/50 animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
              <i className={`fas ${chapterId ? 'fa-edit' : 'fa-plus'} text-white`}></i>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">
                {chapterId ? '编辑章节' : '新增章节'}
              </h2>
              <p className="text-slate-400 text-xs">填写章节信息</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() => setShowPreview(!showPreview)}
              className={`px-4 py-2 rounded-lg transition-all font-medium ${
                showPreview
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <i className="fas fa-eye mr-2"></i>
              {showPreview ? '隐藏预览' : '显示预览'}
            </button>
            <button
              onClick={onClose}
              className="w-10 h-10 flex items-center justify-center rounded-lg bg-slate-700 hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-all"
            >
              <i className="fas fa-times"></i>
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-hidden flex">
          {/* Left: Form Fields */}
          <div className={`flex-1 overflow-y-auto p-6 ${showPreview ? 'w-1/2 border-r border-slate-700/50' : 'w-full'}`}>
            <div className="space-y-5">
              {/* 标题和标识符 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <i className="fas fa-tag mr-2 text-cyan-400"></i>
                    标识符 (slug) *
                  </label>
                  <input
                    type="text"
                    name="slug"
                    value={formData.slug}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all"
                    placeholder="chapter-1-intro"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <i className="fas fa-heading mr-2 text-cyan-400"></i>
                    标题 *
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all"
                    placeholder="章节标题"
                  />
                </div>
              </div>

              {/* 类型和顺序 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <i className="fas fa-shapes mr-2 text-cyan-400"></i>
                    类型
                  </label>
                  <select
                    name="chapter_type"
                    value={formData.chapter_type}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-xl text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all"
                  >
                    <option value="story">📖 故事</option>
                    <option value="code">💻 代码</option>
                    <option value="quiz">📝 测验</option>
                    <option value="video">🎬 视频</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <i className="fas fa-sort mr-2 text-cyan-400"></i>
                    顺序
                  </label>
                  <input
                    type="number"
                    name="order"
                    value={formData.order}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-xl text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all"
                  />
                </div>
              </div>

              {/* 视频链接 */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <i className="fas fa-video mr-2 text-cyan-400"></i>
                  视频链接
                </label>
                <input
                  type="url"
                  name="video_url"
                  value={formData.video_url}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all"
                  placeholder="https://example.com/video.mp4"
                />
              </div>

              {/* 锁定选项 */}
              <div className="bg-slate-700/30 rounded-xl p-4 border border-slate-600/50">
                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    name="is_locked"
                    id="is_locked"
                    checked={formData.is_locked}
                    onChange={handleChange}
                    className="w-5 h-5 mt-0.5 bg-slate-700 border border-slate-600 rounded text-cyan-500 focus:ring-cyan-500/50"
                  />
                  <label htmlFor="is_locked" className="flex-1 cursor-pointer">
                    <div className="font-medium text-white flex items-center">
                      <i className="fas fa-lock text-amber-400 mr-2"></i>
                      锁定章节
                    </div>
                    <p className="text-slate-400 text-sm mt-1">启用后，用户需要完成前一章节才能学习本章</p>
                  </label>
                </div>
              </div>

              {/* Markdown 编辑器 */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <i className="fab fa-markdown mr-2 text-cyan-400"></i>
                  章节内容 (Markdown) *
                </label>
                <div className="border border-slate-600 rounded-xl overflow-hidden shadow-lg">
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
            <div className="w-1/2 border-l border-slate-700/50 overflow-y-auto p-6 bg-slate-900/50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center">
                  <i className="fas fa-eye text-cyan-400 mr-2"></i>
                  预览
                </h3>
                <span className="text-xs text-slate-500">Markdown 渲染效果</span>
              </div>
              <div className="prose prose-invert prose-lg max-w-none bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                <div dangerouslySetInnerHTML={{ __html: renderMarkdownPreview(formData.content || '') }} />
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-700/50 bg-slate-800/50">
          <p className="text-slate-500 text-sm">
            <i className="fas fa-info-circle mr-2"></i>
            带 * 的字段为必填项
          </p>
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-xl transition-all font-medium"
            >
              取消
            </button>
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={loading}
              className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 disabled:from-slate-600 disabled:to-slate-600 text-white rounded-xl transition-all font-medium shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 disabled:shadow-none flex items-center"
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  保存中...
                </>
              ) : (
                <>
                  <i className="fas fa-save mr-2"></i>
                  保存
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// 简单的 Markdown 转 HTML 预览
function renderMarkdownPreview(markdown: string): string {
  let html = markdown
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-white mb-4">$1</h1>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold text-white mb-3">$1</h2>')
    .replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold text-white mb-2">$1</h3>')
    .replace(/\*\*(.*)\*\*/gim, '<strong class="text-white">$1</strong>')
    .replace(/\*(.*)\*/gim, '<em class="text-slate-300">$1</em>')
    .replace(/```(\w+)?\n([\s\S]*?)```/gim, '<pre class="bg-slate-800 rounded-lg p-4 my-4 overflow-x-auto"><code class="text-green-400">$2</code></pre>')
    .replace(/`([^`]+)`/gim, '<code class="bg-slate-700 px-2 py-1 rounded text-pink-400">$1</code>')
    .replace(/^- (.*$)/gim, '<li class="text-slate-300 ml-4">$1</li>')
    .replace(/\n/gim, '<br>');
  return html;
}

export default ChapterForm;

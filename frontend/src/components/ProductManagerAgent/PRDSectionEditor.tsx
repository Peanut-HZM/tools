import React, { useState, useEffect, useRef } from 'react';

interface PRDSectionEditorProps {
  sectionTitle: string;
  sectionContent: string;
  onSave: (title: string, content: string) => Promise<void>;
  onCancel: () => void;
  saving?: boolean;
}

const PRDSectionEditor: React.FC<PRDSectionEditorProps> = ({
  sectionTitle,
  sectionContent,
  onSave,
  onCancel,
  saving = false,
}) => {
  const [title, setTitle] = useState(sectionTitle);
  const [content, setContent] = useState(sectionContent);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [content]);

  const handleSave = async () => {
    if (!title.trim() || !content.trim()) {
      return;
    }
    await onSave(title.trim(), content.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-4xl mx-4 border border-slate-700 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex-1">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-transparent text-white text-xl font-semibold focus:outline-none focus:border-b-2 focus:border-blue-500"
              placeholder="章节标题"
            />
          </div>
          <button
            onClick={onCancel}
            className="ml-4 p-2 text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Editor */}
        <div className="flex-1 overflow-hidden flex flex-col p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-400">
              支持 Markdown 语法
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Ctrl/Cmd + S 保存</span>
              <span>Esc 取消</span>
            </div>
          </div>
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 w-full bg-slate-900 text-slate-100 p-4 rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500 font-mono text-sm resize-none"
            placeholder="输入章节内容..."
            rows={20}
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-700">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
            disabled={saving}
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !title.trim() || !content.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                保存中...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                保存
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PRDSectionEditor;

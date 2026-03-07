/**
 * 富文本编辑器组件
 * 基于 TipTap 的 Markdown 编辑器，支持代码高亮和预览
 */
import React, { useEffect, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { common, createLowlight } from 'lowlight';

interface RichTextEditorProps {
  content: string;
  onChange: (content: string) => void;
  placeholder?: string;
  height?: string;
  showPreview?: boolean;
}

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  content,
  onChange,
  placeholder = '请输入内容...',
  height = '400px',
  showPreview = false,
}) => {
  const [showPreviewState, setShowPreviewState] = useState(showPreview);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        codeBlock: false,
      }),
      CodeBlockLowlight.configure({
        lowlight: createLowlight(common),
      }),
      Link.configure({
        openOnClick: false,
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  if (!editor) {
    return <div className="text-slate-400">加载编辑器...</div>;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center flex-wrap gap-2 p-3 bg-slate-800/50 border border-slate-700/50 rounded-t-xl">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('bold')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="粗体"
        >
          <i className="fas fa-bold"></i>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('italic')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="斜体"
        >
          <i className="fas fa-italic"></i>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('strike')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="删除线"
        >
          <i className="fas fa-strikethrough"></i>
        </button>
        <div className="w-px h-6 bg-slate-600 mx-2"></div>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('heading', { level: 1 })
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="标题 1"
        >
          <span className="font-bold">H1</span>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('heading', { level: 2 })
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="标题 2"
        >
          <span className="font-bold">H2</span>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('heading', { level: 3 })
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="标题 3"
        >
          <span className="font-bold">H3</span>
        </button>
        <div className="w-px h-6 bg-slate-600 mx-2"></div>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('bulletList')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="无序列表"
        >
          <i className="fas fa-list-ul"></i>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('orderedList')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="有序列表"
        >
          <i className="fas fa-list-ol"></i>
        </button>
        <div className="w-px h-6 bg-slate-600 mx-2"></div>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('codeBlock')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="代码块"
        >
          <i className="fas fa-code"></i>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('blockquote')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="引用"
        >
          <i className="fas fa-quote-left"></i>
        </button>
        <div className="w-px h-6 bg-slate-600 mx-2"></div>
        <button
          type="button"
          onClick={() => {
            const url = window.prompt('输入链接地址:');
            if (url) {
              editor.chain().focus().setLink({ href: url }).run();
            }
          }}
          className={`p-2 rounded-lg transition-all ${
            editor.isActive('link')
              ? 'bg-cyan-500/20 text-cyan-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600'
          }`}
          title="链接"
        >
          <i className="fas fa-link"></i>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().unsetAllMarks().run()}
          className="p-2 rounded-lg bg-slate-700/50 text-slate-400 hover:bg-slate-600 transition-all"
          title="清除格式"
        >
          <i className="fas fa-remove-format"></i>
        </button>
        <div className="flex-1"></div>
        <button
          type="button"
          onClick={() => setShowPreviewState(!showPreviewState)}
          className={`px-4 py-2 rounded-lg transition-all font-medium ${
            showPreviewState
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          <i className="fas fa-eye mr-2"></i>
          {showPreviewState ? '隐藏预览' : '显示预览'}
        </button>
      </div>

      {/* Editor Content */}
      <div className={`flex-1 flex ${showPreviewState ? 'divide-x divide-slate-700/50' : ''}`}>
        <div className={`flex-1 overflow-y-auto border border-slate-700/50 rounded-b-xl ${showPreviewState ? 'w-1/2' : 'w-full'}`}>
          <EditorContent
            editor={editor}
            className="prose prose-invert prose-lg max-w-none p-4 h-full editor-content"
          />
        </div>

        {/* Preview Panel */}
        {showPreviewState && (
          <div className="w-1/2 overflow-y-auto border border-slate-700/50 rounded-b-xl bg-slate-900/50 p-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center">
              <i className="fas fa-eye text-cyan-400 mr-2"></i>
              预览
            </h3>
            <div
              className="prose prose-invert prose-lg max-w-none preview-content"
              dangerouslySetInnerHTML={{ __html: editor.getHTML() }}
            />
          </div>
        )}
      </div>

      <style>{`
        .editor-content {
          min-height: ${height};
        }
        .editor-content:focus {
          outline: none;
        }
        .ProseMirror {
          outline: none;
        }
        .ProseMirror p.is-editor-empty:first-child::before {
          color: #64748b;
          content: attr(data-placeholder);
          float: left;
          height: 0;
          pointer-events: none;
        }
        .ProseMirror code {
          background: #1e293b;
          padding: 0.2em 0.4em;
          border-radius: 0.25rem;
          font-size: 0.875em;
        }
        .ProseMirror pre {
          background: #0f172a;
          border-radius: 0.5rem;
          padding: 1rem;
          overflow-x: auto;
        }
        .ProseMirror blockquote {
          border-left: 4px solid #06b6d4;
          padding-left: 1rem;
          margin-left: 0;
          color: #94a3b8;
        }
      `}</style>
    </div>
  );
};

export default RichTextEditor;

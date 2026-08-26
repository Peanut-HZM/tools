/**
 * 富文本编辑器组件
 * 基于 TipTap 的 Markdown 编辑器，支持代码高亮和预览
 */
import { Bold, Code, Eye, Italic, Link as LinkIcon, List, ListOrdered, Quote, RemoveFormatting, Strikethrough } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { common, createLowlight } from 'lowlight';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/Tooltip';

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
    return <div className="text-ink-faint">加载编辑器...</div>;
  }

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full">
        {/* Toolbar */}
        <div className="flex items-center flex-wrap gap-2 p-3 bg-surface-1/50 border border-border/50 rounded-t-xl">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleBold().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('bold')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="粗体"
              >
                <Bold className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>粗体</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleItalic().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('italic')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="斜体"
              >
                <Italic className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>斜体</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleStrike().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('strike')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="删除线"
              >
                <Strikethrough className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>删除线</TooltipContent>
          </Tooltip>
          <div className="w-px h-6 bg-surface-3 mx-2"></div>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('heading', { level: 1 })
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="标题 1"
              >
                <span className="font-bold">H1</span>
              </button>
            </TooltipTrigger>
            <TooltipContent>标题 1</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('heading', { level: 2 })
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="标题 2"
              >
                <span className="font-bold">H2</span>
              </button>
            </TooltipTrigger>
            <TooltipContent>标题 2</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('heading', { level: 3 })
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="标题 3"
              >
                <span className="font-bold">H3</span>
              </button>
            </TooltipTrigger>
            <TooltipContent>标题 3</TooltipContent>
          </Tooltip>
          <div className="w-px h-6 bg-surface-3 mx-2"></div>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('bulletList')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="无序列表"
              >
                <List className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>无序列表</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('orderedList')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="有序列表"
              >
                <ListOrdered className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>有序列表</TooltipContent>
          </Tooltip>
          <div className="w-px h-6 bg-surface-3 mx-2"></div>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('codeBlock')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="代码块"
              >
                <Code className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>代码块</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
                className={`p-2 rounded-lg transition-all ${
                  editor.isActive('blockquote')
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="引用"
              >
                <Quote className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>引用</TooltipContent>
          </Tooltip>
          <div className="w-px h-6 bg-surface-3 mx-2"></div>
          <Tooltip>
            <TooltipTrigger asChild>
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
                    ? 'bg-accent/20 text-accent'
                    : 'bg-surface-2/50 text-ink-faint hover:bg-surface-3'
                }`}
                aria-label="链接"
              >
                <LinkIcon className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>链接</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => editor.chain().focus().unsetAllMarks().run()}
                className="p-2 rounded-lg bg-surface-2/50 text-ink-faint hover:bg-surface-3 transition-all"
                aria-label="清除格式"
              >
                <RemoveFormatting className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>清除格式</TooltipContent>
          </Tooltip>
          <div className="flex-1"></div>
          <button
            type="button"
            onClick={() => setShowPreviewState(!showPreviewState)}
            className={`px-4 py-2 rounded-lg transition-all font-medium ${
              showPreviewState
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'bg-surface-2 text-ink-muted hover:bg-surface-3'
            }`}
          >
            <Eye className="w-4 h-4 mr-2" />
            {showPreviewState ? '隐藏预览' : '显示预览'}
          </button>
        </div>

        {/* Editor Content */}
        <div className={`flex-1 flex ${showPreviewState ? 'divide-x divide-border/50' : ''}`}>
          <div className={`flex-1 overflow-y-auto border border-border/50 rounded-b-xl ${showPreviewState ? 'w-1/2' : 'w-full'}`}>
            <EditorContent
              editor={editor}
              className="prose prose-invert prose-lg max-w-none p-4 h-full editor-content"
            />
          </div>

          {/* Preview Panel */}
          {showPreviewState && (
            <div className="w-1/2 overflow-y-auto border border-border/50 rounded-b-xl bg-canvas/50 p-4">
              <h3 className="text-sm font-semibold text-ink-faint mb-3 flex items-center">
                <Eye className="w-4 h-4 text-accent mr-2" />
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
    </TooltipProvider>
  );
};

export default RichTextEditor;

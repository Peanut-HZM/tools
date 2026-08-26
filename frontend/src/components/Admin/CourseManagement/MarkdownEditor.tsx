/**
 * Markdown 编辑器组件
 * 支持 Monaco Editor 语法高亮和实时预览
 */
import React, { useState, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Pencil, Columns2, Info } from 'lucide-react';
import 'highlight.js/styles/atom-one-dark.css';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  height?: string;
  showPreview?: boolean;
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  placeholder = '使用 Markdown 格式编写内容...',
  height = '300px',
  showPreview = false,
}) => {
  const [viewMode, setViewMode] = useState<'edit' | 'split'>('edit');

  // 工具栏按钮配置
  const toolbarButtons = [
    { icon: 'B', title: '加粗', prefix: '**', suffix: '**' },
    { icon: 'I', title: '斜体', prefix: '*', suffix: '*' },
    { icon: '#', title: '标题', prefix: '## ', suffix: '' },
    { icon: '[]', title: '链接', prefix: '[', suffix: '](url)' },
    { icon: '{}', title: '代码块', prefix: '```\n', suffix: '\n```' },
    { icon: '>', title: '引用', prefix: '> ', suffix: '' },
    { icon: '≡', title: '列表', prefix: '- ', suffix: '' },
  ];

  // 处理工具栏按钮点击
  const handleToolbarClick = (prefix: string, suffix: string) => {
    const editor = document.querySelector('.monaco-editor') as HTMLElement;
    if (!editor) return;

    // 使用 Monaco Editor API 获取选中文本
    onChange(value); // 确保值已同步
  };

  // 字符计数
  const charCount = useMemo(() => value.length, [value]);

  // 预览组件
  const Preview = () => (
    <div className="h-full overflow-y-auto p-4 bg-canvas/50 rounded-r-xl">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-ink-inverse mb-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold text-ink-inverse mb-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-medium text-ink-inverse mb-2">{children}</h3>,
          p: ({ children }) => <p className="mb-4 text-ink-muted leading-relaxed">{children}</p>,
          strong: ({ children }) => <strong className="text-ink-inverse font-semibold">{children}</strong>,
          em: ({ children }) => <em className="text-accent">{children}</em>,
          code: ({ children }) => (
            <code className="px-1.5 py-0.5 bg-surface-2/50 rounded text-pink-400 text-xs">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-canvas/50 rounded-lg p-3 my-2 overflow-x-auto border border-border/30">
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-2 my-3 text-ink-muted">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-2 my-3 text-ink-muted">{children}</ol>
          ),
          li: ({ children }) => <li className="text-ink-muted">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-accent/50 pl-4 my-3 text-ink-muted italic">
              {children}
            </blockquote>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              className="text-accent hover:text-accent underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
        }}
      >
        {value || '_暂无内容*'}
      </ReactMarkdown>
    </div>
  );

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-surface-1/50">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface-2/50 border-b border-border">
        <div className="flex items-center gap-1">
          {toolbarButtons.map((btn, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleToolbarClick(btn.prefix, btn.suffix)}
              className="px-2.5 py-1.5 text-sm bg-surface-3 hover:bg-accent/20 text-ink-muted hover:text-accent rounded transition-all font-mono"
              title={btn.title}
            >
              {btn.icon}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setViewMode('edit')}
            className={`px-3 py-1.5 text-xs rounded transition-all font-medium ${
              viewMode === 'edit'
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'bg-surface-3 text-ink-muted hover:bg-accent-hover'
            }`}
          >
            <Pencil className="w-4 h-4 mr-1.5" />
            编辑
          </button>
          <button
            type="button"
            onClick={() => setViewMode('split')}
            className={`px-3 py-1.5 text-xs rounded transition-all font-medium ${
              viewMode === 'split'
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'bg-surface-3 text-ink-muted hover:bg-accent-hover'
            }`}
          >
            <Columns2 className="w-4 h-4 mr-1.5" />
            并排预览
          </button>
        </div>
      </div>

      {/* 编辑器和预览 */}
      <div className={`flex ${viewMode === 'split' ? 'flex-row' : 'flex-col'}`}>
        {/* Monaco Editor */}
        <div className={viewMode === 'split' ? 'w-1/2' : 'w-full'}>
          <Editor
            height={height}
            language="markdown"
            theme="vs-dark"
            value={value}
            onChange={(val) => onChange(val || '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 12 },
            }}
          />
        </div>

        {/* 预览面板 */}
        {viewMode === 'split' && (
          <div className="w-1/2 border-l border-border/50">
            <Preview />
          </div>
        )}
      </div>

      {/* Footer - 字符计数 */}
      <div className="px-4 py-2 bg-surface-2/30 border-t border-border flex items-center justify-between">
        <p className="text-xs text-ink-muted">
          <Info className="w-4 h-4 mr-1" />
          支持 Markdown 格式
        </p>
        <p className="text-xs text-ink-muted">
          {charCount} 字
        </p>
      </div>
    </div>
  );
};

export default MarkdownEditor;

/**
 * Markdown 编辑器组件
 * 支持 Monaco Editor 语法高亮和实时预览
 */
import React, { useState, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
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
    <div className="h-full overflow-y-auto p-4 bg-slate-900/50 rounded-r-xl">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-white mb-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold text-white mb-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-medium text-white mb-2">{children}</h3>,
          p: ({ children }) => <p className="mb-4 text-slate-300 leading-relaxed">{children}</p>,
          strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
          em: ({ children }) => <em className="text-cyan-300">{children}</em>,
          code: ({ children }) => (
            <code className="px-1.5 py-0.5 bg-slate-700/50 rounded text-pink-400 text-xs">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-slate-900/50 rounded-lg p-3 my-2 overflow-x-auto border border-slate-700/30">
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-2 my-3 text-slate-300">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-2 my-3 text-slate-300">{children}</ol>
          ),
          li: ({ children }) => <li className="text-slate-300">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-cyan-500/50 pl-4 my-3 text-slate-400 italic">
              {children}
            </blockquote>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              className="text-cyan-400 hover:text-cyan-300 underline"
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
    <div className="border border-slate-600 rounded-xl overflow-hidden bg-slate-800/50">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-700/50 border-b border-slate-600">
        <div className="flex items-center gap-1">
          {toolbarButtons.map((btn, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleToolbarClick(btn.prefix, btn.suffix)}
              className="px-2.5 py-1.5 text-sm bg-slate-600 hover:bg-cyan-500/20 text-slate-300 hover:text-cyan-400 rounded transition-all font-mono"
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
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
            }`}
          >
            <i className="fas fa-edit mr-1.5"></i>
            编辑
          </button>
          <button
            type="button"
            onClick={() => setViewMode('split')}
            className={`px-3 py-1.5 text-xs rounded transition-all font-medium ${
              viewMode === 'split'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
            }`}
          >
            <i className="fas fa-columns mr-1.5"></i>
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
          <div className="w-1/2 border-l border-slate-700/50">
            <Preview />
          </div>
        )}
      </div>

      {/* Footer - 字符计数 */}
      <div className="px-4 py-2 bg-slate-700/30 border-t border-slate-600 flex items-center justify-between">
        <p className="text-xs text-slate-400">
          <i className="fas fa-info-circle mr-1"></i>
          支持 Markdown 格式
        </p>
        <p className="text-xs text-slate-400">
          {charCount} 字
        </p>
      </div>
    </div>
  );
};

export default MarkdownEditor;

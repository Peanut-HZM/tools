/**
 * Markdown 增强编辑器组件
 * 支持实时预览、工具栏、快捷键
 */
import React, { useState, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

interface MarkdownEditorProps {
  initialValue: string;
  onSave: (value: string) => void;
  onCancel: () => void;
}

interface ToolbarButtonProps {
  icon: string;
  title: string;
  onClick: () => void;
  shortcut?: string;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({ icon, title, onClick, shortcut }) => (
  <button
    type="button"
    onClick={onClick}
    className="p-2 text-slate-300 hover:text-white hover:bg-slate-600 rounded transition-colors"
    title={`${title}${shortcut ? ` (${shortcut})` : ''}`}
  >
    {icon}
  </button>
);

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({ initialValue, onSave, onCancel }) => {
  const [value, setValue] = useState(initialValue);
  const [previewPosition, setPreviewPosition] = useState<'right' | 'bottom'>('right');
  const [splitRatio, setSplitRatio] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 工具栏操作
  const insertMarkdown = useCallback((before: string, after: string = '') => {
    const textarea = editorRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.substring(start, end);
    const newText = value.substring(0, start) + before + selectedText + after + value.substring(end);

    setValue(newText);

    // 恢复焦点和选区
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, end + before.length);
    }, 0);
  }, [value]);

  const handleBold = () => insertMarkdown('**', '**');
  const handleItalic = () => insertMarkdown('*', '*');
  const handleCode = () => insertMarkdown('`', '`');
  const handleCodeBlock = () => insertMarkdown('```\n', '\n```');
  const handleLink = () => insertMarkdown('[', '](url)');
  const handleQuote = () => insertMarkdown('> ');
  const handleList = () => insertMarkdown('- ');
  const handleOrderedList = () => insertMarkdown('1. ');

  // 处理快捷键
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key.toLowerCase()) {
        case 'b':
          e.preventDefault();
          handleBold();
          break;
        case 'i':
          e.preventDefault();
          handleItalic();
          break;
        case 'e':
          e.preventDefault();
          handleCode();
          break;
        case 'k':
          e.preventDefault();
          handleLink();
          break;
        case 'l':
          e.preventDefault();
          handleList();
          break;
        case 'q':
          e.preventDefault();
          handleQuote();
          break;
      }
    }
  }, []);

  // 拖拽调整分栏比例
  const handleMouseDown = useCallback(() => {
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    const newRatio = ((e.clientX - rect.left) / rect.width) * 100;

    if (newRatio >= 20 && newRatio <= 80) {
      setSplitRatio(newRatio);
    }
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-2 py-2 bg-slate-700 border-b border-slate-600">
        <div className="flex items-center space-x-1">
          <ToolbarButton icon="**B**" title="粗体" shortcut="Ctrl+B" onClick={handleBold} />
          <ToolbarButton icon="*I*" title="斜体" shortcut="Ctrl+I" onClick={handleItalic} />
          <ToolbarButton icon="🔗" title="链接" shortcut="Ctrl+K" onClick={handleLink} />
          <ToolbarButton icon="&lt;/&gt;" title="内联代码" shortcut="Ctrl+E" onClick={handleCode} />
          <ToolbarButton icon="&lt;pre&gt;" title="代码块" onClick={handleCodeBlock} />
          <ToolbarButton icon="•" title="列表" shortcut="Ctrl+L" onClick={handleList} />
          <ToolbarButton icon="1." title="有序列表" onClick={handleOrderedList} />
          <ToolbarButton icon=">" title="引用" shortcut="Ctrl+Q" onClick={handleQuote} />
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setPreviewPosition(previewPosition === 'right' ? 'bottom' : 'right')}
            className="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 text-slate-200 rounded transition-colors"
            title="切换预览方向"
          >
            {previewPosition === 'right' ? '⬇️ 上下' : '➡️ 左右'}
          </button>
        </div>
      </div>

      {/* 编辑区和预览区 */}
      <div
        ref={containerRef}
        className={`flex ${previewPosition === 'bottom' ? 'flex-col' : 'flex-row'}`}
        style={{ height: previewPosition === 'bottom' ? '400px' : '300px' }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* 编辑区 */}
        <div
          className="h-full bg-slate-800"
          style={{ [previewPosition === 'right' ? 'width' : 'height']: `${splitRatio}%` }}
        >
          <textarea
            ref={editorRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full h-full bg-slate-800 text-slate-100 px-4 py-3 font-mono text-sm resize-none focus:outline-none border-none"
            placeholder="输入 Markdown 内容..."
          />
        </div>

        {/* 分隔线（仅左右布局时） */}
        {previewPosition === 'right' && (
          <div
            className="w-1 bg-slate-600 hover:bg-blue-500 cursor-col-resize transition-colors"
            onMouseDown={handleMouseDown}
          />
        )}

        {/* 预览区 */}
        <div
          className={`h-full bg-slate-700/50 overflow-y-auto ${previewPosition === 'bottom' ? 'border-t' : 'border-l'} border-slate-600`}
          style={{ [previewPosition === 'right' ? 'width' : 'height']: `${100 - splitRatio}%` }}
        >
          <div className="p-4 prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{value}</ReactMarkdown>
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center justify-end space-x-2 px-4 py-3 bg-slate-700 border-t border-slate-600">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm bg-slate-600 hover:bg-slate-500 text-slate-200 rounded transition-colors"
        >
          取消
        </button>
        <button
          onClick={() => onSave(value)}
          className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
        >
          保存
        </button>
      </div>
    </div>
  );
};

export default MarkdownEditor;

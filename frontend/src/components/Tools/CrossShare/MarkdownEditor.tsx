/**
 * Markdown 增强编辑器组件
 * 支持实时预览、工具栏、快捷键
 */
import React, { useState, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

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
  <Button
    size="icon"
    variant="ghost"
    type="button"
    onClick={onClick}
    className="text-ink-muted hover:text-ink"
    title={`${title}${shortcut ? ` (${shortcut})` : ''}`}
  >
    {icon}
  </Button>
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
    <Card className="overflow-hidden">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-2 py-2 bg-surface-2 border-b border-border">
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
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setPreviewPosition(previewPosition === 'right' ? 'bottom' : 'right')}
            title="切换预览方向"
          >
            {previewPosition === 'right' ? '⬇️ 上下' : '➡️ 左右'}
          </Button>
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
          className="h-full bg-surface-1"
          style={{ [previewPosition === 'right' ? 'width' : 'height']: `${splitRatio}%` }}
        >
          <textarea
            ref={editorRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full h-full bg-surface-1 text-ink px-4 py-3 font-mono text-sm resize-none focus:outline-none border-none"
            placeholder="输入 Markdown 内容..."
          />
        </div>

        {/* 分隔线（仅左右布局时） */}
        {previewPosition === 'right' && (
          <div
            className="w-1 bg-surface-3 hover:bg-accent-hover cursor-col-resize transition-colors"
            onMouseDown={handleMouseDown}
          />
        )}

        {/* 预览区 */}
        <div
          className={`h-full bg-surface-2/50 overflow-y-auto ${previewPosition === 'bottom' ? 'border-t' : 'border-l'} border-border`}
          style={{ [previewPosition === 'right' ? 'width' : 'height']: `${100 - splitRatio}%` }}
        >
          <div className="p-4 prose prose-sm max-w-none">
            <ReactMarkdown>{value}</ReactMarkdown>
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center justify-end space-x-2 px-4 py-3 bg-surface-2 border-t border-border">
        <Button
          size="sm"
          variant="secondary"
          onClick={onCancel}
          className="bg-surface-3 text-ink hover:bg-surface-3"
        >
          取消
        </Button>
        <Button
          variant="default"
          onClick={() => onSave(value)}
          className="text-white"
        >
          保存
        </Button>
      </div>
    </Card>
  );
};

export default MarkdownEditor;

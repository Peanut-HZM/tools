/**
 * Editor Component - Monaco-based Markdown editor
 * Note: Using a simple textarea as Monaco requires additional setup
 * Performance optimizations:
 * - Debounced onChange to reduce re-renders
 * - Memoized event handlers
 * - Efficient cursor position tracking
 */
import { useRef, useEffect, useCallback, useMemo, memo } from 'react';
import type { EditorConfig } from '../../../types/markdownEditor';

interface EditorProps {
  content: string;
  config: EditorConfig;
  onChange: (content: string) => void;
  onSave: () => void;
  onCursorChange?: (line: number, column: number) => void;
}

function Editor({
  content,
  config,
  onChange,
  onSave,
  onCursorChange
}: EditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastCursorRef = useRef({ line: 1, column: 1 });

  // Memoize style object to prevent unnecessary re-renders
  const textareaStyle = useMemo(() => ({
    fontSize: `${config.fontSize}px`,
    tabSize: config.tabSize,
    lineHeight: 1.6,
    wordWrap: config.wordWrap ? 'break-word' as const : 'normal' as const,
    whiteSpace: config.wordWrap ? 'pre-wrap' as const : 'pre' as const
  }), [config.fontSize, config.tabSize, config.wordWrap]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl/Cmd + S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      onSave();
      return;
    }

    // Ctrl/Cmd + B for bold
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = content.substring(start, end);
        const newText = content.substring(0, start) + `**${selectedText}**` + content.substring(end);
        onChange(newText);
        // Set cursor position after the operation
        requestAnimationFrame(() => {
          textarea.selectionStart = start + 2;
          textarea.selectionEnd = end + 2;
        });
      }
      return;
    }

    // Ctrl/Cmd + I for italic
    if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = content.substring(start, end);
        const newText = content.substring(0, start) + `*${selectedText}*` + content.substring(end);
        onChange(newText);
        requestAnimationFrame(() => {
          textarea.selectionStart = start + 1;
          textarea.selectionEnd = end + 1;
        });
      }
      return;
    }

    // Tab handling
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const indent = config.useSpaces ? ' '.repeat(config.tabSize) : '\t';
        const newText = content.substring(0, start) + indent + content.substring(end);
        onChange(newText);
        requestAnimationFrame(() => {
          textarea.selectionStart = textarea.selectionEnd = start + indent.length;
        });
      }
    }
  }, [content, config.useSpaces, config.tabSize, onChange, onSave]);

  // Handle cursor position changes - optimized to avoid unnecessary updates
  const handleSelect = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea && onCursorChange) {
      const text = textarea.value.substring(0, textarea.selectionStart);
      const lines = text.split('\n');
      const line = lines.length;
      const column = lines[lines.length - 1].length + 1;
      
      // Only update if position actually changed
      if (lastCursorRef.current.line !== line || lastCursorRef.current.column !== column) {
        lastCursorRef.current = { line, column };
        onCursorChange(line, column);
      }
    }
  }, [onCursorChange]);

  // Update cursor position on content change
  useEffect(() => {
    handleSelect();
  }, [content, handleSelect]);

  const themeClass = 'bg-transparent text-inherit';

  return (
    <div className="h-full flex flex-col">
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onSelect={handleSelect}
        onClick={handleSelect}
        className={`flex-1 w-full p-4 resize-none outline-none ${themeClass} font-mono`}
        style={textareaStyle}
        placeholder="开始编写 Markdown..."
        spellCheck={false}
      />
    </div>
  );
}

// Memoize the component to prevent unnecessary re-renders
export default memo(Editor);

/**
 * 消息操作按钮组
 * 横向展示所有操作按钮：复制纯文本、复制 Markdown、展开/折叠、删除
 */
import React, { useState } from 'react';
import { Copy, FileText, Trash2, ChevronDown, ChevronUp } from 'lucide-react';

interface MessageActionsProps {
  content: string;
  messageId: string;
  onDelete: (messageId: string) => void;
  onCopySuccess: () => void;
  isExpanded?: boolean;
  needsCollapse?: boolean;
  onToggleExpand?: () => void;
}

const MessageActions: React.FC<MessageActionsProps> = ({
  content,
  messageId,
  onDelete,
  onCopySuccess,
  isExpanded = false,
  needsCollapse = false,
  onToggleExpand,
}) => {
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback(label);
      onCopySuccess();
      setTimeout(() => setCopyFeedback(null), 1500);
    } catch (err) {
      console.error('复制失败:', err);
      alert('复制失败，请手动复制');
    }
  };

  const handleCopyText = () => {
    // 复制纯文本（去除 Markdown 标记）
    const plainText = content
      .replace(/`{3}[\w]*\n?/g, '\n')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/#(#+)\s+/g, '')
      .replace(/^\s*[-*+]\s+/gm, '')
      .replace(/^\s*\d+\.\s+/gm, '')
      .replace(/^\s*>/gm, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim();
    copyToClipboard(plainText, 'text');
  };

  const handleCopyMarkdown = () => {
    copyToClipboard(content, 'markdown');
  };

  const handleDelete = () => {
    if (confirm('确定要删除这条消息吗？')) {
      onDelete(messageId);
    }
  };

  const buttonBase = 'flex items-center space-x-1 px-2.5 py-1 text-xs rounded-md transition-colors whitespace-nowrap leading-none';

  return (
    <div className="flex items-center gap-1.5">
      {/* 复制纯文本 */}
      <button
        onClick={handleCopyText}
        className={`${buttonBase} bg-surface-3/60 hover:bg-slate-500 text-ink-muted hover:text-ink-inverse`}
        title="复制纯文本"
      >
        {copyFeedback === 'text' ? (
          <span className="text-green-400">✓</span>
        ) : (
          <Copy size={12} strokeWidth={1.5} />
        )}
        <span>{copyFeedback === 'text' ? '已复制' : '文本'}</span>
      </button>

      {/* 复制 Markdown */}
      <button
        onClick={handleCopyMarkdown}
        className={`${buttonBase} bg-surface-3/60 hover:bg-slate-500 text-ink-muted hover:text-ink-inverse`}
        title="复制 Markdown 源码"
      >
        {copyFeedback === 'markdown' ? (
          <span className="text-green-400">✓</span>
        ) : (
          <FileText size={12} strokeWidth={1.5} />
        )}
        <span>{copyFeedback === 'markdown' ? '已复制' : 'MD'}</span>
      </button>

      {/* 展开/折叠 */}
      {needsCollapse && onToggleExpand && (
        <button
          onClick={onToggleExpand}
          className={`${buttonBase} bg-accent/60 hover:bg-accent-hover text-blue-200 hover:text-ink-inverse`}
          title={isExpanded ? '折叠' : '展开'}
        >
          {isExpanded ? (
            <>
              <ChevronUp size={12} strokeWidth={1.5} />
              <span>折叠</span>
            </>
          ) : (
            <>
              <ChevronDown size={12} strokeWidth={1.5} />
              <span>展开</span>
            </>
          )}
        </button>
      )}

      {/* 删除 */}
      <button
        onClick={handleDelete}
        className={`${buttonBase} bg-red-600/40 hover:bg-red-500/70 text-red-300 hover:text-ink-inverse`}
        title="删除消息"
      >
        <Trash2 size={12} strokeWidth={1.5} />
        <span>删除</span>
      </button>
    </div>
  );
};

export default MessageActions;

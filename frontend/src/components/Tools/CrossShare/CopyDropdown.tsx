/**
 * 复制下拉菜单组件
 * 提供多种复制选项
 */
import React from 'react';
import { Button } from "@/components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/DropdownMenu';

interface CopyDropdownProps {
  content: string;
  messageId?: string;
  onDelete?: (messageId: string) => void;
  onCopySuccess?: () => void;
}

type CopyType = 'text' | 'markdown' | 'html';

const CopyDropdown: React.FC<CopyDropdownProps> = ({ content, messageId, onDelete, onCopySuccess }) => {
  const copyToClipboard = async (text: string, _type: CopyType) => {
    try {
      await navigator.clipboard.writeText(text);
      onCopySuccess?.();
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('复制失败，请手动复制');
    }
  };

  const handleCopyText = () => {
    // 复制纯文本（去除 Markdown 标记）
    const plainText = content
      .replace(/`{3}[\w]*\n?/g, '\n') // 代码块
      .replace(/`([^`]+)`/g, '$1') // 内联代码
      .replace(/\*\*([^*]+)\*\*/g, '$1') // 粗体
      .replace(/\*([^*]+)\*/g, '$1') // 斜体
      .replace(/#(#+)\s+/g, '') // 标题
      .replace(/^\s*[-*+]\s+/gm, '') // 列表
      .replace(/^\s*\d+\.\s+/gm, '') // 有序列表
      .replace(/^\s*>/gm, '') // 引用
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // 链接
      .trim();
    copyToClipboard(plainText, 'text');
  };

  const handleCopyMarkdown = () => {
    // 复制原始 Markdown 源码
    copyToClipboard(content, 'markdown');
  };

  const handleCopyHtml = () => {
    // 简单的 Markdown 转 HTML（实际项目中可使用 marked 等库）
    let html = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*)\*/gim, '<em>$1</em>')
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>')
      .replace(/^\s*> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/^\s*[-*+]\s+(.*$)/gim, '<li>$1</li>')
      .replace(/^\s*\d+\.\s+(.*$)/gim, '<li>$1</li>')
      .replace(/\n/gim, '<br>');

    html = `<div class="markdown-body">${html}</div>`;
    copyToClipboard(html, 'html');
  };

  const handleDelete = () => {
    if (messageId && onDelete) {
      onDelete(messageId);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          size="sm"
          variant="secondary"
          aria-label="复制选项"
          className="flex items-center space-x-1"
        >
          <span>📋</span>
          <span>复制</span>
          <span className="text-[10px]">▼</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onSelect={handleCopyText}>
          <span className="text-xs mr-2">📄</span>
          复制内容（纯文本）
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={handleCopyMarkdown}>
          <span className="text-xs mr-2">📝</span>
          复制 Markdown 源码
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={handleCopyHtml}>
          <span className="text-xs mr-2">🌐</span>
          复制渲染 HTML
        </DropdownMenuItem>
        {onDelete && messageId && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={handleDelete}
              className="text-accent-danger focus:text-accent-danger"
            >
              <span className="text-xs mr-2">🗑️</span>
              删除消息
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default CopyDropdown;

/**
 * 复制下拉菜单组件
 * 提供多种复制选项
 */
import React, { useState } from 'react';

interface CopyDropdownProps {
  content: string;
  onCopySuccess?: () => void;
}

type CopyType = 'text' | 'markdown' | 'html';

const CopyDropdown: React.FC<CopyDropdownProps> = ({ content, onCopySuccess }) => {
  const [isOpen, setIsOpen] = useState(false);

  const copyToClipboard = async (text: string, type: CopyType) => {
    try {
      await navigator.clipboard.writeText(text);
      setIsOpen(false);
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

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 text-slate-200 rounded transition-colors flex items-center space-x-1"
        title="复制选项"
      >
        <span>📋</span>
        <span>复制</span>
        <span className="text-[10px]">▼</span>
      </button>

      {isOpen && (
        <>
          {/* 遮罩层 */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* 下拉菜单 */}
          <div className="absolute right-0 top-full mt-1 w-48 bg-slate-700 border border-slate-600 rounded-lg shadow-xl z-20 overflow-hidden">
            <div className="py-1">
              <button
                onClick={handleCopyText}
                className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-600 transition-colors flex items-center space-x-2"
              >
                <span className="text-xs">📄</span>
                <span>复制内容（纯文本）</span>
              </button>
              <button
                onClick={handleCopyMarkdown}
                className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-600 transition-colors flex items-center space-x-2"
              >
                <span className="text-xs">📝</span>
                <span>复制 Markdown 源码</span>
              </button>
              <button
                onClick={handleCopyHtml}
                className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-600 transition-colors flex items-center space-x-2"
              >
                <span className="text-xs">🌐</span>
                <span>复制渲染 HTML</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default CopyDropdown;

/**
 * Markdown 预览器
 */
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PreviewProps } from './types';

export const MarkdownViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [content, setContent] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [copySuccess, setCopySuccess] = React.useState(false);

  React.useEffect(() => {
    const fetchContent = async () => {
      try {
        // 通过后端代理获取文件内容，避免 CORS 问题
        const response = await fetch(`/api/cross-share/files/${fileId}/content`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        if (!response.ok) {
          throw new Error('Failed to fetch file content');
        }
        const text = await response.text();
        setContent(text);
      } catch (err) {
        console.error('Failed to load markdown:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [fileId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400">
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>Markdown 加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-auto bg-slate-800 p-6">
      <button
        onClick={handleCopy}
        className="absolute top-4 right-4 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center space-x-1 z-10"
      >
        <span>{copySuccess ? '✓ 已复制' : '📋 复制'}</span>
      </button>
      <div className="max-w-4xl mx-auto prose prose-invert prose-slate">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

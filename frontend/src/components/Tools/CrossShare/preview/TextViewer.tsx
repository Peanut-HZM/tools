/**
 * 文本预览器
 */
import React from 'react';
import { PreviewProps } from './types';
import { Button } from "@/components/ui/Button";

export const TextViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
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
          throw new Error('Failed to fetch text file');
        }
        const text = await response.text();
        setContent(text);
      } catch (err) {
        console.error('Failed to load text:', err);
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
      <div className="w-full h-full flex items-center justify-center text-ink-muted">
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-danger">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>文件加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-auto bg-surface-1 p-6">
      <Button
        size="sm"
        variant="secondary"
        onClick={handleCopy}
        className="absolute top-4 right-4 text-ink-inverse flex items-center space-x-1 z-10"
      >
        <span>{copySuccess ? '✓ 已复制' : '📋 复制'}</span>
      </Button>
      <pre className="text-ink-muted text-sm font-mono whitespace-pre-wrap break-words">
        {content}
      </pre>
    </div>
  );
};

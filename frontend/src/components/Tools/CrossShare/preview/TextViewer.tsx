/**
 * 文本预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const TextViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [content, setContent] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);

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
          <div>文件加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-auto bg-slate-800 p-6">
      <pre className="text-slate-300 text-sm font-mono whitespace-pre-wrap break-words">
        {content}
      </pre>
    </div>
  );
};

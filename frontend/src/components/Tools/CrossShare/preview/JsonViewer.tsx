/**
 * JSON 预览器
 */
import React from 'react';
import ReactJsonView from 'react18-json-view';
import 'react18-json-view/src/style.css';
import { PreviewProps } from './types';
import { Button } from "@/components/ui/Button";

export const JsonViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [copySuccess, setCopySuccess] = React.useState(false);

  React.useEffect(() => {
    const fetchJson = async () => {
      try {
        // 通过后端代理获取文件内容，避免 CORS 问题
        const response = await fetch(`/api/cross-share/files/${fileId}/content`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        if (!response.ok) {
          throw new Error('Failed to fetch JSON file');
        }
        const jsonData = await response.json();
        setData(jsonData);
      } catch (err) {
        console.error('Failed to load JSON:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchJson();
  }, [fileId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
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
          <div>JSON 加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-auto bg-surface-1 p-4">
      <Button
        size="sm"
        variant="secondary"
        onClick={handleCopy}
        className="absolute top-4 right-4 text-ink-inverse flex items-center space-x-1 z-10"
      >
        <span>{copySuccess ? '✓ 已复制' : '📋 复制'}</span>
      </Button>
      <ReactJsonView
        src={data}
        theme="vitesse"
        collapsed={2}
        dark
        style={{
          backgroundColor: 'transparent',
        }}
      />
    </div>
  );
};

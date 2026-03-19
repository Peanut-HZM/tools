/**
 * JSON 预览器
 */
import React from 'react';
import ReactJsonView from 'react-json-view';
import { PreviewProps } from './types';

export const JsonViewer: React.FC<PreviewProps> = ({ url, fileName, fileId }) => {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);

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
          <div>JSON 加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-auto bg-slate-800 p-4">
      <ReactJsonView
        src={data}
        theme="monokai"
        collapsed={2}
        enableClipboard={true}
        displayDataTypes={true}
        displayObjectSize={true}
        name={null}
        style={{
          backgroundColor: 'transparent',
          fontSize: '14px',
        }}
      />
    </div>
  );
};

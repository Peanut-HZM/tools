/**
 * 视频预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const VideoViewer: React.FC<PreviewProps> = ({ fileName, fileId }) => {
  const [error, setError] = React.useState(false);

  // 从 localStorage 获取 auth token
  const authToken = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  // 在 URL 中添加 token 作为查询参数，因为 HTML5 video 标签无法设置 Authorization header
  const videoUrl = `/api/cross-share/files/${fileId}/content${authToken ? `?token=${authToken}` : ''}`;

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>视频加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-900">
      <video
        controls
        width="100%"
        height="100%"
        className="max-w-full max-h-full"
        crossOrigin="anonymous"
        onError={() => setError(true)}
      >
        <source src={videoUrl} type="video/mp4" />
        Your browser does not support video playback
      </video>
    </div>
  );
};

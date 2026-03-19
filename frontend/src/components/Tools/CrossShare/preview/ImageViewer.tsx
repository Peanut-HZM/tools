/**
 * 图片预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const ImageViewer: React.FC<PreviewProps> = ({ url, fileName }) => {
  const [error, setError] = React.useState(false);
  const [loading, setLoading] = React.useState(true);

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>图片加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-900">
      {loading && (
        <div className="absolute text-slate-400">加载中...</div>
      )}
      <img
        src={url}
        alt={fileName}
        className="max-w-full max-h-full object-contain"
        onLoad={() => setLoading(false)}
        onError={() => {
          setLoading(false);
          setError(true);
        }}
      />
    </div>
  );
};

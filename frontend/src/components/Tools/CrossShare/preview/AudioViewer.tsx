/**
 * 音频预览器
 */
import React from 'react';
import { PreviewProps } from './types';

export const AudioViewer: React.FC<PreviewProps> = ({ fileName, fileId }) => {
  const [error, setError] = React.useState(false);
  const audioUrl = `/api/cross-share/files/${fileId}/content`;

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <div className="text-4xl mb-2">❌</div>
          <div>音频加载失败</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-900">
      <div className="w-full max-w-2xl px-8">
        <audio
          controls
          className="w-full"
          crossOrigin="anonymous"
        >
          <source src={audioUrl} type="audio/mpeg" />
          Your browser does not support audio playback
        </audio>
      </div>
    </div>
  );
};

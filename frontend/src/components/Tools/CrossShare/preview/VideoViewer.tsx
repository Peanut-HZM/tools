/**
 * 视频预览器
 */
import React from 'react';
import ReactPlayer from 'react-player';
import { PreviewProps } from './types';

export const VideoViewer: React.FC<PreviewProps> = ({ url, fileName }) => {
  const [error, setError] = React.useState(false);

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
      <ReactPlayer
        url={url}
        width="100%"
        height="100%"
        controls
        playing={false}
        onError={() => setError(true)}
        config={{
          file: {
            attributes: {
              crossOrigin: 'anonymous',
            },
          },
        }}
      />
    </div>
  );
};

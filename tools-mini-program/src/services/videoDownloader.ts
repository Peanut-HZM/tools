import { request } from './request';

export interface VideoInfo {
  url: string;
  thumbnail?: string;
  title?: string;
  duration?: number;
  format?: string;
  quality?: string;
  size?: number;
}

export interface VideoExtractResponse {
  videos: VideoInfo[];
  count: number;
}

export interface VideoFormat {
  format_id: string;
  quality: string;
  resolution?: string;
  ext: string;
  size?: number;
}

export interface VideoFormatsResponse {
  formats: VideoFormat[];
  count: number;
}

export interface DownloadTaskResponse {
  task_id: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  progress: number;
  file_size?: number;
  speed?: string;
  eta?: string;
  error?: string;
  download_url?: string;
}

export const videoDownloaderApi = {
  extractVideos: async (url: string): Promise<VideoExtractResponse> => {
    return request('/tools/extract-videos', {
      method: 'POST',
      data: { url },
      needAuth: false,
    });
  },

  getVideoFormats: async (url: string): Promise<VideoFormatsResponse> => {
    return request(`/tools/video-formats?url=${encodeURIComponent(url)}`, {
      needAuth: false,
    });
  },

  createDownloadTask: async (url: string, quality = 'best'): Promise<DownloadTaskResponse> => {
    return request('/tools/download-video-ytdlp', {
      method: 'POST',
      data: { url, quality },
      needAuth: false,
    });
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    return request(`/tools/download-task/${taskId}`, {
      needAuth: false,
    });
  },

  cancelTask: async (taskId: string): Promise<{ message: string }> => {
    return request(`/tools/download-task/${taskId}`, {
      method: 'DELETE',
      needAuth: false,
    });
  },

  getDownloadStats: async (): Promise<{
    total_tasks: number;
    pending: number;
    downloading: number;
    completed: number;
    failed: number;
    success_rate: number;
  }> => {
    return request('/tools/download-stats', {
      needAuth: false,
    });
  },
};

import { request } from './request';

export interface ImageInfo {
  url: string;
  thumbnail?: string;
  width?: number;
  height?: number;
  format?: string;
  size?: number;
  filename?: string;
}

export interface ImageExtractResponse {
  images: ImageInfo[];
  count: number;
}

export interface ImageDownloadResponse {
  url: string;
  oss_url?: string;
  filename: string;
  size?: number;
  width?: number;
  height?: number;
}

export interface ImageHistoryRecord {
  id: string;
  source_url: string;
  images: ImageInfo[];
  count: number;
  created_at: string;
}

export interface ImageHistoryResponse {
  records: ImageHistoryRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface ImageQuotaResponse {
  user_id: string;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  reset_date: string;
}

export const imageDownloaderApi = {
  extractImages: async (url: string): Promise<ImageExtractResponse> => {
    return request('/image-downloader/extract-images', {
      method: 'POST',
      data: { url },
      needAuth: false,
    });
  },

  downloadImage: async (url: string, saveHistory = true): Promise<ImageDownloadResponse> => {
    return request(`/image-downloader/download?url=${encodeURIComponent(url)}&save_history=${saveHistory}`, {
      needAuth: true,
    });
  },

  getHistory: async (page = 1, pageSize = 20): Promise<ImageHistoryResponse> => {
    return request(`/image-downloader/history?page=${page}&page_size=${pageSize}`, {
      needAuth: true,
    });
  },

  getQuota: async (): Promise<ImageQuotaResponse> => {
    return request('/image-downloader/quota', {
      needAuth: true,
    });
  },

  deleteHistory: async (historyId: string): Promise<{ message: string }> => {
    return request(`/image-downloader/history/${historyId}`, {
      method: 'DELETE',
      needAuth: true,
    });
  },
};

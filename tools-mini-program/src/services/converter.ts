import { request, uploadFile } from './request';

export interface ConverterHistoryRecord {
  id: string;
  file_name: string;
  file_size: number;
  output_size: number;
  content_preview?: string;
  created_at: string;
}

export interface ConverterHistoryResponse {
  records: ConverterHistoryRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConverterQuotaResponse {
  user_id: string;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  reset_date: string;
}

export interface ConvertResponse {
  content: string;
  file_name: string;
  file_size: number;
  output_size: number;
}

export const converterApi = {
  convertFile: async (filePath: string, saveHistory = true): Promise<ConvertResponse> => {
    return uploadFile('/converter/convert', filePath, 'file', { save_history: String(saveHistory) }, true);
  },

  getHistory: async (page = 1, pageSize = 20): Promise<ConverterHistoryResponse> => {
    return request(`/converter/history?page=${page}&page_size=${pageSize}`, {
      needAuth: true,
    });
  },

  getQuota: async (): Promise<ConverterQuotaResponse> => {
    return request('/converter/quota', {
      needAuth: true,
    });
  },

  deleteHistory: async (historyId: string): Promise<{ message: string }> => {
    return request(`/converter/history/${historyId}`, {
      method: 'DELETE',
      needAuth: true,
    });
  },
};

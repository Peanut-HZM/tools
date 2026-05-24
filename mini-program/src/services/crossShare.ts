import { request, uploadFile, downloadFile } from './request';
import type { Device, Message, CrossFile, StorageStats } from '../types/crossShare';

const BASE = '/cross-share';

/**
 * 设备管理 API
 */
export const deviceApi = {
  /** 获取设备列表 */
  getDevices: async (): Promise<Device[]> => {
    const res = await request<{ devices: Device[] }>(`${BASE}/devices`);
    return res.devices || [];
  },

  /** 注册设备 */
  registerDevice: async (deviceName: string, deviceToken: string, deviceType?: string): Promise<Device> => {
    return request(`${BASE}/devices`, {
      method: 'POST',
      data: {
        device_name: deviceName,
        device_token: deviceToken,
        device_type: deviceType || 'mobile'
      }
    });
  },

  /** 更新设备活跃时间 */
  pingDevice: async (deviceId: string): Promise<Device> => {
    return request(`${BASE}/devices/${deviceId}/ping`, {
      method: 'POST'
    });
  },

  /** 删除设备 */
  deleteDevice: async (deviceId: string): Promise<void> => {
    return request(`${BASE}/devices/${deviceId}`, {
      method: 'DELETE'
    });
  }
};

/**
 * 消息功能 API
 */
export const messageApi = {
  /** 获取消息列表 */
  getMessages: async (limit = 50, offset = 0, messageType?: string): Promise<Message[]> => {
    const params: Record<string, any> = { limit, offset };
    if (messageType) params.message_type = messageType;
    const res = await request<{ messages: Message[] }>(`${BASE}/messages`, { data: params });
    return res.messages || [];
  },

  /** 发送消息 */
  sendMessage: async (content: string, messageType: string, fileId?: string): Promise<Message> => {
    return request(`${BASE}/messages`, {
      method: 'POST',
      data: { content, message_type: messageType, file_id: fileId }
    });
  },

  /** 删除消息 */
  deleteMessage: async (messageId: string): Promise<void> => {
    return request(`${BASE}/messages/${messageId}`, { method: 'DELETE' });
  },

  /** 标记消息为已读 */
  markMessageRead: async (messageId: string): Promise<Message> => {
    return request(`${BASE}/messages/${messageId}/read`, { method: 'POST' });
  },

  /** 同步剪贴板 */
  syncClipboard: async (content: string): Promise<Message> => {
    return request(`${BASE}/messages/clipboard`, {
      method: 'POST',
      data: { content }
    });
  },

  /** 获取剪贴板历史 */
  getClipboardHistory: async (limit = 50): Promise<Message[]> => {
    const res = await request<{ messages: Message[] }>(`${BASE}/messages/clipboard`, {
      data: { limit }
    });
    return res.messages || [];
  }
};

/**
 * 文件功能 API
 */
export const fileApi = {
  /** 获取文件列表 */
  getFiles: async (limit = 50, offset = 0, fileType?: string, search?: string): Promise<CrossFile[]> => {
    const params: Record<string, any> = { limit, offset };
    if (fileType) params.file_type = fileType;
    if (search) params.search = search;
    const res = await request<{ files: CrossFile[] }>(`${BASE}/files`, { data: params });
    return res.files || [];
  },

  /** 获取文件详情 */
  getFile: async (fileId: string): Promise<CrossFile> => {
    return request(`${BASE}/files/${fileId}`);
  },

  /** 上传文件 */
  uploadFile: async (filePath: string, onProgress?: (p: number) => void): Promise<any> => {
    return uploadFile(`${BASE}/files/upload`, filePath, 'file');
  },

  /** 删除文件 */
  deleteFile: async (fileId: string): Promise<void> => {
    return request(`${BASE}/files/${fileId}`, { method: 'DELETE' });
  },

  /** 获取下载链接 */
  getDownloadUrl: async (fileId: string): Promise<{ download_url: string; expires_at: string }> => {
    return request(`${BASE}/files/${fileId}/download`, { method: 'POST' });
  },

  /** 获取存储统计 */
  getStorageStats: async (): Promise<StorageStats> => {
    return request(`${BASE}/files/stats`);
  }
};

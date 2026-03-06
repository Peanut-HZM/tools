/**
 * CrossShare 跨设备共享 API 服务
 */
import axios from 'axios';

const API_BASE_URL = '/api/cross-share';

// ============ 类型定义 ============

export interface Device {
  id: string;
  user_id: string;
  device_name: string;
  device_type: 'desktop' | 'mobile' | 'tablet';
  device_token: string;
  is_active: boolean;
  last_seen_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  user_id: string;
  from_device_id?: string;
  content?: string;
  message_type: 'text' | 'file' | 'link' | 'clipboard' | 'image';
  file_id?: string;
  file?: File;
  is_read: boolean;
  is_encrypted: boolean;
  expires_at?: string;
  created_at: string;
}

export interface CrossFile {
  id: string;
  user_id: string;
  upload_device_id?: string;
  oss_bucket: string;
  oss_key: string;
  oss_url?: string;
  file_name: string;
  file_size: number;
  file_type: 'image' | 'document' | 'video' | 'audio' | 'archive' | 'text' | 'other';
  file_hash?: string;
  download_count: number;
  is_deleted: boolean;
  created_at: string;
  expires_at?: string;
}

export interface UserConfig {
  id: number;
  user_id: string;
  max_file_size: number;
  storage_quota: number;
  file_expire_days: number;
  enable_encryption: boolean;
  enable_clipboard: boolean;
  allowed_file_types?: string;
  created_at: string;
  updated_at: string;
}

export interface StorageStats {
  total_files: number;
  total_size: number;
  used_quota: number;
  available_quota: number;
  usage_percentage: number;
  files_by_type: Record<string, number>;
}

export interface UploadTokenResponse {
  token: string;
  bucket: string;
  oss_key: string;
  upload_url: string;
  file_id: string;
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_at: string;
}

// ============ API 方法 ============

/**
 * 设备管理
 */
export const deviceApi = {
  /** 获取设备列表 */
  getDevices: async (): Promise<Device[]> => {
    const response = await axios.get(`${API_BASE_URL}/devices`);
    return response.data.devices;
  },

  /** 注册设备 */
  registerDevice: async (deviceName: string, deviceToken: string, deviceType?: string): Promise<Device> => {
    const response = await axios.post(`${API_BASE_URL}/devices`, {
      device_name: deviceName,
      device_type: deviceType,
      device_token: deviceToken,
    });
    return response.data;
  },

  /** 更新设备 */
  updateDevice: async (deviceId: string, data: Partial<Device>): Promise<Device> => {
    const response = await axios.put(`${API_BASE_URL}/devices/${deviceId}`, data);
    return response.data;
  },

  /** 删除设备 */
  deleteDevice: async (deviceId: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/devices/${deviceId}`);
  },

  /** 更新设备活跃时间 */
  pingDevice: async (deviceId: string): Promise<Device> => {
    const response = await axios.post(`${API_BASE_URL}/devices/${deviceId}/ping`);
    return response.data;
  },
};

/**
 * 消息功能
 */
export const messageApi = {
  /** 获取消息列表 */
  getMessages: async (limit = 50, offset = 0, messageType?: string): Promise<Message[]> => {
    const params: Record<string, any> = { limit, offset };
    if (messageType) {
      params.message_type = messageType;
    }
    const response = await axios.get(`${API_BASE_URL}/messages`, { params });
    return response.data.messages;
  },

  /** 发送消息 */
  sendMessage: async (
    content: string,
    messageType: string,
    fileId?: string
  ): Promise<Message> => {
    const response = await axios.post(`${API_BASE_URL}/messages`, {
      content,
      message_type: messageType,
      file_id: fileId,
    });
    return response.data;
  },

  /** 删除消息 */
  deleteMessage: async (messageId: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/messages/${messageId}`);
  },

  /** 标记消息为已读 */
  markMessageRead: async (messageId: string): Promise<Message> => {
    const response = await axios.post(`${API_BASE_URL}/messages/${messageId}/read`);
    return response.data;
  },

  /** 获取剪贴板历史 */
  getClipboardHistory: async (limit = 100): Promise<Message[]> => {
    const response = await axios.get(`${API_BASE_URL}/messages/clipboard`, {
      params: { limit },
    });
    return response.data.messages;
  },

  /** 同步剪贴板 */
  syncClipboard: async (content: string): Promise<Message> => {
    const response = await axios.post(`${API_BASE_URL}/messages/clipboard`, {
      content,
    });
    return response.data;
  },
};

/**
 * 文件功能
 */
export const fileApi = {
  /** 获取文件列表 */
  getFiles: async (
    limit = 50,
    offset = 0,
    fileType?: string,
    search?: string
  ): Promise<CrossFile[]> => {
    const params: Record<string, any> = { limit, offset };
    if (fileType) {
      params.file_type = fileType;
    }
    if (search) {
      params.search = search;
    }
    const response = await axios.get(`${API_BASE_URL}/files`, { params });
    return response.data.files;
  },

  /** 获取文件详情 */
  getFile: async (fileId: string): Promise<CrossFile> => {
    const response = await axios.get(`${API_BASE_URL}/files/${fileId}`);
    return response.data;
  },

  /** 获取上传令牌 */
  getUploadToken: async (
    fileName: string,
    fileSize: number,
    fileType: string
  ): Promise<UploadTokenResponse> => {
    const response = await axios.post(`${API_BASE_URL}/files/upload`, {
      file_name: fileName,
      file_size: fileSize,
      file_type: fileType,
    });
    return response.data;
  },

  /** 上传文件到 OSS */
  uploadToOSS: async (
    file: File,
    uploadUrl: string,
    ossKey: string
  ): Promise<void> => {
    // 直传 OSS
    await axios.put(uploadUrl, file, {
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
      },
    });
  },

  /** 删除文件 */
  deleteFile: async (fileId: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/files/${fileId}`);
  },

  /** 获取下载链接 */
  getDownloadUrl: async (fileId: string): Promise<DownloadUrlResponse> => {
    const response = await axios.post(`${API_BASE_URL}/files/${fileId}/download`);
    return response.data;
  },

  /** 获取存储统计 */
  getStorageStats: async (): Promise<StorageStats> => {
    const response = await axios.get(`${API_BASE_URL}/files/stats`);
    return response.data;
  },
};

/**
 * 配置功能
 */
export const configApi = {
  /** 获取用户配置 */
  getConfig: async (): Promise<UserConfig> => {
    const response = await axios.get(`${API_BASE_URL}/config`);
    return response.data;
  },

  /** 更新用户配置 */
  updateConfig: async (data: Partial<UserConfig>): Promise<UserConfig> => {
    const response = await axios.put(`${API_BASE_URL}/config`, data);
    return response.data;
  },
};

// ============ 工具函数 ============

/**
 * 生成设备唯一标识
 */
export const generateDeviceToken = (): string => {
  const ua = navigator.userAgent;
  const platform = navigator.platform;
  const language = navigator.language;

  // 简单判断设备类型
  let deviceType = 'desktop';
  if (/mobile/i.test(ua)) {
    deviceType = 'mobile';
  } else if (/tablet/i.test(ua)) {
    deviceType = 'tablet';
  }

  // 生成设备名称
  let deviceName = 'Unknown Device';
  if (ua.includes('Mac')) {
    deviceName = 'Mac';
  } else if (ua.includes('Win')) {
    deviceName = 'Windows';
  } else if (ua.includes('Linux')) {
    deviceName = 'Linux';
  } else if (ua.includes('iPhone')) {
    deviceName = 'iPhone';
  } else if (ua.includes('iPad')) {
    deviceName = 'iPad';
  } else if (ua.includes('Android')) {
    deviceName = 'Android';
  }

  // 添加浏览器信息
  const browser = ua.includes('Chrome') ? 'Chrome' : ua.includes('Firefox') ? 'Firefox' : 'Safari';
  deviceName += ` (${browser})`;

  // 生成唯一 token
  const token = btoa(`${platform}-${language}-${Date.now()}-${Math.random()}`).replace(/[^a-zA-Z0-9]/g, '');

  return token;
};

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * 格式化日期
 */
export const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // 少于 1 分钟
  if (diff < 60000) return '刚刚';
  // 少于 1 小时
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  // 少于 24 小时
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  // 少于 7 天
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;

  // 超过 7 天显示具体日期
  return date.toLocaleDateString('zh-CN');
};

/**
 * 获取文件类型图标
 */
export const getFileTypeIcon = (fileType: string): string => {
  const icons: Record<string, string> = {
    image: '🖼️',
    document: '📄',
    video: '🎬',
    audio: '🎵',
    archive: '📦',
    text: '📝',
    other: '📎',
  };
  return icons[fileType] || icons.other;
};

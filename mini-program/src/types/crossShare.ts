/**
 * CrossShare 类型定义（与 PC 端共享）
 */

// 设备类型
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

// 消息类型
export interface Message {
  id: string;
  user_id: string;
  from_device_id?: string;
  content?: string;
  message_type: 'text' | 'file' | 'link' | 'clipboard' | 'image';
  file_id?: string;
  is_read: boolean;
  is_encrypted: boolean;
  expires_at?: string;
  created_at: string;
}

// 文件类型
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

// 存储统计
export interface StorageStats {
  total_files: number;
  total_size: number;
  used_quota: number;
  available_quota: number;
  usage_percentage: number;
  files_by_type: Record<string, number>;
}

// 用户配置
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

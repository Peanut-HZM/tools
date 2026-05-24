/**
 * 通用类型定义（与 PC 端共享）
 */

// 用户信息
export interface User {
  id: string;
  username: string;
  email?: string;
  role: 'admin' | 'user';
  created_at: string;
}

// 认证响应（匹配后端 AuthResponse）
export interface AuthResponse {
  user_id: string;
  username: string;
  email: string;
  role: string;
  token: string;
  phone?: string;
}

// 工具信息（匹配后端 Tool 模型）
export interface Tool {
  id: string;
  icon: string;
  iconColor?: string;
  title: string;
  description: string;
  rating?: number;
  usageCount?: string;
  category: string;
  status?: string;
  sort_order?: number;
  created_at?: string;
  custom_icon_url?: string;
  show_pc?: boolean;
  show_mobile?: boolean;
  require_login?: boolean;
  // 小程序端补充字段
  path?: string;
}

// 工具分类
export type ToolCategory =
  | 'all'
  | 'media'
  | 'text'
  | 'dev'
  | 'ai'
  | 'utility'
  | 'share';

export interface CategoryInfo {
  key: ToolCategory;
  label: string;
  icon: string;
}

// 通用 API 响应
export interface ApiResponse<T = any> {
  detail?: string;
  [key: string]: any;
}

// 分页参数
export interface PaginationParams {
  limit?: number;
  offset?: number;
}

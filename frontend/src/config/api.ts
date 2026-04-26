/**
 * API配置
 * 支持通过环境变量配置API地址
 * 开发环境：.env.development
 * 生产环境：.env.production
 */

// 从环境变量获取API地址
const getApiBaseUrl = (): string => {
  // 优先使用环境变量中的配置
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  
  // 生产构建且无环境变量时使用相对路径
  if (import.meta.env.PROD) {
    return '/api';
  }
  
  // 开发环境默认地址
  return 'http://127.0.0.1:19092/api';
};

export const API_BASE_URL = getApiBaseUrl();

// 导出各个模块的API地址
export const AUTH_API_BASE_URL = `${API_BASE_URL}/auth`;
export const MARKDOWN_EDITOR_API_BASE_URL = `${API_BASE_URL}/markdown-editor`;
export const CONVERTER_API_BASE_URL = `${API_BASE_URL}/converter`;

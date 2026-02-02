/**
 * API配置
 * 支持通过环境变量配置API地址
 */

// 从环境变量获取API地址，生产环境使用相对路径，开发环境使用localhost
const getApiBaseUrl = (): string => {
  // Vite环境变量
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  
  // 生产环境使用相对路径
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

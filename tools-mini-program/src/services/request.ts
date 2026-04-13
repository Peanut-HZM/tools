import Taro from '@tarojs/taro';

const API_BASE_URL = process.env.TARO_APP_API_URL || 'http://localhost:19092/api';

/**
 * 获取请求头（包含认证 token）
 */
function getHeaders(): Record<string, string> {
  const token = Taro.getStorageSync('auth_token');
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return {
    'Content-Type': 'application/json'
  };
}

/**
 * 封装 Taro.request，支持认证
 */
export async function request<T = any>(
  url: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    data?: any;
    needAuth?: boolean;
  } = {}
): Promise<T> {
  const { method = 'GET', data, needAuth = true } = options;

  const headers = needAuth ? getHeaders() : { 'Content-Type': 'application/json' };

  try {
    const res = await Taro.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header: headers,
      timeout: 15000
    });

    if (res.statusCode === 401) {
      handleAuthExpired()
      throw new Error('认证已过期，请重新登录')
    }

    return res.data as T;
  } catch (error: any) {
    console.error(`[API Error] ${method} ${url}:`, error);
    throw error;
  }
}

/**
 * 上传文件
 */
export async function uploadFile(
  url: string,
  filePath: string,
  name: string = 'file',
  formData: Record<string, any> = {},
  needAuth: boolean = true
): Promise<any> {
  const token = needAuth ? Taro.getStorageSync('auth_token') : null;
  const header = token ? { 'Authorization': `Bearer ${token}` } : {};

  try {
    const res = await Taro.uploadFile({
      url: `${API_BASE_URL}${url}`,
      filePath,
      name,
      formData,
      header,
      timeout: 60000
    });

    if (res.statusCode === 401) {
      handleAuthExpired()
      throw new Error('认证已过期，请重新登录')
    }

    return JSON.parse(res.data);
  } catch (error: any) {
    console.error(`[Upload Error] ${url}:`, error);
    throw error;
  }
}

/**
 * 下载文件
 */
export async function downloadFile(
  url: string,
  needAuth: boolean = true
): Promise<string> {
  const token = Taro.getStorageSync('auth_token');
  const header = needAuth && token ? { 'Authorization': `Bearer ${token}` } : {};

  try {
    const res = await Taro.downloadFile({
      url: `${API_BASE_URL}${url}`,
      header,
      timeout: 60000
    });

    if (res.statusCode === 401) {
      handleAuthExpired()
      throw new Error('认证已过期，请重新登录')
    }

    return res.tempFilePath;
  } catch (error: any) {
    console.error(`[Download Error] ${url}:`, error);
    throw error;
  }
}

/**
 * 处理认证过期：清除存储、提示用户、跳转登录页
 */
function handleAuthExpired() {
  Taro.removeStorageSync('auth_token')
  Taro.removeStorageSync('user_info')
  Taro.showToast({ title: '认证已过期，请重新登录', icon: 'none', duration: 1500 })
  setTimeout(() => {
    const pages = Taro.getCurrentPages()
    const currentPage = pages[pages.length - 1]
    const redirect = currentPage?.route ? `/${currentPage.route}` : '/'
    Taro.redirectTo({
      url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}`,
      fail: () => {
        Taro.reLaunch({ url: `/pages/login/index?redirect=${encodeURIComponent(redirect)}` })
      }
    })
  }, 1500)
}

export { API_BASE_URL, getHeaders };

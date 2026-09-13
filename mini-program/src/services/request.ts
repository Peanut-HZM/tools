import Taro from '@tarojs/taro';

// API 地址必须通过 TARO_APP_API_URL 环境变量注入（见 .env.development / .env.production / .env.test）
// 不再内置默认域名，避免泄露部署方信息。
//
// 读取说明：TARO_APP_* 在构建期由 DefinePlugin 替换为字符串字面量——env 配置齐全时
// 此处就是常量，运行时不抛错；本机缺 .env 文件时字面量原样留进产物，而微信运行时
// 没有 process 对象，求值会抛 ReferenceError，用 try/catch 兜底为空串（保留下方 warn）。
// 注意不能用 typeof process 守护：DefinePlugin 只替换 process.env.*，不替换裸 process，
// 微信运行时 typeof 判断恒为 false，会把已注入的地址也短路掉（386bc827 的回归教训）。
function readTaroAppApiUrl(): string {
  try {
    // @ts-expect-error process 在微信运行时可能未定义，ReferenceError 由 catch 兜底
    return process.env.TARO_APP_API_URL || '';
  } catch {
    return '';
  }
}

const TARO_APP_API_URL = readTaroAppApiUrl();

const API_BASE_URL =
  TARO_APP_API_URL && TARO_APP_API_URL !== 'https://your-domain.com/api'
    ? TARO_APP_API_URL
    : '';

if (!API_BASE_URL) {
  // 仅在开发期/启动时提示一次；生产环境请确保 TARO_APP_API_URL 已正确配置
  // eslint-disable-next-line no-console
  console.warn('[mini-program] TARO_APP_API_URL 未配置，请在 .env 中设置');
}

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

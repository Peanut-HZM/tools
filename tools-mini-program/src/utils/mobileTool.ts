import Taro from '@tarojs/taro';

export interface ChooseFileResult {
  path: string;
  name: string;
  size: number;
  type: string;
}

export async function chooseFileCompat(options: {
  accept?: string;
  maxSize?: number;
} = {}): Promise<ChooseFileResult> {
  const { accept = '*/*', maxSize = 10 * 1024 * 1024 } = options;

  return new Promise((resolve, reject) => {
    Taro.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: accept === 'image/*' ? ['jpg', 'jpeg', 'png', 'gif', 'webp'] :
                 accept === 'document/*' ? ['doc', 'docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx'] :
                 undefined,
      success: (res) => {
        const file = res.tempFiles[0];
        if (file.size > maxSize) {
          reject(new Error(`文件大小超过 ${maxSize / 1024 / 1024}MB 限制`));
          return;
        }
        resolve({
          path: file.path,
          name: file.name,
          size: file.size,
          type: file.type || 'application/octet-stream',
        });
      },
      fail: (err) => reject(new Error(err.errMsg || '选择文件失败')),
    });
  });
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await Taro.setClipboardData({ data: text });
    Taro.showToast({ title: '已复制', icon: 'success' });
    return true;
  } catch {
    Taro.showToast({ title: '复制失败', icon: 'none' });
    return false;
  }
}

export async function openOrCopyUrl(url: string): Promise<void> {
  try {
    await Taro.setClipboardData({ data: url });
    Taro.showToast({ title: '链接已复制', icon: 'success' });
  } catch {
    Taro.showToast({ title: '复制失败', icon: 'none' });
  }
}

export function formatApiError(error: any): string {
  if (typeof error === 'string') return error;
  if (error?.detail) return error.detail;
  if (error?.message) return error.message;
  return '请求失败，请稍后重试';
}

export interface PollOptions {
  interval?: number;
  maxAttempts?: number;
  timeout?: number;
}

export async function pollTask<T>(
  checkFn: () => Promise<T>,
  isComplete: (result: T) => boolean,
  options: PollOptions = {}
): Promise<T> {
  const { interval = 2000, maxAttempts = 60, timeout = 120000 } = options;
  const startTime = Date.now();

  for (let i = 0; i < maxAttempts; i++) {
    if (Date.now() - startTime > timeout) {
      throw new Error('任务处理超时，请稍后查看历史记录');
    }
    const result = await checkFn();
    if (isComplete(result)) return result;
    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error('轮询次数超限，请稍后查看历史记录');
}

export function safeJsonParse(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

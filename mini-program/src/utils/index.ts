/**
 * 工具函数（与 PC 端共享的纯逻辑）
 */

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * 格式化日期
 * 兼容 iOS JavaScriptCore：将 ISO 8601 含时区偏移的字符串预处理为
 * "yyyy/MM/dd HH:mm:ss" 格式（iOS 原生支持），避免 new Date() 返回 NaN。
 */
export function formatDateTime(dateStr: string): string {
  const date = parseDateSafe(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
  return date.toLocaleDateString('zh-CN');
}

/**
 * 跨平台日期解析：兼容 iOS JavaScriptCore 对 ISO 8601 时区偏移格式（如
 * "2026-05-30T21:07:06.015480+08:00"）的不支持。
 *
 * 策略：先用 new Date() 尝试，若结果为 Invalid Date 则手动解析 ISO 字符串
 * 为 "yyyy/MM/dd HH:mm:ss" 再构造（iOS 原生支持的唯一带时间的格式）。
 */
export function parseDateSafe(dateStr: string): Date {
  const direct = new Date(dateStr);
  if (!isNaN(direct.getTime())) return direct;

  // 手动解析 ISO 8601: "2026-05-30T21:07:06.015480+08:00" 或 "2026-05-30 21:07:06"
  const m = dateStr.match(
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?$/
  );
  if (!m) return direct; // 无法解析，返回原始结果（保持 NaN 以便调用方感知）

  // iOS 只支持 "yyyy/MM/dd HH:mm:ss" 格式
  const iosSafe = `${m[1]}/${m[2]}/${m[3]} ${m[4]}:${m[5]}:${m[6] || '00'}`;
  const parsed = new Date(iosSafe);
  return isNaN(parsed.getTime()) ? direct : parsed;
}

/**
 * 检测内容类型
 */
export function detectContentType(content: string): 'json' | 'code' | 'text' {
  const trimmed = content.trim();
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      JSON.parse(trimmed);
      return 'json';
    } catch {
      // not valid json, fall through
    }
  }
  if (/^```[\w]*\n[\s\S]*```$/s.test(trimmed)) {
    return 'code';
  }
  return 'text';
}

/**
 * 判断是否是 URL
 */
export function isUrl(text: string): boolean {
  try {
    new URL(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

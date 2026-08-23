/**
 * localStorage 持久化缓存工具
 * TTL 默认 5 分钟，用于减少重复 API 请求
 */

const DEFAULT_TTL = 30 * 1000; // 30 秒

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

/**
 * 从缓存读取数据
 * @param key 缓存键
 * @returns 缓存数据或 null（过期/不存在）
 */
export function getCached<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;

    const entry: CacheEntry<T> = JSON.parse(raw);
    const now = Date.now();

    // 检查是否过期
    if (now - entry.timestamp > entry.ttl) {
      localStorage.removeItem(key);
      return null;
    }

    return entry.data;
  } catch (e) {
    console.warn(`[Cache] 读取缓存失败: ${key}`, e);
    return null;
  }
}

/**
 * 写入缓存
 * @param key 缓存键
 * @param data 缓存数据
 * @param ttl 过期时间（毫秒），默认 5 分钟
 */
export function setCache<T>(key: string, data: T, ttl: number = DEFAULT_TTL): void {
  try {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl,
    };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch (e) {
    console.warn(`[Cache] 写入缓存失败: ${key}`, e);
  }
}

/**
 * 清除缓存
 * @param key 缓存键
 */
export function clearCache(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.warn(`[Cache] 清除缓存失败: ${key}`, e);
  }
}

/**
 * 清除所有工具相关缓存
 */
export function clearToolsCache(): void {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('categories') || key.startsWith('tools:'))) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
  } catch (e) {
    console.warn('[Cache] 清除工具缓存失败', e);
  }
}

import { Tool, ToolCategory } from '../types';
import { API_BASE_URL } from '../config/api';

// ==================== Promise 缓存（请求去重） ====================

interface CacheEntry {
  promise: Promise<any>;
  expiry: number;
}

const promiseCache = new Map<string, CacheEntry>();
const CACHE_TTL = 30_000; // 30 秒

function cachedFetch<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  const cached = promiseCache.get(key);
  if (cached && Date.now() < cached.expiry) {
    return cached.promise;
  }
  const promise = fetcher();
  promiseCache.set(key, { promise, expiry: Date.now() + CACHE_TTL });
  promise.then(
    () => {
      // 成功：30 秒后自动清除
      setTimeout(() => promiseCache.delete(key), CACHE_TTL);
    },
    () => {
      // 失败：立即清除，不缓存错误结果
      promiseCache.delete(key);
    }
  );
  return promise;
}

// ==================== API 函数 ====================

export async function fetchCategories(signal?: AbortSignal): Promise<ToolCategory[]> {
  const key = `${API_BASE_URL}/categories`;
  return cachedFetch(key, async () => {
    const response = await fetch(key, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    return await response.json();
  });
}

export async function fetchTools(platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  const url = platform
    ? `${API_BASE_URL}/tools?platform=${platform}`
    : `${API_BASE_URL}/tools`;
  return cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    const data = await response.json();
    return data.tools;
  });
}

export async function searchTools(query: string, signal?: AbortSignal): Promise<Tool[]> {
  const url = `${API_BASE_URL}/tools/search?q=${encodeURIComponent(query)}`;
  return cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to search tools');
    }
    const data = await response.json();
    return data.tools;
  });
}

export async function fetchToolsByCategory(category: string, platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  const params = new URLSearchParams();
  if (platform) params.append('platform', platform);
  const url = `${API_BASE_URL}/tools/category/${encodeURIComponent(category)}?${params.toString()}`;
  return cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch tools by category');
    }
    const data = await response.json();
    return data.tools;
  });
}

export async function loadToolsByCategory(category: string, platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  return fetchToolsByCategory(category, platform, signal);
}

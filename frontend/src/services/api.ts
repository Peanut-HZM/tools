import { Tool, ToolCategory } from '../types';
import { API_BASE_URL } from '../config/api';
import { getCached, setCache } from '../utils/cache';

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
  // 1. 尝试从 localStorage 缓存读取
  const cached = getCached<ToolCategory[]>('categories');
  if (cached) {
    return cached;
  }

  // 2. 缓存未命中，发起请求
  const key = `${API_BASE_URL}/categories`;
  const data = await cachedFetch(key, async () => {
    const response = await fetch(key, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    return await response.json();
  });

  // 3. 写入 localStorage 缓存
  setCache('categories', data);

  return data;
}

export async function fetchTools(platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  const cacheKey = `tools:${platform || 'all'}`;

  // 1. 尝试从 localStorage 缓存读取
  const cached = getCached<Tool[]>(cacheKey);
  if (cached) {
    return cached;
  }

  // 2. 缓存未命中，发起请求
  const url = platform
    ? `${API_BASE_URL}/tools?platform=${platform}`
    : `${API_BASE_URL}/tools`;
  const data = await cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    const result = await response.json();
    return result.tools;
  });

  // 3. 写入 localStorage 缓存
  setCache(cacheKey, data);

  return data;
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

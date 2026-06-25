/**
 * 基于 IndexedDB 的离线缓存工具
 * 用于缓存数据库工具的各类数据，减少重复 API 请求
 */

interface CacheEntry {
  data: unknown;
  timestamp: number;
  expiresAt: number;
}

interface CacheConfig {
  [key: string]: { ttl: number };
}

// 缓存 TTL 配置
const CACHE_CONFIG: CacheConfig = {
  configs: { ttl: 30 * 60 * 1000 },        // 连接列表：30 分钟
  databases: { ttl: 30 * 60 * 1000 },       // 数据库列表：30 分钟
  structure: { ttl: 60 * 60 * 1000 },       // 表结构：1 小时（表结构低频变动）
  history: { ttl: 60 * 60 * 1000 },         // 执行历史：1 小时
};

const DB_NAME = 'dbToolCache';
const STORE_NAME = 'cacheStore';
const DB_VERSION = 1;

let dbPromise: Promise<IDBDatabase> | null = null;

/**
 * 打开/创建 IndexedDB 数据库
 */
function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;

  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);

    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'key' });
      }
    };
  });

  return dbPromise;
}

export class DBCache {
  /**
   * 获取缓存数据，过期或不存在时返回 undefined
   */
  static async get<T>(cacheKey: string): Promise<T | undefined> {
    try {
      const db = await openDB();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.get(cacheKey);

        request.onsuccess = () => {
          const entry: CacheEntry | undefined = request.result;
          if (!entry) {
            resolve(undefined);
            return;
          }
          if (Date.now() > entry.expiresAt) {
            // 已过期，删除并返回 undefined
            DBCache.invalidate(cacheKey);
            resolve(undefined);
            return;
          }
          resolve(entry.data as T);
        };

        request.onerror = () => {
          console.warn('[DBCache] 读取缓存失败:', request.error);
          resolve(undefined);
        };
      });
    } catch {
      return undefined;
    }
  }

  /**
   * 获取缓存数据，返回 { data, isStale } 结构。
   * 即使过期也返回数据（供 stale-while-revalidate 策略使用）。
   * 不存在时返回 undefined。
   */
  static async getRaw<T>(cacheKey: string): Promise<{ data: T; isStale: boolean } | undefined> {
    try {
      const db = await openDB();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.get(cacheKey);

        request.onsuccess = () => {
          const entry: CacheEntry | undefined = request.result;
          if (!entry) {
            resolve(undefined);
            return;
          }
          resolve({
            data: entry.data as T,
            isStale: Date.now() > entry.expiresAt,
          });
        };

        request.onerror = () => {
          console.warn('[DBCache] getRaw 读取失败:', request.error);
          resolve(undefined);
        };
      });
    } catch {
      return undefined;
    }
  }

  /**
   * 设置缓存数据，根据 ttlKey 自动计算过期时间
   */
  static async set<T>(cacheKey: string, data: T, ttlKey: keyof typeof CACHE_CONFIG): Promise<void> {
    try {
      const db = await openDB();
      const ttl = CACHE_CONFIG[ttlKey]?.ttl ?? 5 * 60 * 1000;
      const entry: CacheEntry = {
        data,
        timestamp: Date.now(),
        expiresAt: Date.now() + ttl,
      };

      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.put({ key: cacheKey, ...entry });
        tx.oncomplete = () => resolve();
        tx.onerror = () => {
          console.warn('[DBCache] 写入缓存失败:', tx.error);
          resolve();
        };
      });
    } catch {
      // 静默失败，不影响主流程
    }
  }

  /**
   * 清除指定缓存
   */
  static async invalidate(cacheKey: string): Promise<void> {
    try {
      const db = await openDB();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.delete(cacheKey);
        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      });
    } catch {
      // 静默失败
    }
  }

  /**
   * 批量清除匹配前缀的缓存
   * 例如 invalidatePrefix('databases:') 会清除所有以 databases: 开头的缓存
   */
  static async invalidatePrefix(prefix: string): Promise<void> {
    try {
      const db = await openDB();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const request = store.openCursor();

        request.onsuccess = () => {
          const cursor = request.result;
          if (cursor) {
            if ((cursor.value as { key: string }).key.startsWith(prefix)) {
              cursor.delete();
            }
            cursor.continue();
          }
        };

        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      });
    } catch {
      // 静默失败
    }
  }

  /**
   * 清除所有缓存
   */
  static async clear(): Promise<void> {
    try {
      const db = await openDB();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.clear();
        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      });
    } catch {
      // 静默失败
    }
  }
}

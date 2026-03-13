/**
 * Cursor 对话历史缓存工具
 * 使用 IndexedDB 实现本地缓存，提升加载性能
 */

const DB_NAME = 'CursorHistoryCache';
const DB_VERSION = 1;
const STORE_NAME = 'sessions';
const CACHE_EXPIRY_MS = 5 * 60 * 1000; // 5 分钟缓存过期

interface CacheEntry {
  composer_id: string;
  data: any;
  timestamp: number;
  project_name?: string;
  session_name?: string;
}

interface CacheDatabase {
  db: IDBDatabase | null;
  open(): Promise<IDBDatabase>;
  get(composerId: string): Promise<CacheEntry | null>;
  set(entry: CacheEntry): Promise<void>;
  clear(): Promise<void>;
  getAllKeys(): Promise<string[]>;
}

/**
 * IndexedDB 缓存实现
 */
export const cursorCache: CacheDatabase = {
  db: null,

  /**
   * 打开数据库连接
   */
  async open(): Promise<IDBDatabase> {
    if (this.db) {
      return this.db;
    }

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('打开 IndexedDB 失败:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve(request.result);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'composer_id' });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('project_name', 'project_name', { unique: false });
        }
      };
    });
  },

  /**
   * 从缓存获取会话数据
   * @param composerId 会话 ID
   * @returns 缓存的数据，如果不存在或已过期则返回 null
   */
  async get(composerId: string): Promise<CacheEntry | null> {
    try {
      const db = await this.open();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.get(composerId);

        request.onsuccess = () => {
          const entry = request.result as CacheEntry | undefined;

          if (!entry) {
            resolve(null);
            return;
          }

          // 检查缓存是否过期
          const now = Date.now();
          if (now - entry.timestamp > CACHE_EXPIRY_MS) {
            // 缓存过期，删除并返回 null
            this.delete(composerId).catch(console.error);
            resolve(null);
            return;
          }

          resolve(entry);
        };

        request.onerror = () => {
          console.error('读取缓存失败:', request.error);
          resolve(null);
        };
      });
    } catch (error) {
      console.error('IndexedDB 错误:', error);
      return null;
    }
  },

  /**
   * 将会话数据存入缓存
   * @param entry 缓存条目
   */
  async set(entry: CacheEntry): Promise<void> {
    try {
      const db = await this.open();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.put(entry);

        request.onsuccess = () => {
          resolve();
        };

        request.onerror = () => {
          console.error('写入缓存失败:', request.error);
          reject(request.error);
        };
      });
    } catch (error) {
      console.error('IndexedDB 错误:', error);
    }
  },

  /**
   * 从缓存删除会话数据
   * @param composerId 会话 ID
   */
  async delete(composerId: string): Promise<void> {
    try {
      const db = await this.open();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.delete(composerId);

        request.onsuccess = () => {
          resolve();
        };

        request.onerror = () => {
          console.error('删除缓存失败:', request.error);
          reject(request.error);
        };
      });
    } catch (error) {
      console.error('IndexedDB 错误:', error);
    }
  },

  /**
   * 清空所有缓存
   */
  async clear(): Promise<void> {
    try {
      const db = await this.open();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.clear();

        request.onsuccess = () => {
          resolve();
        };

        request.onerror = () => {
          console.error('清空缓存失败:', request.error);
          reject(request.error);
        };
      });
    } catch (error) {
      console.error('IndexedDB 错误:', error);
    }
  },

  /**
   * 获取所有缓存的键
   */
  async getAllKeys(): Promise<string[]> {
    try {
      const db = await this.open();

      return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.getAllKeys();

        request.onsuccess = () => {
          resolve(request.result as string[]);
        };

        request.onerror = () => {
          console.error('读取缓存键失败:', request.error);
          reject(request.error);
        };
      });
    } catch (error) {
      console.error('IndexedDB 错误:', error);
      return [];
    }
  },
};

/**
 * 缓存会话消息数据
 * @param composerId 会话 ID
 * @param messages 消息数据
 * @param projectName 项目名
 * @param sessionName 会话名
 */
export async function cacheSessionMessages(
  composerId: string,
  messages: any[],
  projectName?: string,
  sessionName?: string
): Promise<void> {
  await cursorCache.set({
    composer_id: composerId,
    data: { messages },
    timestamp: Date.now(),
    project_name: projectName,
    session_name: sessionName,
  });
}

/**
 * 从缓存获取会话消息
 * @param composerId 会话 ID
 * @returns 消息数据，如果缓存不存在或已过期则返回 null
 */
export async function getCachedSessionMessages(
  composerId: string
): Promise<any[] | null> {
  const entry = await cursorCache.get(composerId);
  return entry?.data?.messages || null;
}

/**
 * 检查缓存是否命中
 * @param composerId 会话 ID
 * @returns 是否命中缓存
 */
export async function checkCacheHit(composerId: string): Promise<boolean> {
  const entry = await cursorCache.get(composerId);
  return entry !== null;
}

/**
 * 清理过期缓存
 */
export async function cleanupExpiredCache(): Promise<void> {
  const keys = await cursorCache.getAllKeys();
  const now = Date.now();

  for (const key of keys) {
    const entry = await cursorCache.get(key);
    if (entry && now - entry.timestamp > CACHE_EXPIRY_MS) {
      await cursorCache.delete(key);
    }
  }
}

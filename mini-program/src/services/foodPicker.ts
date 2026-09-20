import Taro from '@tarojs/taro';

/**
 * "今天吃什么"工具 — 美食清单本地存储服务。
 *
 * 设计说明：
 * - 该工具的数据完全属于个人偏好，无跨设备同步诉求，因此不走后端 API，
 *   清单存 Taro 本地存储（key: food_picker_items），图片复制到
 *   USER_DATA_PATH 专属目录持久化（本地用户文件配额 200MB，远大于
 *   chooseImage 返回的临时目录会被运行时回收的问题）。
 * - 图片仅作为可选字段：无图美食在 UI 层以 emoji 兜底展示，
 *   存储结构不区分有无图片两种形态。
 */

/** 单条美食记录 */
export interface FoodItem {
  id: string;
  /** 美食名称（必填） */
  name: string;
  /** 备注（可选，如忌口、推荐店） */
  note?: string;
  /** 本地持久化图片路径（可选，USER_DATA_PATH 下） */
  image?: string;
  createdAt: number;
}

/** 存储键名 */
const STORAGE_KEY = 'food_picker_items';
/** 图片持久化目录（USER_DATA_PATH 下） */
const IMAGE_DIR = `${Taro.env.USER_DATA_PATH}/food_picker_images`;

/** 生成记录 id：时间戳 + 随机段，本地单用户场景足够避免碰撞 */
function genId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

/** 确保图片目录存在（已存在时 mkdirSync 抛错属预期，直接忽略） */
function ensureImageDir(): void {
  const fs = Taro.getFileSystemManager();
  try {
    fs.mkdirSync(IMAGE_DIR, true);
  } catch {
    // 目录已存在（recursive=true 下仍可能抛 already exists），无需处理
  }
}

/** 读取全部美食清单 */
export function loadFoods(): FoodItem[] {
  const items = Taro.getStorageSync(STORAGE_KEY);
  return Array.isArray(items) ? (items as FoodItem[]) : [];
}

/** 全量写回美食清单 */
export function saveFoods(items: FoodItem[]): void {
  Taro.setStorageSync(STORAGE_KEY, items);
}

/**
 * 把选图返回的临时文件复制到持久化目录。
 * 参数：tempFilePath - Taro.chooseImage 返回的临时路径
 * 返回：持久化后的绝对路径
 */
export function persistImage(tempFilePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    ensureImageDir();
    const ext = tempFilePath.includes('.') ? tempFilePath.split('.').pop() : 'jpg';
    const target = `${IMAGE_DIR}/${genId()}.${ext || 'jpg'}`;
    const fs = Taro.getFileSystemManager();
    fs.copyFile({
      srcPath: tempFilePath,
      destPath: target,
      success: () => resolve(target),
      fail: (err) => reject(new Error(err.errMsg || '保存图片失败')),
    });
  });
}

/**
 * 删除持久化图片文件。删除失败只记录日志不抛出：
 * 文件清理属于附带动作，失败不应阻断清单条目的删除流程。
 */
export function removeImageFile(path?: string): void {
  if (!path || !path.startsWith(IMAGE_DIR)) return;
  const fs = Taro.getFileSystemManager();
  fs.unlink({
    filePath: path,
    fail: (err) => console.error('[food-picker] 删除图片文件失败:', err.errMsg),
  });
}

/** 新增美食（name 由调用方保证非空） */
export function addFood(name: string, note: string, image?: string): FoodItem {
  const items = loadFoods();
  const item: FoodItem = { id: genId(), name: name.trim(), note: note.trim() || undefined, image, createdAt: Date.now() };
  saveFoods([...items, item]);
  return item;
}

/** 更新已有美食（返回是否命中） */
export function updateFood(id: string, name: string, note: string, image?: string): boolean {
  const items = loadFoods();
  const idx = items.findIndex((it) => it.id === id);
  if (idx === -1) return false;
  items[idx] = { ...items[idx], name: name.trim(), note: note.trim() || undefined, image };
  saveFoods(items);
  return true;
}

/** 删除美食（同时清理其持久化图片），返回是否命中 */
export function deleteFood(id: string): boolean {
  const items = loadFoods();
  const idx = items.findIndex((it) => it.id === id);
  if (idx === -1) return false;
  removeImageFile(items[idx].image);
  saveFoods(items.filter((it) => it.id !== id));
  return true;
}

/**
 * 从清单中随机抽取 count 个不重复结果（Fisher-Yates 局部洗牌）。
 * count 大于清单长度时返回全量打乱结果。
 */
export function pickRandomFoods(items: FoodItem[], count: number): FoodItem[] {
  const pool = [...items];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, Math.max(1, Math.min(count, pool.length)));
}

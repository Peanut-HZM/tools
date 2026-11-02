/**
 * 客户端设备标识
 *
 * 用途：同一用户可能在多台设备上使用本应用，各设备对「显示偏好」
 * （数据库工具的可见连接 / 可见数据库）的设置应互不影响、各自回显。
 *
 * 机制：
 * 1. 首次访问时生成一个随机 UUID，存入 localStorage
 * 2. 之后每次请求都通过 `X-Device-Id` 请求头带上
 * 3. 后端按 (user_id, device_id) 维度存取该用户的偏好
 *
 * 注意：
 * - 清除浏览器数据 / 换浏览器 / 无痕模式 会产生新的 device_id，
 *   此时该「设备」视为新设备，偏好回到默认值（全部显示）。
 * - device_id 只用于「同一用户下区分设备」，不作为鉴权凭据。
 */
import { safeGetItem, safeSetItem } from './localStorage';

const DEVICE_ID_KEY = 'toolbox_client_device_id';
const DEVICE_ID_HEADER = 'X-Device-Id';

/** 生成随机 UUID（优先用浏览器原生 API） */
function generateUuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // 回退：手动拼 UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (ch) => {
    const rand = (Math.random() * 16) | 0;
    const v = ch === 'x' ? rand : (rand & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * 获取本机设备标识（首次调用时生成并持久化）
 */
export function getClientDeviceId(): string {
  const existing = safeGetItem(DEVICE_ID_KEY);
  if (existing && existing.trim()) {
    return existing.trim();
  }
  const generated = generateUuid();
  safeSetItem(DEVICE_ID_KEY, generated);
  return generated;
}

/**
 * 构造带设备标识的请求头
 *
 * 入参兼容 HeadersInit（Record<string,string> | Headers | string[][]），
 * 统一转成普通对象后再追加 X-Device-Id。
 */
export function withDeviceId(headers: HeadersInit = {}): Record<string, string> {
  const base: Record<string, string> = {};

  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      base[key] = value;
    });
  } else if (Array.isArray(headers)) {
    headers.forEach(([key, value]) => {
      base[key] = value;
    });
  } else {
    Object.assign(base, headers);
  }

  base[DEVICE_ID_HEADER] = getClientDeviceId();
  return base;
}

export { DEVICE_ID_HEADER, DEVICE_ID_KEY };

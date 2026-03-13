/**
 * 最近访问记录管理工具
 * 使用 localStorage 存储最近访问的会话记录
 */

export interface RecentSession {
  composer_id: string;
  session_name: string;
  project_name: string;
  workspace_hash: string;
  visited_at: number;
}

const STORAGE_KEY = 'cursor_history_recent_sessions';
const MAX_RECENT_SESSIONS = 10;

/**
 * 添加访问记录
 * @param session 会话信息
 */
export function addRecentSession(session: RecentSession): void {
  try {
    const sessions = getRecentSessions();

    // 如果已存在，先移除（避免重复）
    const filtered = sessions.filter(s => s.composer_id !== session.composer_id);

    // 添加到开头
    const updated = [
      { ...session, visited_at: Date.now() },
      ...filtered.slice(0, MAX_RECENT_SESSIONS - 1)
    ];

    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('保存最近访问记录失败:', error);
  }
}

/**
 * 获取最近访问记录
 * @returns 最近访问的会话列表
 */
export function getRecentSessions(): RecentSession[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) {
      return [];
    }
    return JSON.parse(data) as RecentSession[];
  } catch (error) {
    console.error('读取最近访问记录失败:', error);
    return [];
  }
}

/**
 * 删除指定访问记录
 * @param composerId 会话 ID
 */
export function removeRecentSession(composerId: string): void {
  try {
    const sessions = getRecentSessions();
    const updated = sessions.filter(s => s.composer_id !== composerId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('删除最近访问记录失败:', error);
  }
}

/**
 * 清空所有访问记录
 */
export function clearRecentSessions(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('清空最近访问记录失败:', error);
  }
}

/**
 * 格式化访问时间
 * @param timestamp 时间戳
 * @returns 格式化后的时间字符串
 */
export function formatVisitedTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  // 少于 1 分钟
  if (diff < 60 * 1000) {
    return '刚刚';
  }

  // 少于 1 小时
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000));
    return `${minutes} 分钟前`;
  }

  // 少于 24 小时
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000));
    return `${hours} 小时前`;
  }

  // 超过 24 小时，显示日期
  const date = new Date(timestamp);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hour = date.getHours().toString().padStart(2, '0');
  const minute = date.getMinutes().toString().padStart(2, '0');
  return `${month}/${day} ${hour}:${minute}`;
}

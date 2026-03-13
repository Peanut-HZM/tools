/**
 * Cursor 对话历史统计工具
 * 提供会话和消息的统计分析功能
 */

export interface StatsOverview {
  total_sessions: number;
  total_messages: number;
  today_sessions: number;
  today_messages: number;
  total_projects: number;
}

export interface StatsTrendItem {
  date: string;
  sessions: number;
  messages: number;
}

export interface StatsProjectItem {
  project_name: string;
  workspace_hash: string;
  session_count: number;
  message_count: number;
}

export interface StatsHourlyItem {
  hour: number;
  count: number;
}

/**
 * 格式化日期为 YYYY-MM-DD
 */
export function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 获取今天的日期对象
 */
export function getToday(): Date {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

/**
 * 计算两个日期之间的天数差
 */
export function getDaysDiff(date1: Date, date2: Date): number {
  const diffTime = Math.abs(date2.getTime() - date1.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * 获取最近 N 天的日期数组
 */
export function getLastNDays(n: number): string[] {
  const days: string[] = [];
  const today = getToday();

  for (let i = n - 1; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    days.push(formatDate(date));
  }

  return days;
}

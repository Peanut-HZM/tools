/**
 * K8s 控制台 - 资源列表工具函数
 *
 * 提供时间格式化、状态颜色等通用辅助
 */

/**
 * 将 ISO 时间字符串转换为人类可读的"运行时间"
 * 例如：2h, 3d, 5m, 1y
 */
export function formatAge(created_at: string | undefined | null): string {
  if (!created_at) return '-';

  const created = new Date(created_at).getTime();
  const now = Date.now();
  const diffMs = now - created;

  if (diffMs < 0) return '-';

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const years = Math.floor(days / 365);

  if (years > 0) return `${years}y`;
  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

/**
 * 根据 Pod phase 返回状态颜色类名
 * - 绿色：Running
 * - 黄色：Pending / ContainerCreating / CrashLoopBackOff
 * - 红色：Failed / Error
 * - 灰色：Succeeded / Unknown
 */
export function getStatusColor(phase: string, status?: string): string {
  const lower = (status || phase).toLowerCase();

  if (lower.includes('crashloop') || lower.includes('error')) return 'text-red-400';
  if (lower === 'running') return 'text-green-400';
  if (lower === 'pending' || lower === 'containercreating' || lower.includes('waiting')) return 'text-yellow-400';
  if (lower === 'failed') return 'text-red-400';
  if (lower === 'succeeded') return 'text-slate-400';
  return 'text-slate-400';
}

/**
 * 根据 Pod phase 返回状态图标
 */
export function getStatusIcon(phase: string, status?: string): string {
  const lower = (status || phase).toLowerCase();

  if (lower.includes('crashloop') || lower.includes('error')) return 'fas fa-times-circle';
  if (lower === 'running') return 'fas fa-check-circle';
  if (lower === 'pending' || lower === 'containercreating' || lower.includes('waiting')) return 'fas fa-clock';
  if (lower === 'failed') return 'fas fa-exclamation-circle';
  if (lower === 'succeeded') return 'fas fa-check-circle';
  return 'fas fa-question-circle';
}

/**
 * 节点就绪状态
 */
export function getNodeStatusColor(status: string): string {
  const lower = status.toLowerCase();
  if (lower === 'ready' || lower === 'true') return 'text-green-400';
  if (lower.includes('notready') || lower === 'false') return 'text-red-400';
  return 'text-yellow-400';
}

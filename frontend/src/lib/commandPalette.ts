import type { Tool } from '../types';
import { PAGE_ROUTES, type PageRouteKey } from './navigation';

/** 命令面板条目：工具 + 静态页面 */
export interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  group: '工具' | '页面';
  route: string;
  /** 仅工具条目有：跳转工作区时通过 route state 传递，与 App.tsx handleToolClick 约定一致 */
  toolId?: string;
}

/** 页面键 → 静态中文 label 映射（面板文案不走 i18n，与原静态清单保持一致；Record 保证键全覆盖） */
const PAGE_LABELS: Record<PageRouteKey, string> = {
  home: '首页',
  marketplace: '工具市场',
  courses: '课程',
  techContents: '技术内容',
  account: '账户设置',
};

/** 面板固定收录的静态页面入口：路由来源收敛到 navigation.ts 的 PAGE_ROUTES，本处仅补文案 */
export const PAGE_ITEMS: CommandItem[] = PAGE_ROUTES.map((page) => ({
  id: page.id,
  label: PAGE_LABELS[page.key],
  group: '页面' as const,
  route: page.to,
}));

/** 后端工具列表 → 面板条目（description 作为 hint；toolId 供工作区 state 跳转） */
export function buildCommandItems(tools: Tool[]): CommandItem[] {
  return tools.map((tool) => ({
    id: `tool-${tool.id}`,
    label: tool.title,
    hint: tool.description,
    group: '工具' as const,
    route: '/workspace',
    toolId: tool.id,
  }));
}

/** 过滤：大小写不敏感，匹配 label/hint/route；空串返回全部 */
export function filterCommands(items: CommandItem[], query: string): CommandItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter(
    (item) =>
      item.label.toLowerCase().includes(q) ||
      (item.hint ?? '').toLowerCase().includes(q) ||
      item.route.toLowerCase().includes(q)
  );
}

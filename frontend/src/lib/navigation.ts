/**
 * 全站路由与事件名单一来源。
 *
 * 纯数据模块：不依赖 React 与 i18n。原因：
 * - i18n 文案需要组件上下文（useI18n Hook），而路由结构与激活判定规则是纯数据；
 * - 消费端（Header/Footer 等）拿到路由定义后，用 `t.nav[item.key]` 自行取文案。
 *
 * 此前 Header、Footer、commandPalette 三处各自维护一份路由清单，存在漂移风险，
 * 现统一收敛到本模块（phase3-deferred 带入项）。
 */

/** 命令面板打开事件名：Header 移动端搜索按钮、Hero CTA 派发，CommandPalette 监听 */
export const OPEN_COMMAND_PALETTE_EVENT = 'open-command-palette';

/** 顶部导航路由键：与 i18n locales 的 nav 文案键一一对应 */
export type NavRouteKey = 'home' | 'marketplace' | 'courses' | 'techContents';

/** 顶部导航路由定义 */
export interface NavRoute {
  /** 跳转目标路径 */
  to: string;
  /** i18n 文案键（t.nav[item.key]），由消费端解析为展示文案 */
  key: NavRouteKey;
  /** 激活判定：首页全等匹配，其余按路径前缀匹配（与原 Header NAV_ITEMS 语义一致） */
  match(path: string): boolean;
}

/**
 * 顶部导航路由（Header 导航与 Footer 页面导航共用）。
 * 注意：激活判定语义不得改变——首页全等、其余 startsWith。
 */
export const NAV_ROUTES: NavRoute[] = [
  { to: '/', key: 'home', match: (p) => p === '/' },
  { to: '/marketplace', key: 'marketplace', match: (p) => p.startsWith('/marketplace') },
  { to: '/courses', key: 'courses', match: (p) => p.startsWith('/courses') },
  { to: '/tech-contents', key: 'techContents', match: (p) => p.startsWith('/tech-contents') },
];

/** 命令面板收录的静态页面路由键：导航四项 + 账户设置 */
export type PageRouteKey = NavRoute['key'] | 'account';

/** 命令面板固定收录的静态页面路由定义 */
export interface PageRoute {
  /** 面板条目 id（page-* 前缀） */
  id: string;
  /** 跳转目标路径 */
  to: string;
  /** 页面键：commandPalette 据此映射静态中文 label */
  key: PageRouteKey;
}

/**
 * 命令面板固定收录的静态页面路由（首页/市场/课程/技术内容/账户设置）。
 * 文案不在此定义——label 映射留在 commandPalette.ts（面板文案不走 i18n）。
 */
export const PAGE_ROUTES: PageRoute[] = [
  { id: 'page-home', to: '/', key: 'home' },
  { id: 'page-marketplace', to: '/marketplace', key: 'marketplace' },
  { id: 'page-courses', to: '/courses', key: 'courses' },
  { id: 'page-tech-contents', to: '/tech-contents', key: 'techContents' },
  { id: 'page-account', to: '/account-settings', key: 'account' },
];

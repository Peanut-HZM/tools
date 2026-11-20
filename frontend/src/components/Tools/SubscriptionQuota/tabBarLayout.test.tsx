/**
 * Tab 栏常驻顶部回归测试
 *
 * 真实缺陷：整个页面外层容器带 `overflow-y-auto`，Tab 导航只是它内部的第一个
 * 子元素。滚动时 Tab 栏跟着内容一起滚出视口；又因为滚动条在外层工作区，
 * 用户继续滚动也再也滚不回来 —— Tab 栏永久消失。
 *
 * 修复后结构：
 *   <div class="flex h-full min-h-0 flex-col">        ← 固定一屏、不滚动
 *     <div class="shrink-0 …">Tab 栏</div>            ← 常驻顶部
 *     <div class="… overflow-y-auto …">内容区</div>   ← 只有这里滚动
 *
 * 注意：jsdom 不加载 Tailwind CSS，`getComputedStyle` 拿不到 overflow 值，
 * 因此这里直接断言 className —— 只要 Tab 的祖先里出现滚动类名即视为回归。
 */
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, it, expect, vi } from 'vitest';

vi.mock('../../../api/subscriptionQuotaApi', () => ({
  listAccounts: () => Promise.resolve([]),
  listProviders: () =>
    Promise.resolve({ providers: [], displayNames: {}, subscriptionIds: [], manualProviderIds: [] }),
  listAgents: () => Promise.resolve({ agents: [] }),
  queryQuota: () => Promise.resolve({ accounts: [] }),
  listSubscriptions: () => Promise.resolve([]),
  getUsage: () => Promise.resolve({ available: false }),
  addAccount: () => Promise.resolve({}),
  updateAccount: () => Promise.resolve({}),
  deleteAccount: () => Promise.resolve({}),
  testAccount: () => Promise.resolve({}),
  adjustQuota: () => Promise.resolve({}),
  switchAgent: () => Promise.resolve({}),
  restoreAgent: () => Promise.resolve({}),
  previewSwitch: () => Promise.resolve({}),
  importFromCcSwitch: () =>
    Promise.resolve({ imported: 0, created: 0, updated: 0, skipped: 0, dryRun: false, items: [] }),
  syncFromMagpie: () => Promise.resolve({}),
  getMagpieStatus: () => Promise.resolve({ available: false }),
  getGatewayStatus: () => Promise.resolve({ enabled: false }),
}));

vi.mock('./AgentSwitchPanel', () => ({
  AgentSwitchPanel: () => <div data-testid="agents-panel" />,
}));
vi.mock('./GatewayPanel', () => ({
  GatewayPanel: () => <div data-testid="gateway-panel" />,
}));

import SubscriptionQuotaPage from './index';

/** 判断某个 className 是否让元素成为纵向滚动容器 */
function isVerticalScroller(className: string): boolean {
  return /(^|\s)(overflow-y-auto|overflow-auto|overflow-y-scroll|overflow-scroll)(\s|$)/.test(
    className,
  );
}

describe('SubscriptionQuota Tab 栏布局', () => {
  afterEach(cleanup);

  it('Tab 栏的祖先中不能出现纵向滚动容器（否则滚动后会永久消失）', async () => {
    render(<SubscriptionQuotaPage />);

    // 等待异步加载完成后再取 Tab（加载态下不渲染 Tab 栏）
    const tab = await screen.findByRole('button', { name: /概览/ });
    expect(tab).toBeTruthy();

    const scrollerAncestors: string[] = [];
    let node: HTMLElement | null = tab.parentElement;
    while (node) {
      const cls = typeof node.className === 'string' ? node.className : '';
      if (isVerticalScroller(cls)) scrollerAncestors.push(cls);
      node = node.parentElement;
    }

    expect(scrollerAncestors).toEqual([]);
  });

  it('Tab 栏自身不随内容滚动（存在独立的滚动容器承载内容）', async () => {
    const { container } = render(<SubscriptionQuotaPage />);
    await screen.findByRole('button', { name: /概览/ });

    // 页面上必须存在至少一个纵向滚动容器（承载各 Tab 内容）
    const scrollers = [...container.querySelectorAll<HTMLElement>('div')].filter((el) =>
      isVerticalScroller(typeof el.className === 'string' ? el.className : ''),
    );
    expect(scrollers.length).toBeGreaterThan(0);
  });
});

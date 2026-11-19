/**
 * Layout 沉浸式外壳回归测试
 *
 * 背景（真实缺陷）：
 * Layout 之前用 `location.pathname === '/workspace'` 精确匹配判断是否工作区，
 * 而工作区工具页的真实地址是 `/workspace/<工具编码>`（如 /workspace/cross-share）。
 * 精确匹配导致所有工作区工具页落入「普通页面」分支：
 *   1. 渲染出底部 Footer + 顶部 Header（工作区本不需要）
 *   2. 外层容器从 `h-dvh overflow-hidden` 退化为 `min-h-screen`
 *      → 页面被整体撑开，工具内部固定在底部的操作区（如 CrossShare 的发送按钮）
 *         被推到可视区之外，必须滚动到页面最底部才能看到并点击。
 *
 * 本测试覆盖：
 * - /workspace/<toolId> 属于工作区：不渲染 Footer / MobileTabBar，容器为沉浸式高度
 * - /workspace 本身同样是工作区
 * - /tools/<toolId> 保持原有的沉浸式行为
 * - 普通页面（首页）仍然渲染 Footer 与移动端 Tab 栏
 */
import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('../Header/Header', () => ({ default: () => <div data-testid="header" /> }));
vi.mock('../Footer/Footer', () => ({ default: () => <footer data-testid="footer" /> }));
vi.mock('./MobileTabBar', () => ({ default: () => <div data-testid="mobile-tabbar" /> }));
vi.mock('../Common/CommandPalette', () => ({ default: () => null }));
vi.mock('../../hooks/useSearch', () => ({
  useSearch: () => ({
    searchValue: '',
    debouncedValue: '',
    handleSearchChange: () => {},
    handleSearch: () => {},
  }),
}));

import Layout from './Layout';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<div data-testid="home" />} />
          <Route path="/workspace" element={<div data-testid="ws" />} />
          <Route path="/workspace/:toolId" element={<div data-testid="ws-tool" />} />
          <Route path="/tools/:toolId" element={<div data-testid="tool" />} />
          <Route path="/marketplace" element={<div data-testid="market" />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

/** 取 Layout 最外层容器 */
function shell(container: HTMLElement): HTMLElement {
  return container.firstElementChild as HTMLElement;
}

describe('Layout 沉浸式外壳', () => {
  afterEach(cleanup);

  it('/workspace/<toolId> 不渲染 Footer 与移动端 Tab 栏', () => {
    const { container, queryByTestId } = renderAt('/workspace/cross-share');
    expect(queryByTestId('footer')).toBeNull();
    expect(queryByTestId('mobile-tabbar')).toBeNull();
    // 沉浸式外壳：高度锁定一屏且禁止整页滚动
    const cls = shell(container).className;
    expect(cls).toContain('h-dvh');
    expect(cls).toContain('overflow-hidden');
  });

  it('/workspace 本身同样不渲染 Footer', () => {
    const { container, queryByTestId } = renderAt('/workspace');
    expect(queryByTestId('footer')).toBeNull();
    expect(shell(container).className).toContain('h-dvh');
  });

  it('/tools/<toolId> 保持沉浸式（无 Footer）', () => {
    const { container, queryByTestId } = renderAt('/tools/cross-share');
    expect(queryByTestId('footer')).toBeNull();
    expect(shell(container).className).toContain('h-dvh');
  });

  it('普通页面仍然渲染 Footer 与移动端 Tab 栏', () => {
    const { container, queryByTestId } = renderAt('/');
    expect(queryByTestId('footer')).not.toBeNull();
    expect(queryByTestId('mobile-tabbar')).not.toBeNull();
    expect(shell(container).className).toContain('min-h-screen');
  });
});

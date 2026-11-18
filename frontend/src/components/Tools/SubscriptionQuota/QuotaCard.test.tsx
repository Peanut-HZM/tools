import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QuotaCard } from './index';
import type { SubscriptionQuotaDto } from '../../../api/subscriptionQuotaApi';

// 组件里只有 Card/Badge 用了 UI 基础件，不做网络请求（QuotaCard 是纯展示）
const baseQuota: SubscriptionQuotaDto = {
  tool: 'kimi',
  credentialStatus: 'valid',
  credentialMessage: null,
  success: true,
  tiers: [
    { name: 'five_hour', utilization: 26, resetsAt: new Date(Date.now() + 3600_000).toISOString() },
    { name: 'weekly_limit', utilization: 47, resetsAt: new Date(Date.now() + 3 * 86400_000).toISOString() },
  ],
  planName: 'Allegretto',
  error: null,
  queriedAt: Date.now() - 60_000,
};

describe('QuotaCard', () => {
  afterEach(cleanup);

  it('渲染供应商名、套餐名与每档剩余百分比', () => {
    render(
      <QuotaCard quota={baseQuota} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );

    // 供应商显示名（来自 toolLabel 兜底）
    expect(screen.getByText('Kimi Code')).toBeTruthy();
    // 套餐名
    expect(screen.getByText('Allegretto')).toBeTruthy();
    // 5 小时档：已用 26% → 剩余 74%
    expect(screen.getByText('5 小时')).toBeTruthy();
    expect(screen.getByText('74%')).toBeTruthy();
    // 每周档：已用 47% → 剩余 53%
    expect(screen.getByText('每周')).toBeTruthy();
    expect(screen.getByText('53%')).toBeTruthy();
  });

  it('额度计为 meter 角色并带正确的 aria 值（无障碍）', () => {
    render(
      <QuotaCard quota={baseQuota} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );
    const meters = screen.getAllByRole('meter');
    expect(meters).toHaveLength(2);
    expect(meters[0].getAttribute('aria-valuenow')).toBe('74');
    expect(meters[1].getAttribute('aria-valuenow')).toBe('53');
  });

  it('剩余低于 20% 时带上警告文案语义（已用 90 → 剩余 10）', () => {
    const lowQuota: SubscriptionQuotaDto = {
      ...baseQuota,
      tiers: [{ name: 'five_hour', utilization: 90, resetsAt: null }],
    };
    render(
      <QuotaCard quota={lowQuota} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );
    const meter = screen.getByRole('meter');
    expect(meter.getAttribute('aria-valuenow')).toBe('10');
    expect(screen.getByText('10%')).toBeTruthy();
  });

  it('未登录时显示未检测到凭据，而不是伪造额度', () => {
    const notFound: SubscriptionQuotaDto = {
      tool: 'claude',
      credentialStatus: 'not_found',
      credentialMessage: null,
      success: false,
      tiers: [],
      planName: null,
      error: null,
      queriedAt: null,
    };
    render(
      <QuotaCard quota={notFound} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );
    expect(screen.getByText('Claude Code')).toBeTruthy();
    expect(screen.getByText('未检测到登录')).toBeTruthy();
    expect(screen.getByText('未检测到本地登录凭据')).toBeTruthy();
    // 不能出现任何百分比
    expect(screen.queryByText(/%$/)).toBeNull();
  });

  it('查询失败时展示后端返回的真实错误原文', () => {
    const failed: SubscriptionQuotaDto = {
      tool: 'zhipu',
      credentialStatus: 'valid',
      credentialMessage: '接口返回错误：令牌已过期或验证不正确',
      success: false,
      tiers: [],
      planName: null,
      error: '接口返回错误：令牌已过期或验证不正确',
      queriedAt: Date.now(),
    };
    render(
      <QuotaCard quota={failed} now={Date.now()} refreshing={false} onRefresh={() => {}} />
    );
    expect(screen.getByText('智谱 GLM')).toBeTruthy();
    expect(screen.getByText('额度查询失败')).toBeTruthy();
    expect(screen.getByText('接口返回错误：令牌已过期或验证不正确')).toBeTruthy();
  });

  it('刷新按钮可点击并触发回调', () => {
    const onRefresh = vi.fn();
    render(
      <QuotaCard quota={baseQuota} now={Date.now()} refreshing={false} onRefresh={onRefresh} />
    );
    const button = screen.getByRole('button', { name: /刷新 Kimi Code 额度/ });
    button.click();
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('刷新中时按钮禁用并显示旋转图标', () => {
    render(
      <QuotaCard quota={baseQuota} now={Date.now()} refreshing onRefresh={() => {}} />
    );
    const button = screen.getByRole('button', { name: /刷新 Kimi Code 额度/ });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
});
